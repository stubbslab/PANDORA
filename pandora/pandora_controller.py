import logging
import time
from datetime import datetime
import numpy as np

## Make Pandora Class
from states.flipmount_state import FlipMountState
from states.shutter_state import ShutterState
from commands.keysight import KeysightState
from commands.monochromator import MonochromatorController
from commands.zaberstages import ZaberController
from states.labjack_handler import LabJack
from states.states_map import State
from utils.logger import initialize_central_logger
from utils.operation_timer import OperationTimer
from database.db import PandoraDatabase

## TODOS:
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
    def __init__(self, config_file='default.yaml', run_id=None, verbose=True):
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
        root = self.get_config_value('database', 'db_path')
        self.pdb = PandoraDatabase(run_id=run_id, root_path=root)
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
        Create and initialize all subsystem objects. This may call constructors and 
        run initial setup routines for each device. After this call, we should have
        objects ready to connect.
        """
        # Query the config for IP addresses and other parameters
        mono_config = self.get_config_section('monochromator')
        ks_config = self.get_config_section('keysights')
        zb_config = self.get_config_section('zaber_stages')
        
        # LabJack Controlled Devices
        # Port names for each subsystem
        labjack_ip = self.get_config_value('labjack', 'ip_address')
        shutter_port = self.get_config_value('labjack', 'shutter')
        fm1_port = self.get_config_value('labjack', 'flipmount1')
        fm2_port = self.get_config_value('labjack', 'flipmount2')
        fm3_port = self.get_config_value('labjack', 'flipmount3')
        # Add more ports as needed...

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
        self.flipMount = type('FlipMountContainer', (), {})()
        self.flipMount.deviceNames = ['fm1', 'fm2', 'fm3']
        self.flipMount.f1 = FlipMountState(fm1_port, labjack=self.labjack)
        self.flipMount.f2 = FlipMountState(fm2_port, labjack=self.labjack)
        self.flipMount.f3 = FlipMountState(fm3_port, labjack=self.labjack)
        # Add more flip mounts as needed...

        # Keysights
        self.keysight = type('KeysightContainer', (), {})()
        self.keysight.deviceNames = list(ks_config.keys())
        # print(k1_config['settings'])
        self.keysight.k1 = KeysightState(**k1_config)
        self.keysight.k2 = KeysightState(**k2_config)
        # Add more Keysights as needed...

        # Zaber Stages
        self.zaber = type('ZaberContainer', (), {})()
        self.zaber.deviceNames = list(zb_config.keys())
        self.zaber.z1 = ZaberController(**z1_config)
        # self.zaber.z2 = ZaberController(**z2_config)
        # self.zaber.z3 = ZaberController(**z3_config)
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

        """
        self.keysight.k1.on()  # Keysight 1 ON
        self.keysight.k2.on()  # Keysight 2 ON

        # Set acquisition time if exptime is provided
        self.keysight.k1.set_acquisition_time(exptime)
        self.keysight.k2.set_acquisition_time(exptime)

        # Define exposure
        self.pdb.add("exptime", exptime)
        self.pdb.add("Description", observation_type)

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
        self._save_exposure(d1, d2, eff_exptime, not is_dark)
        pass

    def _save_exposure(self, d1, d2, eff_exptime, shutter_flag=True):
        self.pdb.add("wavelength", self.get_wavelength())
        self.pdb.add("photoInput", np.mean(d1['CURR']))
        self.pdb.add("photoOutput", np.mean(d2['CURR']))
        self.pdb.add("photoInputErr", np.std(d1['CURR']))
        self.pdb.add("photoOutputErr", np.std(d2['CURR']))
        self.pdb.add("zaber", self.zaber.z1.position)
        self.pdb.add("FM1", self.flipMount.f1.state.value)
        self.pdb.add("FM2", self.flipMount.f2.state.value)
        self.pdb.add("FM3", self.flipMount.f3.state.value)
        self.pdb.add("shutter_opened", shutter_flag)
        self.pdb.add("effective_exptime", eff_exptime)
        self.pdb.save_lightcurve(d1, tag="photoInput")
        self.pdb.save_lightcurve(d2, tag="photoOutput")
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

    def write_exposure(self):
        """
        Write the exposure data to the database.
        """
        self.pdb.write_exposure()
        pass

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
        if hasattr(self, 'flipMount') and self.flipMount is not None:
            for attr_name in dir(self.flipMount):
                if attr_name.startswith('f'):
                    fm = getattr(self.flipMount, attr_name, None)
                    if fm:
                        self.logger.info(f"Closing flip mount {attr_name} connection.")
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
        if hasattr(self, 'zaber') and self.zaber is not None:
            for attr_name in dir(self.zaber):
                if attr_name.startswith('z'):
                    zb = getattr(self.zaber, attr_name, None)
                    if zb:
                        self.logger.info(f"Closing zaber stage {attr_name} connection.")
                        zb.close()

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

    def switch_flipmount(self, mount_name):
        """
        Switch the flip mount to a new position.
        """
        flipmount = getattr(self.flipMount, mount_name, None)
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
    
    def move_to_nd_filter(self,nd_filter_name):
        """
        
        """
        self.zaber.z1.move_to_slot(nd_filter_name)

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