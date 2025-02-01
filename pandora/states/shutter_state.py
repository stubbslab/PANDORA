# states/shutter_state.py
import logging
from states.states_map import State                # '.' means same directory as shutter_state.py
from utils.operation_timer import OperationTimer

class ShutterState:
    """ ShutterState class to handle state and communication with Thorlabs Shutter devices.
    https://www.thorlabs.com/thorproduct.cfm?partnumber=SHB1T#ad-image-0

    Args:
        name (str): Name of the labjack port, e.g., "F03"
        labjack (LabJack): LabJack object to handle communication with the device.

    Example:
        labjack = LabJack()
        shutter = ShutterState(name="F03", labjack=labjack)
        shutter.get_device_info()

        # Activate the shutter
        shutter.activate()

        # Deactivate the shutter
        shutter.deactivate()

        # Get the current state of the shutter
        shutter.get_state()

        # Close the labjack connection
        shutter.close()
    """
    def __init__(self, name, labjack):
        if name is None:
            raise ValueError("Shutter name cannot be None.")
        if labjack is None:
            raise ValueError("LabJack cannot be None.")

        # Initialize the ShutterState object
        self.labjack = labjack
        self.codename = name
        self.state = State.UNINITIALIZED
        self.logger = logging.getLogger(f"pandora.shutter.{name}")

        ## Safety measure for SHB1 shutter
        self.max_operation_freq = 10 # Hz
        self.timer = OperationTimer(min_interval=1/self.max_operation_freq, name=f"Shutter-{name}")

        self.initialize()

    def initialize(self):
        """ Initialize the ShutterState object.
        
        Steps:
        1. Set the initial state to IDLE.
        2. Get the current state of the shutter.
        3. Close the shutter.
        """
        self.logger.info(f"Initializing ShutterState {self.codename}.")
        self.set_state(State.IDLE)
        self.get_state()
        self.activate()
        self.timer.update_last_operation_time()

    def activate(self):
        self.logger.info(f"Activating Shutter {self.codename}.")

        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast for Shutter {self.codename}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.warning(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")

        if self.state == State.OFF:
            self.labjack.send_low_signal(self.codename)
            self.set_state(State.ON)
            self.timer.update_last_operation_time()
        
        elif self.state == State.ON:
            self.logger.debug(f"Shutter {self.codename} is already activated.")
        
        elif self.state == State.FAULT:
            self.logger.error(f"Error activating Shutter {self.codename}.")
        
        elif self.state == State.IDLE:
            self.get_state()
            self.activate()

    def deactivate(self):
        self.logger.info(f"Deactivating Shutter {self.codename}.")

        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast for Shutter {self.codename}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.debug(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")

        if self.state == State.ON:
            self.labjack.send_high_signal(self.codename)
            self.set_state(State.OFF)
            self.timer.update_last_operation_time()
        
        elif self.state == State.OFF:
            self.logger.debug(f"Shutter {self.codename} is already deactivated.")
        
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
        self.logger.debug(f"Querying Shutter state {self.codename}.")

        if self.state != State.UNINITIALIZED:
            try:
                value = int(self.labjack.read("FIO_STATE")) & 1
                self.set_state(State.ON if value == 0 else State.OFF)
                # self.logger.info(f"The shutter state is {self.state.value}")

            except Exception as e:
                self.logger.error(f"Error querying Shutter {self.codename} state: {e}")
                self.set_state(State.FAULT)
                self.logger.error(f"The shutter state is {self.state.value}")

        self.logger.info(f"The shutter state is {self.state.value}")
        return self.state

    def get_device_info(self):
        self.labjack.get_device_info()
        print(f"Shutter name: {self.codename}")
        print(f"Shutter {self.codename} state: {self.state.value}")

    def close(self):
        self.logger.info(f"Closing Shutter {self.codename}.")
        self.activate()
        self.set_state(State.UNINITIALIZED)
        self.get_state()

    def set_state(self, new_state):
        valid_transitions = {
            State.UNINITIALIZED: [State.IDLE],
            State.IDLE: [State.ON, State.OFF, State.FAULT, State.UNINITIALIZED, State.IDLE],
            State.ON: [State.OFF, State.FAULT, State.ON, State.IDLE, State.UNINITIALIZED],
            State.OFF: [State.ON, State.FAULT, State.OFF],
            State.FAULT: [State.IDLE]
        }

        if new_state in valid_transitions[self.state]:
            self.state = new_state
            self.logger.debug(f"State changed to {self.state.value}")
        else:
            self.logger.error(f"Invalid state transition from {self.state.value} to {new_state.value}")

if __name__ == "__main__":
    from labjack_handler import LabJack
    # import logging
    # from config import labjack_ip_address
    from utils.logger import initialize_central_logger  

    # Initialize the logger
    initialize_central_logger("../shutter.log", "INFO")

    ip_address = "169.254.84.89"
    labjack = LabJack(ip_address)

    # Initialize the shutter
    shutter = ShutterState(name="FIO0", labjack=labjack)
    # shutter.get_device_info()

    # Deactivate the shutter
    shutter.deactivate()

    # Activate the shutter
    # shutter.activate()

    # Get the curent state of the shutter
    shutter.get_state()

    # Close the labjack connection
    # shutter.close()
