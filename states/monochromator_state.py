# states/monochromator_state.py
import logger
from states import State

# TODO: Check the labjack connection for the monochromator
# TODO: Implement activate/deactive methods for the monochromator
# TODO: Implement get_state

from labjackHandler import LabJack

class MonochromatorState:
    """ MonochromatorState class to handle communication with XXX device.

    Args:
        usb_id (str): USB address of the LabJack device.
        name (str): Name of the monochromator labjack digital input, e.g. "DIO0"
    
    Example:
        mono = MonochromatorState("ANY", "DIO0")
        mono.get_device_info()
        mono.activate()
        mono.deactivate()
        mono.get_state()
        mono.close()

    """
    def __init__(self, usb_id, name="DIO0"):
        self.labjack = LabJack(usb_address=usb_id)
        self.codename = name
        self.state = State.UNINITIALIZED
        self.logger = logger.get_logger(f"Monochromator")
        self.initialize()

    def initialize(self):
        self.logger.info(f"Initializing MonochromatorState.")
        self.set_state(State.IDLE)
        self.get_state()

    def activate(self):
        self.get_state()
        if self.state == State.OFF or self.state == State.IDLE:
            self.labjack.send_high_signal()
            self.set_state(State.ON)
        
        elif self.state == State.ON:
            self.logger.info(f"Monochromator is already activated.")
    
        elif self.state == State.FAULT:
            self.logger.error(f"Error activating Monochromator.")

    def deactivate(self):
        if self.state == State.ON or self.state == State.IDLE:
            self.labjack.send_low_signal()
            self.set_state(State.OFF)
        
        elif self.state == State.OFF:
            self.logger.info(f"Monochromator is already deactivated.")
        
        elif self.state == State.FAULT:
            self.logger.error(f"Error deactivating Monochromator.")

    def set_error(self):
        self.logger.error(f"Setting state to fault for Monochromator.")
        self.set_state(State.FAULT)

    def reset(self):
        if self.state == State.FAULT:
            self.logger.info(f"Resetting Monochromator from fault state.")
            self.set_state(State.IDLE)

    def get_state(self):
        try:
            self.logger.info(f"Querying Monochromator state.")
            value = int(self.labjack.read(self.codename))
            self.set_state(State.ON if value == 1 else State.OFF)
            return self.state
        except:
            self.logger.error(f"Error querying Monochromator {self.codename} state.")
            self.set_state(State.FAULT)
            return self.state

    def get_device_info(self):
        self.labjack.get_device_info()
        # print(f"Monochromator name: {self.codename}")
        print(f"Monochromator {self.codename} state: {self.state.value}")

    def close(self):
        self.logger.info(f"Closing Monochromator.")
        # check if the system is in fault state
        self.reset()
        # deactivate the monochromator if it is on
        self.deactivate()
        # set the the state to idle to transition to the next state
        self.set_state(State.IDLE)
        # close the labjack connection
        self.labjack.close()
        # set the state to uninitialized
        self.set_state(State.UNINITIALIZED)

    def set_state(self, new_state):
        valid_transitions = {
            State.UNINITIALIZED: [State.IDLE],
            State.IDLE: [State.ON, State.OFF, State.FAULT, State.UNINITIALIZED, State.CALIBRATING],
            State.ON: [State.OFF, State.FAULT],
            State.OFF: [State.ON, State.FAULT],
            State.FAULT: [State.IDLE],
            State.CALIBRATING: [State.IDLE],
        }

        if new_state in valid_transitions[self.state]:
            self.state = new_state
            self.logger.info(f"State changed to {self.state.value}")
        else:
            self.logger.error(f"Invalid state transition from {self.state.value} to {new_state.value}")

if __name__ == "__main__":
    mono = MonochromatorState("ANY", "DIO0")
    mono.get_device_info()
    mono.activate()
    mono.deactivate()
    mono.get_state()
    mono.close()