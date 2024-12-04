# states/flipmount_state.py
import utils.logger as logger
from .states import State

class FlipMountState:
    """ FlipMountState class to handle communication with Thorlabs FlipMount devices.

    Args:
        name (str): Name of the labjack port, e.g. "F01"
        labjack (LabJack): LabJack object to handle communication with the device.

    Example:
        labjack = LabJack()
        flip_mount = FlipMountState(name="F01", labjack=labjack)
        flip_mount.get_device_info()

        # flips the state of the flip mount

        # activate puts the flip mount in the ON state (on the optical path)
        flip_mount.activate()

        # deactivate puts the flip mount in the OFF state (off the optical path)
        flip_mount.deactivate()

        # Get the curent state of the flip mount
        flip_mount.get_state()

        # Close the labjack connection
        flip_mount.close()
    """
    def __init__(self, name, labjack):
        self.labjack = labjack
        self.codename = name  
        self.state = State.UNINITIALIZED
        self.logger = logger.get_logger(f"FlipMountState-{name}")
        self.initialize()

    def initialize(self):
        self.logger.info(f"Initializing FlipMountState {self.codename}.")
        self.set_state(State.IDLE)

        # Set the flip-mount to output mode
        self.labjack.write(f"{self.codename}_DIRECTION", 1)

        self.get_state()

    def activate(self):
        if self.state == State.OFF:
            self.logger.info(f"Activating Flip Mount {self.codename}.")
            self.labjack.send_binary_signal()
            self.set_state(State.ON)
        
        elif self.state == State.ON:
            self.logger.info(f"Flip Mount is already activated {self.codename}.")
    
        elif self.state == State.FAULT:
            self.logger.error(f"Error activating Flip Mount {self.codename}.")
        
        elif self.state == State.IDLE:
            self.get_state()
            self.activate()

    def deactivate(self):
        if self.state == State.ON:
            self.logger.info(f"Deactivating Flip Mount {self.codename}.")
            self.labjack.send_binary_signal()
            self.set_state(State.OFF)
        
        elif self.state == State.OFF:
            self.logger.info(f"Flip Mount is already deactivated {self.codename}.")
        
        elif self.state == State.FAULT:
            self.logger.error(f"Error deactivating Flip Mount {self.codename}.")
        
        elif self.state == State.IDLE:
            self.get_state()
            self.deactivate()

    def set_error(self):
        self.logger.error(f"Setting state to fault for Flip Mount {self.codename}.")
        self.set_state(State.FAULT)

    def reset(self):
        if self.state == State.FAULT:
            self.logger.info(f"Resetting Flip Mount from fault state {self.codename}.")
            self.set_state(State.IDLE)
            # Set the flip-mount to output mode
            self.labjack.write(f"{self.codename}_DIRECTION", 1)
            
    def get_state(self):
        try:
            self.logger.info(f"Querying Flip Mount state {self.codename}.")
            value = int(self.labjack.read(self.codename))
            self.set_state(State.ON if value == 1 else State.OFF)
            return self.state
        except:
            self.logger.error(f"Error querying Flip Mount {self.codename} state.")
            self.set_state(State.FAULT)
            return self.state

    def get_device_info(self):
        self.labjack.get_device_info()
        print(f"Flip Mount name: {self.codename}")
        print(f"Flip Mount {self.codename} state: {self.state.value}")

    def close(self):
        self.logger.info(f"Closing Flip Mount {self.codename}.")
        self.set_state(State.IDLE)
        # Set the flip-mount to input mode
        self.labjack.write(f"{self.codename}_DIRECTION", 0)
        self.set_state(State.UNINITIALIZED)

    def set_state(self, new_state):
        valid_transitions = {
            State.UNINITIALIZED: [State.IDLE],
            State.IDLE: [State.ON, State.OFF, State.FAULT, State.UNINITIALIZED],
            State.ON: [State.OFF, State.FAULT],
            State.OFF: [State.ON, State.FAULT],
            State.FAULT: [State.IDLE]
        }

        if new_state in valid_transitions[self.state]:
            self.state = new_state
            self.logger.info(f"State changed to {self.state.value}")
        else:
            self.logger.error(f"Invalid state transition from {self.state.value} to {new_state.value}")

if __name__ == "__main__":
    from labjackHandler import LabJack
    from config import labjack_ip_address

    ip_address = labjack_ip_address
    labjack = LabJack(ip_address)

    # Initialize the flip mount
    flip_mount = FlipMountState(name="F01", labjack=labjack)
    flip_mount.get_device_info()

    # flips the state of the flip mount
    # activate puts the flip mount in the ON state (on the optical path)
    flip_mount.activate()
    # deactivate puts the flip mount in the OFF state (off the optical path)
    flip_mount.deactivate()

    # Get the curent state of the flip mount
    flip_mount.get_state()

    # Close the FIO1 output connection
    flip_mount.close()