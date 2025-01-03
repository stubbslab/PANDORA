# ./labjackHandler.py

# from labjack import ljm
# import ..utils.logger import 
import time

class LabJack:
    """
    LabJack class to handle communication with LabJack devices.

    Args:
        ip_address (str): IP address of the LabJack device.
        usb_address (str): USB address of the LabJack device.

    Example:
        labjack = LabJack(ip_address="169.254.5.2")
        labjack.get_device_info()
        labjack.send_high_signal()
        labjack.send_low_signal()
        labjack.send_binary_signal(wait_time_ms=5000)
        labjack.close()
    """
    def __init__(self, ip_address=None, usb_address=None):
        if ip_address is None and usb_address is None:
            raise ValueError("Either IP address or USB address must be provided.")
        
        if ip_address is not None:
            self.address = ip_address
            self.tag = "TCP"
        elif usb_address is not None:
            self.address = usb_address
            self.tag = "USB"
        
        self.handle = None
        self.logger = logger.get_logger("LabJack")
        self.initialize()

    def initialize(self):
        try:
            # Open a connection to the LabJack device at the given IP address
            self.handle = ljm.openS("ANY", self.tag, self.address)
            self.logger.info(f"Connected to LabJack at {self.address}")
        except Exception as e:
            self.logger.error(f"Failed to connect to LabJack: {e}")
            raise

    def write(self, register_name, value):
        try:
            ljm.eWriteName(self.handle, register_name, value)
            self.logger.info(f"Wrote value {value} to register {register_name}")
        except Exception as e:
            self.logger.error(f"Failed to write to LabJack: {e}")
            raise

    def read(self, register_name):
        try:
            value = ljm.eReadName(self.handle, register_name)
            self.logger.info(f"Read value {value} from register {register_name}")
            return value
        except Exception as e:
            self.logger.error(f"Failed to read from LabJack: {e}")
            raise

    def close(self):
        if self.handle:
            ljm.close(self.handle)
            self.logger.info("LabJack connection closed.")

    def send_high_signal(self, register_name="FIO0"):
        # self.logger.info("Sending high signal to labjack entry.")
        try:
            # Send high signal to the system
            self.logger.info("Sending high signal to the system...")
            self.write(register_name, 1)
            self.logger.info(f"Signal high sent to {register_name}.")
        except Exception as e:
            self.logger.error(f"Error send_high_signal Monochromator: {e}")
            self.set_error()

    def send_low_signal(self, register_name="FIO0"):
        # self.logger.info("Sending low signal to labjack entry.")
        try:
            # Send low signal to the system
            self.logger.info("Sending low signal to the system...")
            self.write(register_name, 0)
            self.logger.info(f"Signal low sent to {register_name}.")
        except Exception as e:
            self.logger.error(f"Error send_low_signal Monochromator: {e}")
            self.set_error()

    def send_binary_signal(self, register_name, wait_time_ms=50):
        self.logger.info("Sending square signal to labjack entry.")
        self.send_high_signal(register_name)
        time.sleep(wait_time_ms / 1000)
        self.send_low_signal(register_name)

    def get_device_info(self):
        try:
            # Get device information
            info = ljm.getHandleInfo(self.handle)
            self.logger.info(f"Device info: {info}")
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
            raise

if __name__ == "__main__":
    # Usage example
    ip_address = str(input("Enter the IP address of the LabJack device: "))
    labjack = LabJack(ip_address=ip_address)
    labjack.get_device_info()

    # Send Binary Signals
    labjack.send_high_signal()
    labjack.send_low_signal()
    labjack.send_binary_signal(wait_time_ms=5000)
    
    # Close the connection
    labjack.close()