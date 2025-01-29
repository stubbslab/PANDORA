# states/flipmount_state.py
import logging
from states_map import State
from utils.operation_timer import OperationTimer

class FlipMountState:
    """ FlipMountState class to handle communication with Thorlabs FlipMount devices.

    Args:
        name (str): Name of the labjack port, e.g. "F01"
        labjack (LabJack): LabJack object to handle communication with the device.

    Example:
        labjack = LabJack()
        fm = FlipMountState(name="F01", labjack=labjack)
        fm.get_device_info()

        # flips the state of the flip mount

        # activate puts the flip mount in the ON state (on the optical path)
        fm.activate()

        # deactivate puts the flip mount in the OFF state (off the optical path)
        fm.deactivate()

        # Get the curent state of the flip mount
        fm.get_state()

        # Close the labjack connection
        fm.close()
    """
    def __init__(self, name, labjack):
        self.labjack = labjack
        self.codename = name  
        self.state = State.UNINITIALIZED
        self.logger = logging.getLogger(f"pandora.flipmount.{name}")
        ## Safety measure for SHB1 shutter
        self.max_operation_freq = 2 # Hz
        self.timer = OperationTimer(min_interval=1/self.max_operation_freq, name=f"FlipMount-{name}")

        self.initialize()

    def initialize(self):
        self.logger.info(f"Initializing FlipMount {self.codename}.")
        self.set_state(State.IDLE)
        self.get_state()
        self.timer.update_last_operation_time()

    def activate(self):
        self.logger.info(f"Activating FlipMount {self.codename}.")
        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast {self.codename}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.debug(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")

        if self.state == State.OFF:
            self.labjack.send_low_signal(self.codename)
            self.set_state(State.ON)
            self.timer.update_last_operation_time()
        
        elif self.state == State.ON:
            self.logger.info(f"Flip Mount is already activated {self.codename}.")
    
        elif self.state == State.FAULT:
            self.logger.error(f"Error activating Flip Mount {self.codename}.")
        
        elif self.state == State.IDLE:
            self.get_state()
            self.activate()

    def deactivate(self):
        self.logger.info(f"Deactivating FlipMount {self.codename}.")
        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast {self.codename}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.warning(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")

        if self.state == State.ON:
            self.labjack.send_high_signal(self.codename)
            self.set_state(State.OFF)
            self.timer.update_last_operation_time()
        
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
            self.logger.debug(f"Resetting Flip Mount from fault state {self.codename}.")
            self.set_state(State.IDLE)
            
    def get_state(self):
        if self.state != State.UNINITIALIZED:
            try:
                self.logger.debug(f"Querying Flip Mount state {self.codename}.")
                value = int(self.labjack.read(self.codename))
                self.set_state(State.ON if value == 0 else State.OFF)
            except:
                self.logger.error(f"Error querying Flip Mount {self.codename} state.")
                self.set_state(State.FAULT)
        
        self.logger.info(f"FlipMount state is {self.state.value}")
        return self.state

    def get_device_info(self):
        self.labjack.get_device_info()
        print(f"Flip Mount name: {self.codename}")
        print(f"Flip Mount {self.codename} state: {self.state.value}")

    def close(self):
        self.logger.info(f"Closing Flip Mount {self.codename}.")
        self.deactivate()
        # self.set_state(State.IDLE)
        self.set_state(State.UNINITIALIZED)
        self.get_state()

    def set_state(self, new_state):
        valid_transitions = {
            State.UNINITIALIZED: [State.IDLE],
            State.IDLE: [State.ON, State.OFF, State.FAULT, State.UNINITIALIZED, State.IDLE],
            State.ON: [State.OFF, State.FAULT, State.ON, State.UNINITIALIZED],
            State.OFF: [State.ON, State.FAULT, State.OFF, State.UNINITIALIZED],
            State.FAULT: [State.IDLE]
        }

        if new_state in valid_transitions[self.state]:
            self.state = new_state
            self.logger.debug(f"State set to {self.state.value}")
        else:
            self.logger.error(f"Invalid state transition from {self.state.value} to {new_state.value}")

if __name__ == "__main__":
    from PANDORA.pandora.states.labjack_handler import LabJack
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
    fm1 = FlipMountState(name="FIO01", labjack=labjack)
    fm2 = FlipMountState(name="FIO02", labjack=labjack)
    fm3 = FlipMountState(name="FIO03", labjack=labjack)

    for f in [fm1, fm2, fm3]:
        f.activate()

    print("Sleep for 2 sec") 
    time.sleep(2)

    for f in [fm1, fm2, fm3]:
        f.deactivate()

    # Close the FIO1 output connection
    # fm.close()
    labjack.close()