import time
import logging
from labjack import ljm

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
    def __init__(self, ip_address=None, usb_address=None, verbose=False):
        if ip_address is None and usb_address is None:
            raise ValueError("Either IP address or USB address must be provided.")
        
        if ip_address is not None:
            self.address = ip_address
            self.tag = "TCP"
        elif usb_address is not None:
            self.address = usb_address
            self.tag = "USB"
        
        self.handle = None
        self.logger = logging.getLogger("LabJack")
        self.verbose = verbose
        self.wait_time_ms = 1000

        self.state = None
        self.initialize()

    def initialize(self):
        try:
            # Open a connection to the LabJack device at the given IP address
            self.handle = ljm.openS("ANY", self.tag, self.address)
            self.state = "on"
            self.logger.info(f"Connected to LabJack at {self.address}")
        except Exception as e:
            self.state = "off"
            self.logger.error(f"Failed to connect to LabJack: {e}")
            raise

    def write(self, port_name, value):
        try:
            ljm.eWriteName(self.handle, port_name, value)
            self.logger.info(f"Wrote value {value} to register {port_name}")
        except Exception as e:
            self.logger.error(f"Failed to write to LabJack: {e}")
            raise

    def read(self, port_name):
        try:
            value = ljm.eReadName(self.handle, port_name)
            self.logger.info(f"Read value {value} from register {port_name}")
            return value
        except Exception as e:
            self.state = "off"
            self.reset()
            if self.state=="on":
                self.read(port_name)
            else:
                self.logger.error(f"Failed to read from LabJack: {e}")

            raise

    def close(self):
        if self.handle:
            ljm.close(self.handle)
            self.logger.info("LabJack connection closed.")

    def send_high_signal(self, port_name):
        # self.logger.info("Sending high signal to labjack entry.")
        try:
            # Send high signal to the system
            self.logger.info("Sending high signal to the system...")
            self.write(port_name, 1)
            self.logger.info(f"Signal high sent to {port_name}.")
        # try one reset if it fails
        except Exception as e:
            self.logger.error(f"Error send_high_signal Monochromator: {e}")
            self.state = "off"
            self.reset()
            if self.state == "on":
                self.send_high_signal(port_name)


    def send_low_signal(self, port_name):
        # self.logger.info("Sending low signal to labjack entry.")
        try:
            # Send low signal to the system
            self.logger.info("Sending low signal to the system...")
            self.write(port_name, 0)
            self.logger.info(f"Signal low sent to {port_name}.")
        except Exception as e:
            self.logger.error(f"Error send_low_signal Monochromator: {e}")
            self.state = "off"
            self.reset()
            if self.state == "on":
                self.send_low_signal(port_name)

    def send_binary_signal(self, port_name, wait_time_ms=50):
        self.logger.info("Sending square signal to labjack entry.")
        self.send_high_signal(port_name)
        time.sleep(wait_time_ms / 1000)
        self.send_low_signal(self.fport_name)

    def get_device_info(self):
        try:
            # Get device information
            info = ljm.getHandleInfo(self.handle)
            self.logger.info(f"Device info: {info}")
            if self.verbose:
                print(f"Device info: {info}")
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
            if self.verbose:
                print(f"Failed to get device info: {e}")
            raise
    
    def set_error(self):
        # Set error state
        self.logger.error("Error occurred.")
        pass

    def reset(self):
        time.sleep(self.wait_time_ms / 1000)
        try:
            # Reset the device
            self.logger.info("Resetting the device...")
            self.initialize()
            self.logger.info("Device reset.")
        except Exception as e:
            self.state = "off"
            self.logger.error(f"Failed to reset device: {e}")
            raise
        
if __name__ == "__main__":
    # Usage example
    ip_address = str(input("Enter the IP address of the LabJack device: "))
    labjack = LabJack(ip_address=ip_address)
    labjack.get_device_info()

    # Send Binary Signals
    labjack.send_high_signal()
    labjack.send_low_signal()
    # labjack.send_binary_signal(wait_time_ms=5000)
    
    # Close the connection
    labjack.close()