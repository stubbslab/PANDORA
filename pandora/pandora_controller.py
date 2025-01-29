## Make Pandora Class
from states.flipmount_state import FlipMountState
from states.shutter_state import ShutterState
from states.keysight_state import KeysightState
from commands.monochromator import MonochromatorController
from commands.zaberstages import ZaberController
from states.labjack_handler import LabJack
from states.states_map import State
from utils.logger import initialize_central_logger
from utils.operation_timer import OperationTimer

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

    def __init__(self, config_file='default.yaml'):
        # Load configuration (IP addresses, device IDs, calibration files, etc.)
        self.config = self._load_config(config_file)

        # Instantiate subsystem controllers using config parameters.
        self.initialize_subsystems()

        # Initialize logger
        self.logger = self._initialize_logger()

        # Initializer a timer
        self.timer = OperationTimer(min_interval=1/self.max_operation_freq, name=f"Pandora")

    def _load_config(self, config_file):
        # Parse a config file (JSON, YAML, etc.) with device parameters
        # Return a config dictionary.
        pass

    def _initialize_logger(self):
        # Setup and return a logger instance for the Pandora class
        logging_config = self.config['logging']
        self.logger = initialize_central_logger(logging_config['logfile'], logging_config['level'])
        pass

    def initialize_subsystems(self):
        """
        Create and initialize all subsystem objects. This may call constructors and 
        run initial setup routines for each device. After this call, we should have
        objects ready to connect.
        """
        # Create one LabJack object to be shared among shutter, flip mounts, etc.
        labjack_ip = self.config['labjack_ip_address']
        self.labjack = LabJack(ip_address=labjack_ip)

        # Shutter
        self.shutter = ShutterState(
            name=self.config['shutter']['labjack_port'],
            labjack=self.labjack
        )

        # Flip Mounts
        self.flipMount = type('FlipMountContainer', (), {})()
        flipmount_config = self.config['flipmounts']
        self.flipMount.f1 = FlipMountState(
            name=flipmount_config['F01']['labjack_port'],
            labjack=self.labjack
        )
        self.flipMount.f2 = FlipMountState(
            name=flipmount_config['F02']['labjack_port'],
            labjack=self.labjack
        )
        # Add more flip mounts as needed...

        # Keysights
        self.keysight = type('KeysightContainer', (), {})()
        ks_config = self.config['keysights']
        self.keysight.k1 = KeysightState(
            name="K01",
            keysight_ip=ks_config['K01']['keysight_ip'],
            timeout_ms=ks_config['K01']['timeout_ms']
        )
        self.keysight.k2 = KeysightState(
            name="K02",
            keysight_ip=ks_config['K02']['keysight_ip'],
            timeout_ms=ks_config['K02']['timeout_ms']
        )
        # Add more Keysights as needed...

        # Zaber Stages
        # self.zaber = type('ZaberContainer', (), {})()
        # zb_config = self.config['zaber_stages']
        # self.zaber.z1 = ZaberStageState(
        #     name="Z1",
        #     zaber_ip=zb_config['Z1']['zaber_ip'],
        #     device_number=zb_config['Z1']['device_number']
        # )
        # self.zaber.z2 = ZaberStageState(
        #     name="Z2",
        #     zaber_ip=zb_config['Z2']['zaber_ip'],
        #     device_number=zb_config['Z2']['device_number']
        # )
        # # Add more stages as needed...

        # # Monochromator
        # mono_conf = self.config['monochromator']
        # self.monochromator = MonochromatorController(
        #     usb_port=mono_conf['usb_port'],
        #     baud_rate=mono_conf['baud_rate'],
        #     timeout=mono_conf['timeout']
        # )

        # # Spectrograph
        # spec_conf = self.config['spectrograph']
        # self.spectrograph = SpectrographState(
        #     usb_port=spec_conf['usb_port'],
        #     baud_rate=spec_conf['baud_rate'],
        #     timeout=spec_conf['timeout']
        # )

        self.logger.info("All subsystems have been initialized.")
        pass

    def go_home(self):
        """
        Set the PANDORA system to a known "home" state:
        - All flip mounts: OFF (out of the optical path)
        - Shutter: ON (open)
        - Keysights: IDLE (no measurement)
        - Monochromator: send to home position
        """
        self.logger.info("Moving system to home state.")

        # Flip mounts OFF
        # Assuming flipMount.f1, flipMount.f2, etc. exist
        # and OFF is achieved by calling deactivate()
        for attr_name in dir(self.flipMount):
            if attr_name.startswith('f'):
                flipmount = getattr(self.flipMount, attr_name, None)
                if flipmount:
                    self.logger.info(f"Deactivating flip mount {attr_name}")
                    flipmount.deactivate()

        # Shutter ON
        # Assuming ON state achieved by calling activate()
        self.logger.info("Activating shutter.")
        self.shutter.activate()

        # Keysights IDLE
        # Assuming IDLE can be achieved by resetting or deactivating keysight
        for attr_name in dir(self.keysight):
            if attr_name.startswith('k'):
                keysight = getattr(self.keysight, attr_name, None)
                if keysight:
                    self.logger.info(f"Setting keysight {attr_name} to IDLE")
                    keysight.deactivate()  # Deactivate sets OFF
                    keysight.reset()       # Reset moves from FAULT->IDLE if needed, or no-op if not in fault.
                    # If KeysightState does not have a direct method to set IDLE, 
                    # ensure OFF or IDLE states are acceptable. If not, you may need a dedicated method.

        # Monochromator sent home
        # Assuming MonochromatorState class has a method like home() or set_wavelength(0)
        self.logger.info("Homing monochromator.")
        self.monochromator.go_home()
        # Check how long we should wait here
        # self.monochromator.wait_until_ready()

        self.logger.info("System is now in the home state.")

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
        if counts is None and exptime is None:
            raise ValueError("Must provide either 'counts' or 'exptime'.")

        self.timer.mark("Exposure")

        # Assume we have a dedicated keysight for measurement.
        # Let's say keysight.k1 is used for measuring flux/charge.
        # Set keysight to ON (measurement mode)
        if self.keysight.k2.get_state() != State.ON:
            self.logger.info("Activating Keysight for measurement.")
            self.keysight.k2.activate()

        # Open the shutter if not already open
        self.logger.info("Opening shutter for exposure.")
        self.open_shutter()
        self.timer.shutter.mark("Shutter")

        # PLACEHOLDER CODE: Replace with actual measurement loop
        if counts is not None:
            # Integrate until threshold counts is reached
            self.logger.info(f"Starting exposure until {counts} ADU is reached.")
            total_charge = 0.0
            # Hypothetical continuous measurement loop
            while total_charge < counts:
                # This is conceptual. Replace with actual keysight measurement commands.
                new_reading = self.keysight.k1.read_current_charge()
                total_charge += new_reading
                self.logger.debug(f"Integrated charge: {total_charge} ADU")

                # Optional timeout or max integration guard
                if self.timer.elapsed_since("Shutter") > 600:  # 10 minutes max, for example
                    self.logger.warning("Exposure timed out before reaching target counts.")
                    break

            self.logger.info(f"Exposure ended. Integrated charge: {total_charge} ADU")

        elif exptime is not None:
            # Integrate for a fixed exposure time
            self.logger.info(f"Starting exposure for {exptime} seconds.")
            if self.timer.elapsed_since("Shutter")<exptime:
                self.timer.sleep(exptime-self.timer.elapsed_since("Shutter"))

            # One final reading at the end, if needed
            total_charge = self.keysight.k1.read_total_charge()
            self.logger.info(f"Exposure ended after {exptime} s. Integrated charge: {total_charge} ADU")

        # Close shutter and put keysight to IDLE/OFF
        self.logger.info("Closing shutter and returning keysight to IDLE state.")
        self.shutter.deactivate()  # Shutter OFF
        shutter_time = self.timer.elapsed_since("Shutter")

        self.keysight.k1.deactivate()  # Keysight OFF
        print(f"The exposure took {self.timer.elapsed_since('Exposure'):.3f} seconds.")
        print(f"The shuter was open for {shutter_time:.3f} seconds.")
        print(f"The integrated charge was {total_charge} ADU.")
        return total_charge, shutter_time

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
        self.shutter.activate()
        pass

    def close_shutter(self):
        """
        Close the shutter to block light.
        """
        self.shutter.deactivate()
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
        self.monochromator.set_wavelength(wavelength, timeout)
        # Check how long we should wait here
        # self.monochromator.wait_until_ready()
        print(f"Set wavelength to {wavelength} nm took {self.timer.elapsed_since('Wavelength'):.3f} seconds.")
        pass
    
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