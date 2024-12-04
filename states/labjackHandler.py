# ./labjackHandler.py

from labjack import ljm
import utils.logger as logger
import time

class LabJack:
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.handle = None
        self.logger = logger.get_logger("LabJack")
        self.initialize()

    def initialize(self):
        try:
            # Open a connection to the LabJack device at the given IP address
            self.handle = ljm.openS("ANY", "TCP", self.ip_address)
            self.logger.info(f"Connected to LabJack at {self.ip_address}")
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

    def send_binary_signal(self, register_name, wait_time_ms=50):
        self.logger.info("Sending square signal to labjack entry.")
        try:
            # Send binary signal to the system
            self.logger.info("Sending binary signal (High/Low) signal to the system...")
            self.write(register_name, 1)  # High signal
            time.sleep(wait_time_ms / 1000)  # Wait for specified milliseconds
            self.write(register_name, 0)  # Low signal

            self.logger.info("Signal sent.")

        except Exception as e:
            self.logger.error(f"Error activating Flip Mount: {e}")
            self.set_error()