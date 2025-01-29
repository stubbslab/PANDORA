import logging
from states_map import State
import pyvisa

class KeysightState():
    """KeysightState class to handle communication with Keysight devices.

    Args:
        name (str): Name of the Keysight device.
        keysight_ip (str): IP address of the Keysight device.
        timeout_ms (int): Timeout in milliseconds for the connection.
    
    Example:
        keysight = KeysightState(name="K01", keysight_ip="169.254.56.239")
        keysight.get_device_info()
        keysight.activate()
        keysight.deactivate()
        keysight.get_state()
        keysight.close()

    """
    def __init__(self, name, keysight_ip="169.254.56.239", timeout_ms=5000):
        ## Initialize the Keysight State Parameters
        self.codename = name
        self.keysight_ip = keysight_ip
        self.resource_string = f"TCPIP::{keysight_ip}::hislip0,4880::INSTR"
        self.timeout_ms = timeout_ms
        self.logger = logging.getLogger(f"pandora.keysight.state.{name}")

        ## Initialize the Keysight State
        self.state = State.UNINITIALIZED
        self.initialize()

    def initialize(self):
        self.logger.info(f"Initializing Keysight State.")
        self.rm = pyvisa.ResourceManager('@py')  # Use '@py' for PyVISA-py backend
        self.instrument = None
        self._connect()
        self.set_state(State.IDLE)
        self.print_keysight_id()

    def activate(self):
        if self.state == State.IDLE or self.state == State.OFF:
            self.logger.info(f"Activating Keysight {self.codename}.")
            self.write(':INP ON')
            self.set_state(State.ON)
        
        elif self.state == State.ON:
            self.logger.info(f"Keysight is already activated {self.codename}.")
        
        elif self.state == State.FAULT:
            self.logger.error(f"Error activating Keysight {self.codename}.")
        
    def deactivate(self):
        if self.state == State.IDLE or self.state == State.ON:
            self.logger.info(f"Deactivating Keysight {self.codename}.")
            self.write(':INP OFF')
            self.set_state(State.OFF)
        
        elif self.state == State.OFF:
            self.logger.info(f"Keysight is already deactivated {self.codename}.")
        
        elif self.state == State.FAULT:
            self.logger.error(f"Error deactivating Keysight {self.codename}.")
    

    def set_error(self):
        self.logger.error(f"Setting state to fault for Keysight {self.codename}.")
        self.set_state(State.FAULT)

    def reset(self):
        if self.state == State.FAULT:
            self.logger.info(f"Resetting Keysight {self.codename} from fault state.")
            self.set_state(State.IDLE)
    
    def close(self):
        if self.instrument is not None:
            self.set_state(State.IDLE)
            self.instrument.close()
            print("Keysight connection closed.")
            self.set_state(State.UNINITIALIZED)
        else:
            print("No connection to close.")

    def _connect(self):
        """Establish a connection to the instrument."""
        try:
            self.instrument = self.rm.open_resource(self.resource_string, timeout=self.timeout_ms)
            print(f"Connected to Keysight device at {self.keysight_ip}")
        except Exception as e:
            print(f"Error connecting to {self.resource_string}: {e}")
            self.instrument = None

    def _reconnect(self):
        """Re-establish the connection."""
        print("Reconnecting...")
        self._connect()

    def write(self, message):
        """
        Write a command to the instrument.

        :param message: SCPI command to send.
        """
        if self.instrument is None:
            self._reconnect()
        try:
            self.instrument.write(message)
        except pyvisa.errors.VisaIOError as e:
            print(f"Write error: {e}. Reconnecting...")
            self._reconnect()
            self.instrument.write(message)

    def read(self, message):
        """
        Send a command and read the response.

        :param message: SCPI command to send.
        :return: Response from the instrument.
        """
        if not self.instrument:
            self._reconnect()
        try:
            return self.instrument.query(message).strip()
        except pyvisa.errors.VisaIOError as e:
            print(f"Read error: {e}. Reconnecting...")
            self._reconnect()
            return self.instrument.query(message).strip()

    def get_power(self):
        return int(self.read(':INP?').decode()[0])
    
    def get_device_info(self):
        # Send *IDN? command to query the instrument's identity
        response = self.instrument.query("*IDN?").strip()
        print(f"Device Response: {response}")
        
        # Parse response
        if response:
            details = response.split(',')
            model = details[1] if len(details) > 1 else "Unknown Model"
            serial_number = details[2] if len(details) > 2 else "Unknown Serial Number"
            print(f"Model: {model}")
            print(f"Serial Number: {serial_number}")
        else:
            print("No response received from the device.")

    def get_state(self):
        try:
            self.logger.info(f"Querying Keysight {self.codename} state.")
            value = self.get_power()
            self.set_state(State.IDLE if value == '1' else State.OFF)
            return self.state
        except:
            self.logger.error(f"Error querying Keysight {self.codename} state.")
            self.set_state(State.FAULT)
            return self.state
        
    def set_state(self, new_state):
        valid_transitions = {
            State.UNINITIALIZED: [State.IDLE],
            State.IDLE: [State.ON, State.OFF, State.FAULT, State.UNINITIALIZED],
            State.ON: [State.OFF, State.FAULT],
            State.OFF: [State.ON, State.FAULT],
            State.FAULT: [State.IDLE],
            State.MEASURING: [State.IDLE, State.ON]
        }

        if new_state in valid_transitions[self  .state]:
            self.state = new_state
            self.logger.info(f"State changed to {self.state.value}")
        else:
            self.logger.error(f"Invalid state transition from {self.state.value} to {new_state.value}")

if __name__ == "__main__":
    keysight = KeysightState(name="K01", keysight_ip="169.254.56.239")
    keysight.get_device_info()
    keysight.activate()
    keysight.deactivate()
    keysight.get_state()
    keysight.close()