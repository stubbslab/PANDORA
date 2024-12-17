import serial
import time
import logger

class MonochromatorController:
    def __init__(self, port, baudrate=9600):
        """
        Initialize the MonochromatorController object.

        Parameters:
        - port (str): The serial port to connect to (e.g., 'COM3' or '/dev/ttyUSB0').
        """
        self.port = port
        self.ser = None
        self.baudrate = baudrate

        # Set up logging
        self.logger = logger.get_logger(f"Monochromator")

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

    def go_home(self, timeout=5):
        """
        Move the monochromator to the home position.
        """
        self.connect(timeout=timeout)

        if not self._is_connected():
            self.logger.error("Error: Could not establish connection to monochromator.")
            return

        # Command for RESET: <255> D <255><255>
        command = bytes([255, 255, 255])
        self._write(command)
        self.logger.info("Sent RESET command, awaiting response...")

        # Read status byte response
        status_byte = self._read(1)
        if status_byte:
            status = status_byte[0]
            if status < 128:
                # Wait for the final <24> D byte indicating completion
                final_status = self._read(1)
                if final_status and final_status[0] == 24:
                    self.logger.info("Monochromator successfully returned to home position.")
                else:
                    self.logger.warning("Warning: Did not receive final confirmation byte after reset.")
            else:
                self._handle_status_byte(status)
        else:
            self.logger.error("Error: No response from monochromator during reset.")

        # close the connection
        self.close()

    def get_wavelength(self):
        """
        Get the current wavelength setting of the monochromator.

        Returns:
        - float: The current wavelength in nanometers, or None if an error occurred.
        """
        self.connect()
        if not self._is_connected():
            self.logger.error("Error: Could not establish connection to monochromator.")
            return

        # Command for QUERY POSITION: <56> D <00>
        command = bytes([56, 0])
        self._write(command)
        self.logger.info("Sent QUERY command to check current wavelength...")

        response = self._read(2)
        if len(response) == 2:
            high_byte, low_byte = response[0], response[1]
            current_wavelength_angstroms = (high_byte << 8) | low_byte
            current_wavelength_nm = current_wavelength_angstroms / 10
            self.logger.info(f"Current wavelength is: {current_wavelength_nm} nm.")

            # Read final status byte
            final_status = self._read(1)
            if final_status and final_status[0] == 24:
                self.logger.info("Query completed successfully.")
            else:
                self.logger.warning("Warning: Did not receive final confirmation byte after query.")

            current_wavelength_nm
        else:
            self.logger.error("Error: Incomplete response from monochromator during get_wavelength.")
            current_wavelength_nm = None
        # close connection
        self.close()
        return current_wavelength_nm

    def set_wavelength(self, wavelength_nm, timeout=2):
        """
        Move the monochromator to a specified wavelength.

        Parameters:
        - wavelength_nm (float): The target wavelength in nanometers.
        """
        self.connect(timeout=2)

        if not self._is_connected():
            self.logger.error("Error: Could not establish connection to monochromator.")
            return

        # Convert wavelength to Angstroms and split into high and low bytes
        wavelength_angstroms = wavelength_nm * 10
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
                # Wait for the final <24> D byte indicating completion
                final_status = self._read(1)
                if final_status and final_status[0] == 24:
                    self.logger.info(f"Monochromator successfully moved to {wavelength_nm} nm.")
                else:
                    self.logger.warning("Warning: Did not receive final confirmation byte after moving to wavelength.")
            else:
                self._handle_status_byte(status)
        else:
            self.logger.error("Error: No response from monochromator during set_wavelength.")

        # close the connection
        self.close()

    def scan_wavelength(self, start_nm, end_nm):
        """
        Scan the monochromator from a start wavelength to an end wavelength.

        Parameters:
        - start_nm (float): The start wavelength in nanometers.
        - end_nm (float): The end wavelength in nanometers.
        """
        self.connect()

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
                # Wait for the final <24> D byte indicating completion
                final_status = self._read(1)
                if final_status and final_status[0] == 24:
                    self.logger.info(f"Monochromator successfully scanned from {start_nm} nm to {end_nm} nm.")
                else:
                    self.logger.warning("Warning: Did not receive final confirmation byte after scan.")
            else:
                self._handle_status_byte(status)
        else:
            self.logger.error("Error: No response from monochromator during scan.")

        # close the connection
        self.close()

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
            self.logger.error("Error: Serial connection not established.")
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