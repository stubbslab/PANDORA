# states/shutter_state.py
import utils.logger as logger
from .states import State

class ShutterState:
    """ ShutterState class to handle state and communication with Thorlabs Shutter devices.
    https://www.thorlabs.com/thorproduct.cfm?partnumber=SHB1T#ad-image-0

    Args:
        name (str): Name of the labjack port, e.g. "F03"
        labjack (LabJack): LabJack object to handle communication with the device.

    Example:
        labjack = LabJack()
        shutter = ShutterState(name="F03", labjack=labjack)
        shutter.get_device_info()

        # Activate the shutter
        shutter.activate()

        # Deactivate the shutter
        shutter.deactivate()

        # Get the curent state of the shutter
        shutter.get_state()

        # Close the labjack connection
        shutter.close()
    """
    def __init__(self, name, labjack):
        self.labjack = labjack
        self.codename = name  
        self.state = State.UNINITIALIZED
        self.logger = logger.get_logger(f"Shutter-{name}")
        self.initialize()

    def initialize(self):
        self.logger.info(f"Initializing ShutterState {self.codename}.")
        self.set_state(State.IDLE)
        self.get_state()

    def activate(self):
        if self.state == State.OFF:
            self.logger.info(f"Activating Shutter {self.codename}.")
            self.labjack.send_high_signal()
            self.set_state(State.ON)
        
        elif self.state == State.ON:
            self.logger.info(f"Shutter is already activated {self.codename}.")
    
        elif self.state == State.FAULT:
            self.logger.error(f"Error activating Shutter {self.codename}.")
        
        elif self.state == State.IDLE:
            self.get_state()
            self.activate()

    def deactivate(self):
        if self.state == State.ON:
            self.logger.info(f"Deactivating Shutter {self.codename}.")
            self.labjack.send_low_signal()
            self.set_state(State.OFF)
        
        elif self.state == State.OFF:
            self.logger.info(f"Shutter is already deactivated {self.codename}.")
        
        elif self.state == State.FAULT:
            self.logger.error(f"Error deactivating Shutter {self.codename}.")
        
        elif self.state == State.IDLE:
            self.get_state()
            self.deactivate()

    def set_error(self):
        self.logger.error(f"Setting state to fault for Shutter {self.codename}.")
        self.set_state(State.FAULT)

    def reset(self):
        if self.state == State.FAULT:
            self.logger.info(f"Resetting Shutter from fault state {self.codename}.")
            self.set_state(State.IDLE)

    def get_state(self):
        try:
            self.logger.info(f"Querying Shutter state {self.codename}.")
            value = int(self.labjack.read(self.codename))
            self.set_state(State.ON if value == 1 else State.OFF)
            return self.state
        except:
            self.logger.error(f"Error querying Shutter {self.codename} state.")
            self.set_state(State.FAULT)
            return self.state

    def get_device_info(self):
        self.labjack.get_device_info()
        print(f"Shutter name: {self.codename}")
        print(f"Shutter {self.codename} state: {self.state.value}")

    def close(self):
        self.logger.info(f"Closing Shutter {self.codename}.")
        # Set the flip-mount to input mode
        self.labjack.write(f"{self.codename}_DIRECTION", 0)
        self.set_state(State.IDLE)
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

    # Initialize the shutter
    shutter = ShutterState(name="FIO03", labjack=labjack)
    shutter.get_device_info()

    # Activate the shutter
    shutter.activate()

    # Deactivate the shutter
    shutter.deactivate()

    # Get the curent state of the shutter
    shutter.get_state()

    # Close the labjack connection
    shutter.close()