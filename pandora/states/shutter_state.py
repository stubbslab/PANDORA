# states/shutter_state.py
import logging
from pandora.utils.operation_timer import OperationTimer

stateDict = {
    0: "closed",
    1: "opened"
}

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
        self.state = None
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
        self.get_state()
        self.timer.update_last_operation_time()

    def activate(self):
        self.logger.info(f"Activating Shutter {self.codename}.")

        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast for Shutter {self.codename}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.warning(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")

        self.labjack.send_low_signal(self.codename)
        self.timer.update_last_operation_time()
        
        self.get_state()

    def deactivate(self):
        self.logger.info(f"Deactivating Shutter {self.codename}.")

        if not self.timer.can_operate():
            self.logger.warning(f"Operation too fast for Shutter {self.codename}.")
            self.timer.sleep_through_remaining_interval()
            self.logger.debug(f"System sleeped for {self.timer.remaining_time:0.2f} seconds.")

        self.labjack.send_high_signal(self.codename)
        self.timer.update_last_operation_time()
        self.get_state()
        
    def get_state(self):
        self.logger.debug(f"Querying Shutter state {self.codename}.")
        try:
            value = int(self.labjack.read("FIO_STATE")) & 1
            self.state = stateDict[value]
            self.logger.info(f"The shutter state is {self.state}")

        except Exception as e:
            self.logger.error(f"Error querying Shutter {self.codename} state: {e}")
            self.logger.error(f"The shutter state is {self.state}")

        # self.logger.info(f"The shutter state is {self.state}")
        return self.state

    def get_device_info(self):
        self.labjack.get_device_info()
        print(f"Shutter name: {self.codename}")
        print(f"Shutter {self.codename} state: {self.state}")

    def close(self):
        self.logger.info(f"Closing Shutter {self.codename}.")
        self.activate()
        self.get_state()

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
