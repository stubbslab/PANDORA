import serial # pip install pyserial
import logging
import time

"""
This scripts provides a class to control a monochromator via serial communication.

The monochromator should be powered on and connected to the computer via a serial port.

"""

class MonochromatorController:
    """
    Controls Digikröm - CM110/CM112 Monochromator
    via serial communication.

    Attributes:
    - port (str): The serial port to connect to (e.g., 'COM3' or '/dev/ttyUSB0').
    - baudrate (int): The baud rate for the serial connection.
    - logger (logging.Logger): The logger object for logging messages.    
    """
    def __init__(self, usb_port, baudrate=9600, type=None):
        """
        Initialize the MonochromatorController object.

        Parameters:
        - usb_port (str): The serial port to connect to (e.g., 'COM3' or '/dev/ttyUSB0').
        """
        self.port = usb_port
        self.baudrate = baudrate

        # Set up logging
        self.ser = None
        self.logger = logging.getLogger(f"pandora.monochromator")
        self.wavelength = None
        self.timeout = 1 # seconds

    def initialize(self):
        """
        Initialize the monochromator by connecting to the serial port.

        Steps:
        1. Connect to the monochromator.
        2. Move to the home position.
        3. Get the current wavelength.
        """
        self.logger.info(f"Initialize Zaber device at {self.ip_address}.")
        self.go_home()
        self.logger.info(f"Current wavelength is: {self.wavelength} nm.")

    def connect(self, timeout=1):
        """
        Establish the serial connection to the monochromator.
        """
        if not self._is_connected():
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=8,
                    parity='N',
                    stopbits=1,
                    timeout=timeout
                )
                self.logger.info(f"Connected to monochromator on port {self.port}.")
            except serial.SerialException as e:
                self.logger.error(f"Error: Could not connect to port {self.port}. {e}")
                self.ser = None
        else:
            self.logger.warning("Warning: Serial connection already established.")

    def close(self):
        """
        Close the serial connection to the monochromator.
        """
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.info("Serial connection closed.")
        self.ser = None

    def go_home(self, timeout=2, max_attempts=3):
        """
        Move the monochromator to the home position.
        """
        if self.wavelength is None:
            self.get_wavelength()

        if self.wavelength==0:
            self.logger.info("Monochromotor is at home position.")
            return
        
        ## check if the operation is completed
        self.connect(timeout)

        if not self._is_connected():
            self.logger.error("Error: Could not establish connection to monochromator.")
            return

        # Send the RESET command
        command = bytes([255, 255, 255])
        self._write(command)
        self.logger.info("Go Home, sent RESET command, awaiting response...")
        
        # Read status byte response, looping if necessary
        status_byte = self._read(1)
        if status_byte:
            self.logger.bug(f"Received status byte: {status_byte.hex()}")  # Print the received byte
            status = ord(status_byte)
            if status < 128:
                # Keep reading until we get the final <24> D byte indicating completion
                attempts = 0
                while attempts < max_attempts:
                    # Wait for response
                    is_finished = self.query_confirmation_bytes()
                    
                    if is_finished:
                        self.logger.info(f"Monochromator successfully returned to home position.")
                        break
                    else:
                        attempts += 1
                        time.sleep(self.timeout)  # Add a small delay before trying again
                        self.logger.warning(f"Attempt {attempts}: Waiting for final confirmation byte...")

                # If we reach here, the expected <24> D was not received
                if attempts == max_attempts:
                    self.logger.info(f"Monochromator successfully returned to home position.")
            else:
                self.handle_status_byte(status)
        else:
            self.logger.info(f"Monochromator successfully returned to home position.")

        # Close the connection
        self.close()

        # Make a delay to avoid error
        self.get_wavelength(sleep=self.timeout)

    def get_wavelength(self, sleep=1):
        """
        Get the current wavelength setting of the monochromator.

        Returns:
        - float: The current wavelength in nanometers, or None if an error occurred.
        """
        time.sleep(sleep)
        self.connect(timeout=2)
        # Command for QUERY POSITION: <56> D <00>
        command = bytes([56, 0])
        self._write(command)
        self.logger.debug("Sent QUERY command to check current wavelength...")

        response = self._read(2)
        if len(response) == 2:
            high_byte, low_byte = response[0], response[1]
            current_wavelength_angstroms = (high_byte << 8) | low_byte
            current_wavelength_nm = current_wavelength_angstroms / 10
            self.logger.info(f"Current wavelength is: {current_wavelength_nm} nm.")

            # Wait for response
            is_finished = self.query_confirmation_bytes()
            if not is_finished:
                self.logger.warning("Warning: Did not receive final confirmation byte after querying wavelength.")

            self.wavelength = current_wavelength_nm
        else:
            self.logger.error("Incomplete response from monochromator during get_wavelength.")
            current_wavelength_nm = None

        self.wavelength = current_wavelength_nm
        self.close()

    def move_to_wavelength(self, wavelength_nm, timeout=2):
        """
        Move the monochromator to a specified wavelength.

        Parameters:
        - wavelength_nm (float): The target wavelength in nanometers.
        """
        self.connect(timeout)
        
        if not self._is_connected():
            self.logger.error("Error: Could not establish connection to monochromator.")
            return

        # Convert wavelength to Angstroms and split into high and low bytes
        wavelength_angstroms = int(wavelength_nm * 10)
        # Convert wavelength to High Byte and Low Byte
        high_byte = wavelength_angstroms // 256
        low_byte = wavelength_angstroms % 256

        # Command for GOTO: <16> D <High Byte> <Low Byte>
        command = bytes([16, high_byte, low_byte])
        self._write(command)
        self.logger.info(f"Sent GOTO command to move to {wavelength_nm} nm.")

        # Read status byte response
        status_byte = self._read(1)
        if status_byte:
            status = status_byte[0]
            if status < 128:
                # Wait for response
                is_finished = self.query_confirmation_bytes()

                if is_finished:
                    self.logger.info(f"Monochromator successfully moved to {wavelength_nm} nm.")

            else:
                self._handle_status_byte(status)
        else:
            self.logger.error("Error: No response from monochromator during move_to_wavelength.")

        # close the connection
        self.close()

    def scan_wavelength(self, start_nm, end_nm, timeout=2):
        """
        Scan the monochromator from a start wavelength to an end wavelength.

        Parameters:
        - start_nm (float): The start wavelength in nanometers.
        - end_nm (float): The end wavelength in nanometers.
        """
        self.connect(timeout)

        if not self._is_connected():
            self.logger.error("Error: Could not establish connection to monochromator.")
            return

        # Convert start and end wavelengths to Angstroms
        start_angstroms = int(start_nm * 10)
        end_angstroms = int(end_nm * 10)

        # Convert start and end wavelengths to High Byte and Low Byte
        start_high_byte = start_angstroms // 256
        start_low_byte = start_angstroms % 256
        end_high_byte = end_angstroms // 256
        end_low_byte = end_angstroms % 256

        # Construct the command bytes: <12> D <Start High Byte> <Start Low Byte> <End High Byte> <End Low Byte>
        command = bytes([12, start_high_byte, start_low_byte, end_high_byte, end_low_byte])
        self._write(command)
        self.logger.info(f"Sent SCAN command to scan from {start_nm} nm to {end_nm} nm.")

        # Read status byte response

        status_byte = self._read(1)
        if status_byte:
            status = status_byte[0]
            if status < 128:
                # Wait for response
                is_finished = self.query_confirmation_bytes()
                if is_finished:
                        self.logger.info(f"Monochromator successfully scanned from {start_nm} nm to {end_nm} nm.")
            else:
                self._handle_status_byte(status)
        else:
            self.logger.error("Error: Scanning Not Completed - No response from monochromator during scan.")

        # close the connection
        self.close()

    def set_units(self, unit="angstroms"):
        """
        Set the monochromator's wavelength units.
        
        Parameters:
        - unit (str): The desired wavelength unit. Valid options: 'microns', 'nm', 'angstroms'.
        
        Command format:
        - To CM110/112: <50> D <Units Byte>
        - Response: <Status byte> (should return <24> D if successful)
        """
        self.connect()

        # Define the unit byte based on user selection
        unit_mapping = {
            "microns": 0x00,   # 00 Microns
            "nm": 0x01,        # 01 Nanometers
            "angstroms": 0x02  # 02 Angstroms
        }

        if unit not in unit_mapping:
            self.logger.error(f"Invalid unit '{unit}'. Choose from: {list(unit_mapping.keys())}")
            return False

        # Construct command: <50> D <Units Byte>
        command = bytes([50, unit_mapping[unit]])
        self._write(command)
        self.logger.info(f"Sent SET UNITS command to switch to {unit}.")

        # Wait for response
        is_finished = self.query_confirmation_bytes()
        if is_finished:
            self.logger.info(f"Monochromator successfully switched to {unit}.")
        pass
    
    def get_grating_gmm(self):
        """
        Query the current grating groove density (g/mm).
        
        Returns:
        - int: The groove density in gr/mm if successful.
        - None: If no valid response is received.
        """
        self.connect()
        if not self.ser:
            self.logger.error("Error: Could not establish connection to monochromator.")
            return None

        # Construct command: <56> D <02> D  (QUERY GROOVES/MM)
        command = bytes([56, 2])
        self.ser.write(command)
        self.logger.info("Sent QUERY command to get current grating groove density (g/mm).")

        # Wait for response (2 bytes expected: High Byte + Low Byte)
        response = self.ser.read(2)
        if len(response) == 2:
            high_byte, low_byte = response[0], response[1]
            grating_gmm = (high_byte * 256) + low_byte  # Convert to integer
            self.logger.info(f"Current grating has {grating_gmm} grooves/mm.")
            return grating_gmm
        else:
            self.logger.warning("No valid response received for grating query.")
            return None

    def change_order(self, order):
        """
        Change the diffraction order direction.

        Parameters:
        - order (str): "clockwise" (positive orders, m > 0) 
                        or "counterclockwise" (negative orders, m < 0).
        """
        self.connect()
        if not self.ser:
            self.logger.error("Error: Could not establish connection to monochromator.")
            return False

        # Define order bytes
        order_bytes = {
            "clockwise": 0x01,        # Rotates the grating clockwise (selects positive orders, m > 0)
            "counterclockwise": 0xFE  # Rotates the grating counterclockwise (selects negative orders, m < 0)
        }

        if order not in order_bytes:
            self.logger.error("Invalid order. Choose 'clockwise' or 'counterclockwise'.")
            return False

        # Construct command: <51> D <Order Byte>
        command = bytes([51, order_bytes[order]])
        self.ser.write(command)
        self.logger.info(f"Sent ORDER command to rotate {order} (Selecting {'positive' if order == 'clockwise' else 'negative'} orders).")

        # Wait for response
        is_finished = self.query_confirmation_bytes()
        if is_finished:
            self.logger.info(f"Monochromator successfully rotated {order}.")
        pass


    def query_confirmation_bytes(self, expected_byte=24, intermediate_byte=34, num_attempts=10):
        """
        Waits for a confirmation byte from the monochromator.

        Parameters:
        - expected_byte (int): The expected response byte (default: 24, indicating success).
        - intermediate_byte (int): A byte indicating an "in-progress" status (default: 34, hex 0x22).

        Returns:
        - True if the expected byte is received.
        - False if an unknown byte is received or if timeout occurs.
        """
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            response = self._read(1)  # Try to read one byte
            if response:
                status_byte = response[0]
                self.logger.debug(f"DEBUG: Raw response byte: {response} (decimal: {status_byte}, hex: {response.hex()})")

                if status_byte == expected_byte:
                    self.logger.debug("Successfully received confirmation byte.")
                    return True
                elif status_byte == intermediate_byte:  # Handle in-progress signal (0x22)
                    self.logger.debug("Received intermediate response. Waiting for final confirmation...")
                    continue  # Keep waiting for the final confirmation byte
                else:
                    self.logger.error(f"Unexpected response: {response} (decimal: {status_byte})")
                    return False

            time.sleep(self.timeout / num_attempts)  # Wait briefly before retrying

        self.logger.warning("Timeout: No confirmation received from the monochromator.")
        return False

    # Internal helper methods
    def _write(self, command_bytes):
        """
        Write bytes to the monochromator via serial connection.

        Parameters:
        - command_bytes (bytes): The bytes to send to the device.
        """
        try:
            self.logger.debug(f"Writing command: {command_bytes}")
            self.ser.write(command_bytes)
        except serial.SerialException as e:
            self.logger.error(f"Error: Failed to write to serial port. {e}")

    def _read(self, num_bytes):
        """
        Read bytes from the monochromator via serial connection.

        Parameters:
        - num_bytes (int): Number of bytes to read.

        Returns:
        - bytes: The bytes read from the device, or empty bytes if an error occurred.
        """
        try:
            return self.ser.read(num_bytes)
        except serial.SerialException as e:
            self.logger.error(f"Error: Failed to read from serial port. {e}")
            return b''

    def _is_connected(self):
        """
        Check if the serial connection is established.

        Returns:
        - bool: True if connected, False otherwise.
        """
        if self.ser and self.ser.is_open:
            return True
        else:
            return False

    def _handle_status_byte(self, status_byte):
        """
        Interpret the status byte and provide detailed error messages.

        Parameters:
        - status_byte (int): The status byte received from the device.
        """
        error_messages = []

        if status_byte >= 128:
            error_messages.append("Command not accepted.")
        if status_byte & 0b00100000:
            error_messages.append("Specifier too small.")
        if status_byte & 0b00010000:
            error_messages.append("Negative-going scan.")
        if status_byte & 0b00001000:
            error_messages.append("Wavelength out of range.")
        if status_byte & 0b00000010:
            units = "nanometers"
        elif status_byte & 0b00000100:
            units = "angstroms"
        else:
            units = "microns"
        error_messages.append(f"Units are {units}.")

        self.logger.error("Error: " + ' '.join(error_messages))

if __name__ == "__main__":
    import time
    from pandora.utils.logger import initialize_central_logger 
    # Set up logging
    initialize_central_logger("../monochromator.log", "DEBUG")

    # Serial port name
    SERIAL_PORT = "/dev/tty.usbserial-FTDI1CB2"

    # Create an instance of the MonochromatorController
    mono = MonochromatorController(SERIAL_PORT)

    # Get the current wavelength
    mono.get_wavelength(sleep=0.0)

    # Set the monochromator to a new wavelength
    new_wavelength = 650.0  # Move to 550 nm
    mono.move_to_wavelength(new_wavelength)
    # print(f"Monochromator moved to {new_wavelength:.2f} nm.")
    
    # # # Perform a wavelength scan
    start_wavelength = 400.0
    end_wavelength = 900.0
    # print(f"Scanning from {start_wavelength:.2f} nm to {end_wavelength:.2f} nm...")
    # mono.scan_wavelength(start_wavelength, end_wavelength, timeout=20)

    # Return the monochromator to the home position
    # time.sleep(10)
    mono.go_home()
    print("Monochromator returned to home position.")
    print(f"Current Wavelength: {mono.wavelength:.2f} nm")

    # Close the connection
    mono.close()
    print("Connection closed.")