import logging
import time
from datetime import datetime
import numpy as np

## Make Pandora Class

from pandora.states.flipmount_state import FlipMountState
from pandora.states.shutter_state import ShutterState
from pandora.controller.keysight import KeysightController
from pandora.controller.monochromator import MonochromatorController
from pandora.controller.zaberstages import ZaberController
from pandora.states.labjack_handler import LabJack
from pandora.states.states_map import State
from pandora.utils.logger import initialize_central_logger
from pandora.utils.operation_timer import OperationTimer
from pandora.database.db import PandoraDatabase
from pandora.database.calib_db import PandoraCalibrationDatabase

# Moving average for a 1D array
def moving_average(arr, window):
    return np.convolve(arr, np.ones(window)/window, mode='valid')

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
    def __init__(self, config_file='../default.yaml', run_id=None, verbose=True,init_zaber: bool = True ):   #added disable zaber option
        # Load configuration (IP addresses, device IDs, calibration files, etc.)
        self.config = self._load_config(config_file)

        # Initialize logger
        self._initialize_logger(verbose=verbose)
        self.logger = logging.getLogger(f"pandora.controller")

        #new line to disable zabers if need be
        self._init_zaber = init_zaber


        # Instantiate subsystem controllers using config parameters.
        self.initialize_subsystems()  

        # Initialize the database
        self.initialize_db(run_id)

        # Initializer a timer
        self.max_operation_freq = 10 # Hz
        self.timer = OperationTimer(min_interval=1/self.max_operation_freq, name=f"Pandora")

        # initiate the wavelength variable
        self.wavelength = 0

    def initialize_db(self, run_id=None):
        # Initialize the database connection
        self.logger.info("Initializing database connection...")
        root = self.get_config_value('database', 'root')
        self.pdb = PandoraDatabase(run_id=run_id, root=root)
        self.calib = PandoraCalibrationDatabase(root=root)
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

        # Flip Mounts
        self.flipMountNames = ['flipOrderBlockFilter',
                               'flipOD2First', 'flipOD2Second',
                               'flipPD2'
                               # Add more flip mounts as needed...
                               ]
        fports, fstates = [], []
        for name in self.flipMountNames:
            fports.append(self.get_config_value('labjack', name))
            fstates.append(self.get_config_value('labjack', name+'InvertLogic'))


        # Photodiode Controlled Devices
        # Ethernet connections with ip_addresses
        k1_config = self.get_config_section('K1', config=ks_config)
        k2_config = self.get_config_section('K2', config=ks_config)
        # Add powerline_freq from keysights section to each Keysight config
        powerline_freq = ks_config.get('powerline_freq', 60)
        k1_config['powerline_freq'] = powerline_freq
        k2_config['powerline_freq'] = powerline_freq

        z1_config = self.get_config_section('Z1', config=zb_config)
        # z2_config = self.get_config_section('Z2', config=zb_config)
        z3_config = self.get_config_section('Z3', config=zb_config)

        # LabJack
        self.labjack = LabJack(ip_address=labjack_ip)

        # Shutter
        self.shutter = ShutterState(shutter_port,labjack=self.labjack)
        
        # Flip Mounts
        self.flipShutter = FlipMountState(shutter_port, labjack=self.labjack)
        for i, name in enumerate(self.flipMountNames):
            setattr(self, name, FlipMountState(fports[i], labjack=self.labjack, invert_logic=fstates[i]))
        
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
        if self._init_zaber:
            self.zaberNDFilter = ZaberController(**z1_config)
        else:
            self.zaberNDFilter = None
            self.logger.info("Zaber stages disabled (init_zaber = False)")
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

    def take_exposure(self, exptime, observation_type="acq", is_dark=False, warning=False):
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

        # timestamp
        timestamp = datetime.now()

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

        # Check if the exposure is overflow
        if (np.abs(np.mean(d1['CURR'])) > 1e36) and (not warning):
            self.logger.warning("Overflow in Keysight 1")
            # self.set_photodiode_scale(scale_down=1/10)
            self.set_photodiode_scale(keysight_id=1)
            self.take_exposure(exptime, observation_type=observation_type, is_dark=is_dark, warning=True)

        # Check if the exposure is overflow
        if (np.abs(np.mean(d2['CURR'])) > 1e36) and (not warning):
            self.logger.warning("Overflow in Keysight 2")
            # self.set_photodiode_scale(scale_down=1/10)
            self.set_photodiode_scale(keysight_id=2)
            self.take_exposure(exptime, observation_type=observation_type, is_dark=is_dark, warning=True)

        # Save the exposure data
        self._save_exposure(d1, d2, timestamp, exptime, eff_exptime, observation_type, not is_dark)
        pass

    def take_exposure_per_sample(self, exptime, observation_type="acq", is_dark=False, warning=False):
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

        # timestamp
        timestamp = datetime.now()

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

        # Check if the exposure is overflow
        if (np.abs(np.mean(d1['CURR'])) > 1e36) and (not warning):
            self.logger.warning("Overflow in Keysight 1")
            # self.set_photodiode_scale(scale_down=1/10)
            self.set_photodiode_scale(keysight_id=1)
            self.take_exposure(exptime, observation_type=observation_type, is_dark=is_dark, warning=True)

        # Check if the exposure is overflow
        if (np.abs(np.mean(d2['CURR'])) > 1e36) and (not warning):
            self.logger.warning("Overflow in Keysight 1")
            # self.set_photodiode_scale(scale_down=1/10)
            self.set_photodiode_scale(keysight_id=2)
            self.take_exposure(exptime, observation_type=observation_type, is_dark=is_dark, warning=True)

        window_size = 1
        # Loop over rows (i.e., d1[0] and d1[1]) if shape is (2, N)
        avg_curr_d1 = moving_average(d1['CURR'], window_size)
        avg_curr_d2 = moving_average(d2['CURR'], window_size)

        n = avg_curr_d1.size
        for i in range(0, n - n % window_size, window_size):
            dd1 = {'CURR':avg_curr_d1[i:i+window_size]}
            dd2 = {'CURR':avg_curr_d2[i:i+window_size]}
            self._save_exposure(dd1, dd2, timestamp, exptime, eff_exptime, observation_type, not is_dark)

    def _save_exposure(self, d1, d2, timestamp, exptime, eff_exptime, description, shutter_flag=True):
        # Define exposure
        self.pdb.add("exptime", float(exptime))
        self.pdb.add("timestamp", timestamp)
        self.pdb.add("effective_exptime", eff_exptime)
        self.pdb.add("wavelength", float(self.wavelength))
        self.pdb.add("currentInput", np.abs(np.mean(d1['CURR'])))
        self.pdb.add("currentOutput", np.abs(np.mean(d2['CURR'])))
        self.pdb.add("currentInputErr", np.std(d1['CURR']))
        self.pdb.add("currentOutputErr", np.std(d2['CURR']))
        self.pdb.add('shutter', shutter_flag)

        # Save the flip mount states
        for name in self.flipMountNames[1:]:
            fm = getattr(self, name, None)
            if fm is None:
                self.pdb.add(name, False)
                continue
            st = getattr(fm, "state", None)
            raw = getattr(st, "value", st)  # supports Enum-like and plain string states
            flag = str(raw).lower() == "on"
            self.pdb.add(name, flag)
        
        if self.zaberNDFilter is not None:
            self.pdb.add("ndFilter", self.zaberNDFilter.position)
        # self.pdb.add("pinholeMask", self.zaberPinholeMask.position)
        # self.pdb.add("focusPosition", self.zaberFocus.position)
        else:
            self.pdb.add("ndFilter","DISABLED")

        self.pdb.add("Description", description)
        
        # Commented on July 30, 2025, Kane's suggestion to not save lightcurve
        # self.pdb.save_lightcurve(d1, tag="currentInput")
        # self.pdb.save_lightcurve(d2, tag="currentOutput")
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
    
    def take_dark_per_sample(self, exptime, observation_type="dark"):
        """
        Take a dark exposure for a specified time.

        Args:
            exptime (float): Exposure time in seconds.

        """
        self.take_exposure_per_sample(exptime, observation_type=observation_type, is_dark=True)
        
    def wavelength_scan(self, start, end, step, exptime, observation_type="acq", nrepeats=1, range1=None, range2=None):
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
        wavelengthScan = np.arange(start,end+step, np.round(step,1))

        ##### Keysight Fine-Tunning
        if range1 is None: range1 = 200e-9 # B2987B
        if range2 is None: range2 = 2e-9 # B2983B

        # Flip the wavelength ordering filter
        # self.flipMount.f1.activate()
        
        # Auto-range
        self.set_wavelength(start-10)
        self.set_photodiode_scale(keysight_id=1)
        self.set_photodiode_scale(keysight_id=2)

        # wavelength auto range
        # nstops = 6
        # nv = int(wavelengthScan[wavelengthScan<750].size/nstops)
        # wav_auto_range = wavelengthScan[int(nv/2):int((nv-0.5)*nstops):nv]

        for wav in wavelengthScan:
            self.logger.info(f"wavelength-scan: start exposure of lambda = {wav:0.1f} nm with {nrepeats} repeats")
            self.set_wavelength(wav)

            # if wav in wav_auto_range:
            #     self.set_photodiode_scale()

            for _ in range(nrepeats):
                self.take_dark(exptime)
                self.take_exposure(exptime, observation_type=observation_type)
                self.take_dark(exptime)

            self.logger.info(f"wavelength-scan: finished exposure of lambda = {wav:0.1f} nm")

        # self.close_all_connections()
        self.logger.info("wavelength-scan measurement cycle completed.")
        self.logger.info("wavelength-scan saved on {self.pdb.run_data_file}")

    def wavelength_scan2(self, start, end, step, exptime, dark_time=None, observation_type="acq", nrepeats=100):
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
        wavelengthScan = np.arange(start,end+step, np.round(step,1))#, dtype=np.int32)

        # Flip the wavelength ordering filter
        # self.flipMount.f1.activate()
        
        # Auto-range
        self.set_wavelength(start-10)
        self.set_photodiode_scale(keysight_id=1)
        self.set_photodiode_scale(keysight_id=2)

        if dark_time is None:
            dark_time = exptime

        for wav in wavelengthScan:
            self.logger.info(f"wavelength-scan: start exposure of lambda = {wav:0.1f} nm with {nrepeats} repeats")
            self.set_wavelength(wav)

            # one baseline dark at the start of this wavelength
            self.take_dark_per_sample(dark_time)

            for _ in range(nrepeats):
                # light exposure
                self.take_exposure_per_sample(exptime, observation_type=observation_type)
                # closing dark for this repeat
                self.take_dark_per_sample(dark_time)

            self.logger.info(f"wavelength-scan: finished exposure of lambda = {wav:0.1f} nm")

        # self.close_all_connections()
        self.logger.info("wavelength-scan measurement cycle completed.")
        self.logger.info("wavelength-scan saved on {self.pdb.run_data_file}")

    def measure_pandora_tput_final(self, start, end, step, exptime, *, dark_time=None, observation_type="throughput", nrepeats=1):
        """
        Wrapper that runs the final overflow‑safe throughput routine.

        Parameters
        ----------
        start, end, step : float
            Wavelength scan definition in nm.
        exptime : float
            Light exposure time (seconds).
        dark_time : float | None, optional
            Dark block exposure time. If None, defaults to exptime.
        nrepeats : int, optional
            Number of LIGHT repeats per wavelength (defaults to 1).
        """
        # Lazy import to avoid circular imports during CLI boot
        from pandora.commands.measure_pandora_throughput import (
            measure_pandora_tput_final as _tput_final,
        )
        return _tput_final(
            self,
            start,
            end,
            step,
            exptime,
            dark_time=dark_time,
            nrepeats=nrepeats,
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # Charge Measurement Methods (CHAR mode)
    # ─────────────────────────────────────────────────────────────────────────────

    def charge_wavelength_scan(self, start, end, step, exptime, dark_time=None,
                                nrepeats=100, discharge_before_acquire=True):
        """
        Wavelength scan measuring charge instead of current.

        Uses the B2985B/B2987B electrometer in CHAR (coulomb meter) mode.
        Similar to wavelength_scan2() but:
        - Sets Keysight to CHAR mode
        - Discharges capacitor before each acquisition
        - Saves charge values instead of current

        Args:
            start (float): Start wavelength in nm.
            end (float): End wavelength in nm.
            step (float): Step size in nm.
            exptime (float): Integration time in seconds.
            dark_time (float, optional): Dark exposure time. Defaults to exptime.
            nrepeats (int): Number of repeats per wavelength.
            discharge_before_acquire (bool): If True, discharge capacitor before each acquisition.
        """
        self.logger.info(f"Starting charge wavelength scan from {start:.1f} nm to {end:.1f} nm with step {step:.1f} nm...")

        # Wavelength scan setup
        wavelengths = np.arange(start, end + step, np.round(step, 1))

        # Switch to charge mode
        self.logger.info("Switching Keysights to CHAR (charge) mode")
        self.keysight.k1.set_mode('CHAR')
        self.keysight.k2.set_mode('CHAR')

        # Auto-scale for charge ranges at starting wavelength
        self.set_wavelength(start - 10)
        self.logger.info("Auto-scaling charge ranges...")
        self.keysight.k1.auto_scale_charge()
        self.keysight.k2.auto_scale_charge()

        if dark_time is None:
            dark_time = exptime

        for wav in wavelengths:
            self.logger.info(f"charge-scan: start measurement at lambda = {wav:.1f} nm with {nrepeats} repeats")
            self.set_wavelength(wav)

            # Baseline dark at start of this wavelength
            self.take_charge_exposure(dark_time, is_dark=True,
                                       discharge=discharge_before_acquire,
                                       observation_type="charge_dark")

            for _ in range(nrepeats):
                # Light exposure
                self.take_charge_exposure(exptime, is_dark=False,
                                           discharge=discharge_before_acquire,
                                           observation_type="charge")
                # Closing dark for this repeat
                self.take_charge_exposure(dark_time, is_dark=True,
                                           discharge=discharge_before_acquire,
                                           observation_type="charge_dark")

            self.logger.info(f"charge-scan: finished measurement at lambda = {wav:.1f} nm")

        # Restore current mode
        self.logger.info("Restoring Keysights to CURR (current) mode")
        self.keysight.k1.set_mode('CURR')
        self.keysight.k2.set_mode('CURR')

        self.logger.info("Charge wavelength scan completed.")
        self.logger.info(f"Charge scan saved to {self.pdb.run_data_file}")

    def take_charge_exposure(self, exptime, is_dark=False, discharge=True,
                              observation_type="charge", warning=False):
        """
        Take a charge measurement and save every data point.

        Similar to take_exposure_per_sample() but:
        - Calls discharge() before acquire to zero the feedback capacitor
        - Reads CHAR data instead of CURR
        - Saves every data point with its timestamp for timeline analysis

        Args:
            exptime (float): Integration time in seconds.
            is_dark (bool): If True, keep shutter closed.
            discharge (bool): If True, discharge capacitor before acquiring.
            observation_type (str): Description for database.
            warning (bool): If True, this is a retry after overflow.
        """
        self.keysight.k1.on()
        self.keysight.k2.on()

        self.keysight.k1.set_acquisition_time(exptime)
        self.keysight.k2.set_acquisition_time(exptime)

        timestamp = datetime.now()

        if is_dark:
            self.close_shutter()
        else:
            self.open_shutter()

        self.timer.mark("ChargeExposure")

        # Discharge capacitors and acquire
        if discharge:
            self.keysight.k1.discharge()
            self.keysight.k2.discharge()
            time.sleep(0.05)  # Brief settling after discharge

        self.keysight.k1.acquire()
        self.keysight.k2.acquire()
        self.logger.info(f"Charge exposure set to last {self.keysight.k1.t_acq:.3f} seconds.")

        self.timer.sleep(exptime)
        self.close_shutter()
        eff_exptime = self.timer.elapsed_since("ChargeExposure")

        # Read charge data
        d1 = self.keysight.k1.read_data(wait=True)
        d2 = self.keysight.k2.read_data(wait=True)

        self.logger.info(f"Charge exposure ended after {eff_exptime:.3f} seconds.")

        # Check for overflow and retry with auto-scale if needed
        if (np.abs(np.mean(d1['CHAR'])) > 1e36) and (not warning):
            self.logger.warning("Overflow in Keysight 1 (charge mode)")
            self.keysight.k1.auto_scale_charge()
            self.take_charge_exposure(exptime, is_dark=is_dark, discharge=discharge,
                                       observation_type=observation_type, warning=True)
            return

        if (np.abs(np.mean(d2['CHAR'])) > 1e36) and (not warning):
            self.logger.warning("Overflow in Keysight 2 (charge mode)")
            self.keysight.k2.auto_scale_charge()
            self.take_charge_exposure(exptime, is_dark=is_dark, discharge=discharge,
                                       observation_type=observation_type, warning=True)
            return

        # Save every data point individually (for timeline analysis)
        for i in range(len(d1['CHAR'])):
            self._save_charge_exposure(
                d1['time'][i], d1['CHAR'][i], d2['CHAR'][i],
                timestamp, exptime, eff_exptime,
                observation_type, not is_dark
            )

    def _save_charge_exposure(self, sample_time, charge1, charge2,
                               timestamp, exptime, eff_exptime,
                               description, shutter_flag=True):
        """
        Save a single charge data point to database.

        Saves individual data points with their relative timestamps,
        enabling timeline reconstruction for shutter timing analysis.

        Args:
            sample_time (float): Relative time of this sample (seconds from acquisition start).
            charge1 (float): Charge value from Keysight 1 (Coulombs).
            charge2 (float): Charge value from Keysight 2 (Coulombs).
            timestamp: Acquisition start timestamp.
            exptime: Requested exposure time.
            eff_exptime: Actual elapsed time.
            description: Observation type description.
            shutter_flag: True if shutter was open.
        """
        self.pdb.add("exptime", float(exptime))
        self.pdb.add("timestamp", timestamp)
        self.pdb.add("effective_exptime", eff_exptime)
        self.pdb.add("sampleTime", float(sample_time))
        self.pdb.add("wavelength", float(self.wavelength))
        self.pdb.add("chargeInput", float(np.abs(charge1)))
        self.pdb.add("chargeOutput", float(np.abs(charge2)))
        self.pdb.add('shutter', shutter_flag)
        self.pdb.add("measurementMode", "CHAR")

        # Save the flip mount states (same as _save_exposure)
        for name in self.flipMountNames[1:]:
            fm = getattr(self, name, None)
            if fm is None:
                self.pdb.add(name, False)
                continue
            st = getattr(fm, "state", None)
            raw = getattr(st, "value", st)
            flag = str(raw).lower() == "on"
            self.pdb.add(name, flag)

        if self.zaberNDFilter is not None:
            self.pdb.add("ndFilter", self.zaberNDFilter.position)
        else:
            self.pdb.add("ndFilter", "DISABLED")

        self.pdb.add("Description", description)

        self.write_exposure()

    ## TODO
    ## Under construction
    ## First Draft
    def solar_cell_qe_curve(self, start, end, step, exptime, nrepeats=1, range1=None, range2=None):
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
        wavelengthScan = np.arange(start,end+step, np.round(step,1))

        ##### Keysight Fine-Tunning
        if range1 is None: range1 = 200e-9 # B2987B
        if range2 is None: range2 = 2e-9 # B2983B
    
        # for wav in wavelengthScan:
        #     self.logger.info(f"solar-cell-qe-curve: start exposure of lambda = {wav:0.1f} nm with {nrepeats} repeats")
        #     self.set_wavelength(wav)
        #     if wav>700:
        #         # Check what is the IR filter code
        #         self.enable_2nd_order_filter()

        #     self.keysight.k1.set_rang(range1)
        #     self.keysight.k2.set_rang(range2)

        #     # make sure NIST diode is out of the beam
        #     self.flipMount.nist.deactivate()
        #     for _ in range(nrepeats):
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

        # self.close_all_connections()
        self.logger.info("solar-cell-qe-curve measurement cycle completed.")
        self.logger.info("solar-cell-qe-curve saved on {self.pdb.run_data_file}")

    # TODO: Check what is the IR filter code
    def enable_2nd_order_filter(self, state=True):
        """
        Put the Order-Block(UV) filter on the optical path.
        """
        if state:
            self.flipOrderBlockFilter.activate()
        else:
            self.flipOrderBlockFilter.deactivate()
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

    def set_wavelength(self, wavelength, timeout=0.5):
        """
        Set the monochromator to a specific wavelength.
        """
        self.timer.mark("Wavelength")
        if wavelength>self.monochromator.wav_second_order_filter:
            self.enable_2nd_order_filter()
        else:
            self.enable_2nd_order_filter(state=False)

        self.monochromator.move_to_wavelength(wavelength, timeout)
        # Check how long we should wait here
        # self.monochromator.wait_until_ready()
        self.wavelength = wavelength
        self.logger.debug(f"Set wavelength to {wavelength} nm took {self.timer.elapsed_since('Wavelength'):.3f} seconds.")
        pass

    def get_wavelength(self, query=True):
        """
        Get the current wavelength of the monochromator.
        """
        if query:
            self.wavelength = self.monochromator.get_wavelength()
        else:
            self.wavelength = self.monochromator.wavelength
        return self.wavelength
    
    def set_nd_filter(self,nd_filter_name):
        """
        Move the Zaber stage to a new position for the ND filter.
        Args:
            nd_filter_name (str): The name of the ND filter to move to.
        """
        self.zaberNDFilter.move_to_slot(nd_filter_name)
        pass

    def set_pinhole_mask(self, mask_name):
        """
        Move the Zaber stage to a new position for the ND filter.
        Args:
            mask_name (str): The name of the pinhole mask to move to.
        """
        # self.zaberPinholeMask.move_to_slot(mask_name)
        pass

    def set_photodiode_scale(self, keysight_id=1, scale_down=None, scale=None):
        """
        Adjust the scale of the specified Keysight photodiode channel.

        Args:
            keysight_id (int): 1 for k1, 2 for k2.
            scale_down (float, optional): Factor to scale down the current range.
            scale (float, optional): Set an explicit scale value.
        """
        ks = self.keysight.k1 if keysight_id == 1 else self.keysight.k2

        if scale is not None:
            ks.set_rang(scale)
        elif scale_down is not None:
            current_scale = float(ks.get_rang())
            ks.set_rang(current_scale / scale_down)
        else:
            self.open_shutter()
            ks.auto_scale()
            self.close_shutter()
        

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
