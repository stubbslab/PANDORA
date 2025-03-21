import logging
import time
from datetime import datetime
import numpy as np

## Make Pandora Class
from pandora.states.flipmount_state import FlipMountState
from pandora.states.shutter_state import ShutterState
from pandora.controller.keysight import KeysightController
from pandora.controller.monochromator import MonochromatorController
# from pandora.controller.zaberstages import ZaberController
from pandora.states.labjack_handler import LabJack
from pandora.states.states_map import State
from pandora.utils.logger import initialize_central_logger
from pandora.utils.operation_timer import OperationTimer
from pandora.database.db import PandoraDatabase
from pandora.database.calib_db import PandoraCalibrationDatabase

## TODOS:
## Add a header to the class
## Add a header with the run information
## Add a timer to the Pandora methods to measure the time taken for each operation
## Each method should log the time taken for the operation
## 
class PandoraBox:
    """
    The Pandora class manages all subsystems of the PANDORA instrument.
    It coordinates communication and state management across the 
    monochromator, shutter, flip mounts, Keysight electrometers, 
    and Zaber stages.

    The class handles:
    - Initializing each subsystem controller class
    - Establishing connections to hardware
    - Validating that each subsystem is ready (e.g. in IDLE state)
    - Providing a unified interface to configure and operate the entire system
    """
    def __init__(self, config_file='../default.yaml', run_id=None, verbose=True):
        # Load configuration (IP addresses, device IDs, calibration files, etc.)
        self.config = self._load_config(config_file)

        # Initialize logger
        self._initialize_logger(verbose=verbose)
        self.logger = logging.getLogger(f"pandora.controller")

        # Instantiate subsystem controllers using config parameters.
        self.initialize_subsystems()  

        # Initialize the database
        self.initialize_db(run_id)

        # Initializer a timer
        self.max_operation_freq = 10 # Hz
        self.timer = OperationTimer(min_interval=1/self.max_operation_freq, name=f"Pandora")

    def initialize_db(self, run_id=None):
        # Initialize the database connection
        self.logger.info("Initializing database connection...")
        root = self.get_config_value('database', 'root')
        self.pdb = PandoraDatabase(run_id=run_id, root_path=root)
        self.calib = PandoraCalibrationDatabase(root_path=root)
        pass

    def get_db(self):
        return self.pdb.db
    
    def _initialize_logger(self,verbose=True):
        # Setup and return a logger instance for the Pandora class
        logging_config = self.get_config_section('logging')
        self.logger = initialize_central_logger(logging_config['logfile'], logging_config['level'], verbose)
        pass

    def initialize_subsystems(self):
        """
        Create and initialize all subsystem objects. 
        
        This may call constructors and run initial setup routines for each device. 
        After this call, we should have objects ready to connect.
        """
        # Query the config for IP addresses and other parameters
        mono_config = self.get_config_section('monochromator')
        ks_config = self.get_config_section('keysights')
        zb_config = self.get_config_section('zaber_stages')
        
        # LabJack Controlled Devices
        # Port names for each subsystem
        labjack_ip = self.get_config_value('labjack', 'ip_address')
        shutter_port = self.get_config_value('labjack', 'flipShutter')
        fm1_port = self.get_config_value('labjack', 'flipSpecMount')
        fm2_port = self.get_config_value('labjack', 'flipOrderBlockFilter')
        fm3_port = self.get_config_value('labjack', 'flipOD2First')
        fm4_port = self.get_config_value('labjack', 'flipOD2Second')
        fm5_port = self.get_config_value('labjack', 'flipPD2')
        fm6_port = self.get_config_value('labjack', 'flipPD3')
        fm7_port = self.get_config_value('labjack', 'flipQuarterWavePlate')
        

        # Photodiode Controlled Devices
        # Ethernet connections with ip_addresses
        k1_config = self.get_config_section('K1', config=ks_config)
        k2_config = self.get_config_section('K2', config=ks_config)

        z1_config = self.get_config_section('Z1', config=zb_config)
        z2_config = self.get_config_section('Z2', config=zb_config)
        z3_config = self.get_config_section('Z3', config=zb_config)

        # LabJack
        self.labjack = LabJack(ip_address=labjack_ip)

        # Shutter
        self.shutter = ShutterState(shutter_port,labjack=self.labjack)
        
        # Flip Mounts
        self.flipMountNames = [
                               'flipShutter', 'flipSpecMount', 'flipOrderBlockFilter',
                               'flipOD2First', 'flipOD2Second', 'flipPD2',
                               'flipQuarterWavePlate', 'flipPD3'
                               ]
        
        self.flipShutter = FlipMountState(shutter_port, labjack=self.labjack)
        self.flipSpecMount = FlipMountState(fm1_port, labjack=self.labjack)
        self.flipOrderBlockFilter = FlipMountState(fm2_port, labjack=self.labjack)
        self.flipOD2First = FlipMountState(fm3_port, labjack=self.labjack)
        self.flipOD2Second = FlipMountState(fm4_port, labjack=self.labjack)
        self.flipPD2 = FlipMountState(fm5_port, labjack=self.labjack)
        self.flipPD3 = FlipMountState(fm6_port, labjack=self.labjack)
        self.flipQuarterWavePlate = FlipMountState(fm7_port, labjack=self.labjack)
        
        # Add more flip mounts as needed...

        # Keysights
        # self.photodiodeNames = list(ks_config.keys())
        self.keysight = type('KeysightContainer', (), {})()
        self.keysight.deviceNames = list(ks_config.keys())
        self.keysight.k1 = KeysightController(**k1_config)
        self.keysight.k2 = KeysightController(**k2_config)
        # Add more Keysights as needed...

        # Zaber Stages
        # self.zaber = type('ZaberContainer', (), {})()
        # self.zaberNames = list(zb_config.keys())
        # self.zaberNDFilter = ZaberController(**z1_config)
        # self.zaberFocus = ZaberController(**z2_config)
        # self.zaberPinholeMask = ZaberController(**z3_config)
        # Add more stages as needed...

        # Monochromator
        self.monochromator = MonochromatorController(**mono_config)

        # # Spectrograph
        # spec_conf = self.config['spectrograph']
        # self.spectrograph = SpectrographState(
        #     usb_port=spec_conf['usb_port'],
        #     baud_rate=spec_conf['baud_rate'],
        #     timeout=spec_conf['timeout']
        # )

        self.logger.info("All subsystems have been initialized.")
        pass

    def _load_config(self, config_file):
        # Parse a config file (JSON, YAML, etc.) with device parameters
        import yaml
        import os
        # get current working directory
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def get_config_section(self, section, config=None):
        if config is None: config = self.config
        return config.get(section, {})
    
    def get_config_value(self, section, key, default=None, config=None):
        if config is None: config = self.config
        return config.get(section, {}).get(key, default)

    def go_home(self):
        """
        Set the PANDORA system to a known "home" state:
        - All flip mounts: OFF (out of the optical path)
        - Shutter: ON (open)
        - Keysights: IDLE (no measurement)
        - Monochromator: send to home position
        """
        pass

    def exposure(self, counts=None, exptime=None):
        """
        Perform an exposure by either integrating until a given threshold flux (counts) 
        is reached, or for a specified exposure time (exptime).

        Args:
            counts (float, optional): Target integrated charge in ADU (or suitable units). 
                                    If provided, the exposure ends when the threshold is reached.
            exptime (float, optional): Exposure time in seconds. If provided, the exposure ends 
                                    after this duration.
        
        Examples:
            pb.exposure(counts=1e-13)  # Integrate until 1e-13 ADU is reached
            pb.exposure(exptime=1)     # Integrate for 1 second
        """
        pass

    def take_exposure(self, exptime, observation_type="acq", is_dark=False):
        """
        Take an exposure for a specified time.

        Args:
            exptime (float): Exposure time in seconds.
            is_dark (bool): If True, the exposure is a dark frame. 

        """
        self.keysight.k1.on()  # Keysight 1 ON
        self.keysight.k2.on()  # Keysight 2 ON

        # Set acquisition time if exptime is provided
        self.keysight.k1.set_acquisition_time(exptime)
        self.keysight.k2.set_acquisition_time(exptime)

        # Define exposure
        self.pdb.add("exptime", float(exptime))
        self.pdb.add("timestamp", datetime.now())
        if is_dark:
            self.close_shutter()
        else:
            self.open_shutter()  # Shutter ON
        self.timer.mark("Exposure")

        # Start acquire without waiting
        self.keysight.k1.acquire()
        self.keysight.k2.acquire()
        self.logger.info(f"Exposure is set last {self.keysight.k1.t_acq:0.3f} seconds.")

        self.timer.sleep(exptime)
        self.close_shutter()  # Shutter OFF
        eff_exptime = self.timer.elapsed_since("Exposure")

        # Reading the data
        d1 = self.keysight.k1.read_data(wait=True)
        d2 = self.keysight.k2.read_data(wait=True)

        self.logger.info(f"Exposure ended after {eff_exptime:.3f} seconds.")

        # Save the exposure data
        self._save_exposure(d1, d2, eff_exptime, observation_type, not is_dark)
        pass

    def _save_exposure(self, d1, d2, eff_exptime, description, shutter_flag=True):
        self.pdb.add("effective_exptime", eff_exptime)
        self.pdb.add("wavelength", self.get_wavelength())
        self.pdb.add("currentInput", np.abs(np.mean(d1['CURR'])))
        self.pdb.add("currentOutput", np.abs(np.mean(d2['CURR'])))
        self.pdb.add("currentInputErr", np.std(d1['CURR']))
        self.pdb.add("currentOutputErr", np.std(d2['CURR']))
        # self.pdb.add("zaberNDFilter", self.zaberNDFilter.position)

        # Save the flip mount states
        for name in self.flipMountNames:
            fm = getattr(self, name, None)
            self.pdb.add(name, fm.state.value)
        
        self.pdb.add("Description", description)
        
        self.pdb.save_lightcurve(d1, tag="currentInput")
        self.pdb.save_lightcurve(d2, tag="currentOutput")
        # self.pdb.add("Alt", self.mount.altitude)
        # self.pdb.add("Az", self.mount.azimuth)

        self.write_exposure()
    
    def take_dark(self, exptime, observation_type="dark"):
        """
        Take a dark exposure for a specified time.

        Args:
            exptime (float): Exposure time in seconds.

        """
        self.take_exposure(exptime, observation_type=observation_type, is_dark=True)
        pass
        
    def wavelength_scan(self, start, end, step, exptime, observation_type="acq", nrpeats=1, range1=None, range2=None):
        """
        Wavelength scan with measurements from start to end with a given step size.

        The measurements sequence is one dark, one light, and one dark.

        Args:
            start (float): Start wavelength in nm.
            end (float): End wavelength in nm.
            step (float): Step size in nm.
            exptime (float): Exposure time in seconds.
            observation_type (str, optional): Type of observation (acq, dark, calib).
            range1 (float, optional): Range for Keysight 1.
            range2 (float, optional): Range for Keysight 2.

        """
        self.logger.info(f"Starting wavelength-scan from {start:.1f} nm to {end:.1f} nm with step {step:.1f} nm...")

        ##### Wavelength Scan Setup
        wavelengthScan = np.arange(start,end+step, step)

        ##### Keysight Fine-Tunning
        if range1 is None: range1 = 200e-9 # B2987B
        if range2 is None: range2 = 2e-9 # B2983B

        # Flip the wavelength ordering filter
        # self.flipMount.f1.activate()
        
        for wav in wavelengthScan:
            self.logger.info(f"wavelength-scan: start exposure of lambda = {wav:0.1f} nm with {nrpeats} repeats")
            self.set_wavelength(wav)
            if wav>700:
                # Check what is the IR filter code
                self.enable_ir_filter()

            self.keysight.k1.set_rang(range1)
            self.keysight.k2.set_rang(range2)

            for _ in range(nrpeats):
                self.take_dark(exptime)
                self.take_exposure(exptime, observation_type=observation_type)
                self.take_dark(exptime)

            self.logger.info(f"wavelength-scan: finished exposure of lambda = {wav:0.1f} nm")

        self.close_all_connections()
        self.logger.info("wavelength-scan measurement cycle completed.")
        self.logger.info("wavelength-scan saved on {self.pdb.run_data_file}")

    ## TODO
    ## Under construction
    ## First Draft
    def solar_cell_qe_curve(self, start, end, step, exptime, nrpeats=1, range1=None, range2=None):
        """
        Solar cell QE curve is a walength scan with flipping the NIST diode on and off.

        The measurements sequence is 
        1) solar cell (NIST diode out of the beam): one dark
        2) NIST (NIST diode in the beam): one dark, one light, one dark
        3) solar cell: one light, one dark

        Args:
            start (float): Start wavelength in nm.
            end (float): End wavelength in nm.
            step (float): Step size in nm.
            exptime (float): Exposure time in seconds.
            range1 (float, optional): Range for Keysight 1.
            range2 (float, optional): Range for Keysight 2.

        """
        self.logger.info(f"Starting solar cell qe curve from {start:.1f} nm to {end:.1f} nm with step {step:.1f} nm...")

        ##### Wavelength Scan Setup
        wavelengthScan = np.arange(start,end+step, step)

        ##### Keysight Fine-Tunning
        if range1 is None: range1 = 200e-9 # B2987B
        if range2 is None: range2 = 2e-9 # B2983B
    
        # for wav in wavelengthScan:
        #     self.logger.info(f"solar-cell-qe-curve: start exposure of lambda = {wav:0.1f} nm with {nrpeats} repeats")
        #     self.set_wavelength(wav)
        #     if wav>700:
        #         # Check what is the IR filter code
        #         self.enable_ir_filter()

        #     self.keysight.k1.set_rang(range1)
        #     self.keysight.k2.set_rang(range2)

        #     # make sure NIST diode is out of the beam
        #     self.flipMount.nist.deactivate()
        #     for _ in range(nrpeats):
        #         self.take_dark(exptime, observation_type="dark")
                
        #         # put NIST diode in the beam
        #         self.flipMount.nist.activate()
        #         self.take_dark(exptime, observation_type="dark")
        #         self.take_exposure(exptime, observation_type="solarcell")
        #         self.take_dark(exptime, observation_type="dark")

        #         # put NIST diode out of the beam
        #         self.flipMount.nist.deactivate()
        #         self.take_exposure(exptime, observation_type="solarcell")
        #         self.take_dark(exptime, observation_type="dark")

        #     self.logger.info(f"solar-cell-qe-curve: finished exposure of lambda = {wav:0.1f} nm")

        self.close_all_connections()
        self.logger.info("solar-cell-qe-curve measurement cycle completed.")
        self.logger.info("solar-cell-qe-curve saved on {self.pdb.run_data_file}")

    # TODO: Check what is the IR filter code
    def enable_ir_filter(self):
        """
        Put the Order-Block(UV) filter on the optical path.
        """
        self.flipOrderBlock.activate()
        pass

    def write_exposure(self):
        """
        Write the exposure data to the database.
        """
        self.pdb.write_exposure()
        pass

    def write_calibration(self, data, tag="calibration"):
        """
        Write the calibration data to the database (root/calib/).
        
        Parameters
        ----------
        data : pd.DataFrame
            The calibration data to save.
        tag : str, optional
            A tag to append to the filename.
        """
        self.pdb.write_calibration(data, tag)
        pass

    def load_pandora_throughput(self, fname=None):
        """
        Load the throughput calibration data for the PANDORA system.

        Parameters
        ----------
        fname : str, optional
            The filename of the throughput calibration data. If none, the default file is loaded.

        """
        if fname is None:
            return self.calib.get_calibration_file(fname)
        else:
            return self.calib.get_default_calibration("throughput")
    
    def get_qe_curve(self, fname=None, label="qe_solarcell"):
        """
        Get the quantum efficiency curve for the solar cell.

        Parameters
        ----------
        fname : str, optional
            The filename of the QE curve data. If none, the default file is loaded.

        label : str, optional
            The label of the calibration data to load.

        Returns
        -------
        qeCurve : function
            The quantum efficiency curve function.
        """
        from scipy.interpolate import interp1d
        if fname is not None:
            df = self.calib.get_calibration_file(fname)
        else:
            df = self.calib.get_default_calibration(label)

        # Interpolate the QE curve
        qeCurve = interp1d(df['wavelength'], df['qe'], kind='cubic',
                         fill_value=np.nan, bounds_error=False)
        return qeCurve
            
    def get_qe_solarcell(self, fname=None):
        """
        Get the quantum efficiency curve for the solar cell.
        """
        qeCurve = self.get_qe_curve(fname, label="qe_solarcell")
        return qeCurve
    
    def get_qe_diode(self, fname=None):
        """
        Get the quantum efficiency curve for the monitor diode.s
        """
        qeCurve = self.get_qe_curve(fname, label="qe_diode")
        return qeCurve
    
    def get_qe_nist(self, fname=None):
        """
        Get the quantum efficiency curve for the NIST diode.
        """
        qeCurve = self.get_qe_curve(fname, label="qe_nist")
        return qeCurve
    
    def close_all_connections(self):
        """
        Close all connections to devices in a controlled manner.
        Ensures that each subsystem returns to a safe state before closing.
        """
        self.logger.info("Closing all device connections...")

        # Close monochromator connection if exists
        if hasattr(self, 'monochromator') and self.monochromator is not None:
            self.logger.info("Closing monochromator connection.")
            self.monochromator.close()

        # Close shutter connection
        if hasattr(self, 'shutter') and self.shutter is not None:
            self.logger.info("Closing shutter connection.")
            self.shutter.close()

        # Close flip mount connections
        names = self.flipMountNames
        for name in names:
            fm = getattr(self, name, None)
            if fm:
                self.logger.info(f"Closing flip mount {name} connection.")
                fm.close()

        # Close keysight connections
        if hasattr(self, 'keysight') and self.keysight is not None:
            for attr_name in dir(self.keysight):
                if attr_name.startswith('k'):
                    ks = getattr(self.keysight, attr_name, None)
                    if ks:
                        self.logger.info(f"Closing keysight {attr_name} connection.")
                        ks.close()

        # Close Zaber stage connections
        # TODO: Check if we need to close the Zaber stages

        # Close spectrograph connection
        if hasattr(self, 'spectrograph') and self.spectrograph is not None:
            self.logger.info("Closing spectrograph connection.")
            self.spectrograph.close()

        # Close LabJack connection
        if hasattr(self, 'labjack') and self.labjack is not None:
            self.logger.info("Closing LabJack connection.")
            self.labjack.close()

        self.logger.info("All device connections have been closed.")

    def run_initial_checks(self):
        """
        Run any initial calibration routines, checks, or verifications needed 
        before the system can be fully operational.
        """
        # This might involve setting known positions for Zaber stages,
        # verifying filters, checking the shutter, etc.
        pass

    def open_shutter(self):
        """
        Open the shutter to allow light to pass.
        """
        self.shutter.deactivate()
        pass

    def close_shutter(self):
        """
        Close the shutter to block light.
        """
        self.shutter.activate()
        pass

    def turn_on_sollar_cell(self):
        """
        Turn on the solar cell by moving the flip mount.
        """
        # self..activate()
        pass

    def switch_flipmount(self, mount_name):
        """
        Switch the flip mount to a new position.
        """
        flipmount = getattr(self, mount_name, None)
        if flipmount:
            flipmount.get_state()
            if flipmount.state == State.OFF:
                flipmount.activate()
            elif flipmount.state == State.ON:
                flipmount.deactivate()
            else:
                self.logger.error(f"Error switching flip mount {mount_name}.")
                print(f"Error switching flip mount {mount_name}.")
        pass

    def set_wavelength(self, wavelength, timeout=2):
        """
        Set the monochromator to a specific wavelength.
        """
        self.timer.mark("Wavelength")
        self.monochromator.move_to_wavelength(wavelength, timeout)
        # Check how long we should wait here
        # self.monochromator.wait_until_ready()
        self.logger.debug(f"Set wavelength to {wavelength} nm took {self.timer.elapsed_since('Wavelength'):.3f} seconds.")
        pass

    def get_wavelength(self):
        """
        Get the current wavelength of the monochromator.
        """
        self.monochromator.get_wavelength()
        return self.monochromator.wavelength
    
    def set_nd_filter(self,nd_filter_name):
        """
        Move the Zaber stage to a new position for the ND filter.
        Args:
            nd_filter_name (str): The name of the ND filter to move to.
        """
        # self.zaberNDFilter.move_to_slot(nd_filter_name)
        pass

    def set_pinhole_mask(self, mask_name):
        """
        Move the Zaber stage to a new position for the ND filter.
        Args:
            mask_name (str): The name of the pinhole mask to move to.
        """
        # self.zaberPinholeMask.move_to_slot(mask_name)
        pass

    def set_photodiode_scale(self, scale_down=None, scale=None):
        if scale_down is None and scale is None:
            self.open_shutter()
            self.keysight.k1.auto_scale()
            self.keysight.k2.auto_scale()
            self.close_shutter()
        elif scale is None:
            s1 = float(self.keysight.k2.get_rang())
            self.keysight.k2.set_rang(s1/scale_down)
        else:
            self.keysight.k2.set_rang(scale)

    def shutdown(self):
        """
        Gracefully shut down the system, ensuring everything returns to a safe state.
        """
        # Could call close_all_connections or put all subsystems off/idle first.
        pass

if __name__ == "__main__":
    pb = PandoraBox()
    pb.go_home()
    pb.exposure(counts=1e-13)
    pb.close_all_connections()
    pb.shutdown()