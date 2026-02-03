# states/flipmount_state.py
import logging
from pandora.utils.operation_timer import OperationTimer

class FlipMountState:
    """ FlipMountState class to handle communication with Thorlabs FlipMount devices.

    Args:
        labjack_port (str): Name of the labjack port, e.g. "F01"
        labjack (LabJack): LabJack object to handle communication with the device.

    Example:
        labjack = LabJack()
        fm = FlipMountState(labjack_port="F01", labjack=labjack)
        fm.get_device_info()

        # flips the state of the flip mount

        # activate puts the flip mount in the ON state (on the optical path)
        fm.activate()

        # deactivate puts the flip mount in the OFF state (off the optical path)
        fm.deactivate()

        # Close the labjack connection
        fm.close()
    """
    def __init__(self, labjack_port, labjack, invert_logic=False):
        if labjack_port is None:
            raise ValueError("Flip Mount name cannot be None.")
        if labjack is None:
            raise ValueError("LabJack cannot be None.")
        
        ## Initialize the Flip Mount State Parameters
        self.labjack = labjack
        self.labjack_port = labjack_port  
        self.logger = logging.getLogger(f"pandora.flipmount.{labjack_port}")
        
        ## Invert logic is used to set the state of the flip mount
        ## to ON when the signal is low and OFF when the signal is high.
        self.invert_logic = invert_logic

        ## Safety measure for SHB1 shutter
        self.max_operation_freq = 2 # Hz
        self.timer = OperationTimer(min_interval=1/self.max_operation_freq, name=f"FlipMount-{labjack_port}")

        self.initialize()

    def initialize(self):
        """ Initialize the FlipMountState object.
        Steps:
        1. Get the current state of the flip mount.
        """
        self.logger.info(f"Initializing FlipMount {self.labjack_port}.")
        
        if self.is_powered_on():
            self.set_state("ON")
            # Ensure we don't operate too fast
            self.timer.sleep(1/self.max_operation_freq)
        else:
            raise RuntimeError(f"Flip Mount {self.labjack_port} is not powered on.")
            # print(f"Error: Flip Mount {self.labjack_port} is not powered on. Setting state to OFF.")

    def activate(self):
        self.logger.info(f"Activating FlipMount {self.labjack_port}.")
        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast {self.labjack_port}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.debug(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")

        if not self.invert_logic:
            self.logger.debug(f"Sending low signal to Flip Mount {self.labjack_port}.")
            self.labjack.send_low_signal(self.labjack_port)
        else:
            self.logger.debug(f"Sending high signal to Flip Mount {self.labjack_port}.")
            self.labjack.send_high_signal(self.labjack_port)

        self.timer.update_last_operation_time()
        self.set_state("ON")

    def deactivate(self):
        self.logger.info(f"Deactivating FlipMount {self.labjack_port}.")
        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast {self.labjack_port}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.warning(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")
        
        if not self.invert_logic:
            self.logger.debug(f"Sending high signal to Flip Mount {self.labjack_port}.")
            self.labjack.send_high_signal(self.labjack_port)
        else:
            self.logger.debug(f"Sending low signal to Flip Mount {self.labjack_port}.")
            self.labjack.send_low_signal(self.labjack_port)

        self.timer.update_last_operation_time()
        self.set_state("OFF")

    @property
    def state(self):
        """Return the internally tracked state of the flip mount."""
        self.logger.debug(f"Returning internal state for Flip Mount {self.labjack_port}: {self._state}")
        return self._state

    def set_state(self, state):
        """Manually set the internal state of the flip mount."""
        if state not in ("ON", "OFF"):
            raise ValueError("State must be 'ON' or 'OFF'.")
        self.logger.debug(f"Manually setting internal state for Flip Mount {self.labjack_port} to {state}")
        self._state = state

    def get_device_info(self):
        self.labjack.get_device_info()
        print(f"Flip Mount name: {self.labjack_port}")
        print(f"Flip Mount {self.labjack_port} and state: {self.state}")

    def close(self):
        self.logger.info(f"Closing Flip Mount {self.labjack_port}.")
        self.deactivate()
        self.set_state("OFF")

    def is_powered_on(self) -> bool:
        """Check if the flip mount is powered on."""
        # send command to low state
        self.labjack.write(self.labjack_port, 0)
        
        # wait for the command to take effect
        self.timer.sleep(1 / self.max_operation_freq)  # wait for the command to take effect

        # flip the state to high if it is on
        self.labjack.read(self.labjack_port)

        # read now the state
        power_status = int(self.labjack.read(self.labjack_port)) == 1

        if power_status:
            self.logger.info(f"Flip Mount {self.labjack_port} is powered ON.")
        else:
            self.logger.warning(f"Flip Mount {self.labjack_port} is powered OFF.")
        
        # update the timer of last operation
        self.timer.update_last_operation_time()
        return power_status


if __name__ == "__main__":
    from labjack_handler import LabJack
    import time
    # from config import labjack_ip_address
    from utils.logger import initialize_central_logger 
    
    # Set up logging
    initialize_central_logger("../flipmount.log", "INFO")

    # Initialize the LabJack connection
    ip_address = "169.254.84.89"
    labjack = LabJack(ip_address)
    # labjack.send_low_signal("FIO3")

    # Initialize the flip mount
    fm2 = FlipMountState("FIO02", labjack=labjack)
    fm3 = FlipMountState("FIO03", labjack=labjack)
    fm4 = FlipMountState("FIO04", labjack=labjack)


    for f in [fm2, fm3, fm4]:   #fm1
        f.activate()

    print("Sleep for 2 sec") 
    time.sleep(2)

    for f in [fm2, fm3, fm4]:  #fm1
        f.deactivate()

    # Close the FIO1 output connection
    # fm.close()
    labjack.close()

