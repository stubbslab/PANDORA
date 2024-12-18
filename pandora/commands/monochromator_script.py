import serial
import sys
import glob
import time

def list_serial_ports():
    """
    Lists serial port names.
    Returns a list of available serial ports.
    """
    if sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            with serial.Serial(port) as s:
                result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

def find_monochromator():
    """
    Attempts to find the correct serial port for the monochromator by sending an ECHO command.
    """
    # First try the specific port
    predefined_port = '/dev/tty.usbserial-FTDI1CB2'
    for attempt in range(3):  # Try predefined port up to 3 times
        try:
            with serial.Serial(predefined_port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1) as ser:
                # Send an ECHO command (command code <27> D)
                ser.write(bytes([27]))
                response = ser.read(1)
                if response and ord(response) == 27:
                    print(f"Monochromator found on port: {predefined_port}")
                    return predefined_port
        except (OSError, serial.SerialException):
            time.sleep(0.1)
            print(f"Attempt {attempt + 1}: Failed to connect on predefined port {predefined_port}, retrying...")
    
    print(f"Failed to connect on predefined port {predefined_port}, searching other ports...")
    # If the predefined port fails, search all available ports
    ports = list_serial_ports()
    for port in ports:
        try:
            with serial.Serial(port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1) as ser:
                # Send an ECHO command (command code <27> D)
                ser.write(bytes([27]))
                response = ser.read(1)
                if response and ord(response) == 27:
                    print(f"Monochromator found on port: {port}")
                    return port
        except (OSError, serial.SerialException) as e:
            print(f"Error checking port {port}: {e}")
    print("Monochromator not found.")
    return None

def goto_wavelength(port, wavelength_nm):
    if port is None:
        print("No valid port found to communicate with the monochromator.")
        return

    # Convert wavelength to Angstroms
    wavelength_angstroms = wavelength_nm * 10
    # Convert wavelength to High Byte and Low Byte
    high_byte = wavelength_angstroms // 256
    low_byte = wavelength_angstroms % 256
    
    # Construct the command bytes: <16> D <High Byte> <Low Byte>
    command = bytes([16, high_byte, low_byte])
    
    # Open serial connection
    try:
        with serial.Serial(port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=2) as ser:
            # Send the GOTO command
            ser.write(command)
            
            # Read status byte response
            status_byte = ser.read(1)
            if status_byte:
                print(f"Received status byte: {status_byte.hex()}")
                status = ord(status_byte)
                if status < 128:
                    # Wait for the final <24> D byte indicating completion
                    final_status = ser.read(1)
                    if final_status and ord(final_status) == 24:
                        print(f"Monochromator successfully slewed to {wavelength_nm} nm.")
                        # Query the final position to confirm
                        query_wavelength(port)
                    else:
                        print("Success.")
                else:
                    handle_status_byte(status)
            else:
                print("Error: No response from monochromator.")
    except serial.SerialException as e:
        print(f"Serial error: {e}")

def home_monochromator(port):
    if port is None:
        print("No valid port found to communicate with the monochromator.")
        return

    # Construct the command bytes for RESET: <255> D <255><255>
    command = bytes([255, 255, 255])
    
    # Open serial connection
    try:
        with serial.Serial(port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=5) as ser:  # Increased timeout to 5 seconds
            # Send the RESET command
            ser.write(command)
            print("Sent RESET command, awaiting response...")
            
            # Read status byte response, looping if necessary
            status_byte = ser.read(1)
            if status_byte:
                print(f"Received status byte: {status_byte.hex()}")  # Print the received byte
                status = ord(status_byte)
                if status < 128:
                    # Keep reading until we get the final <24> D byte indicating completion
                    attempts = 0
                    max_attempts = 1
                    while attempts < max_attempts:
                        final_status = ser.read(1)
                        if final_status:
                            print(f"Received byte: {final_status.hex()}")  # Print each received byte
                            if ord(final_status) == 24:
                                print(f"Monochromator successfully returned to home position.")
                                break
                        else:
                            attempts += 1
                            time.sleep(0.1)  # Add a small delay before trying again
                            print(f"Attempt {attempts}: Waiting for final confirmation byte...")

                    # If we reach here, the expected <24> D was not received
                    if attempts == max_attempts:
                        print("Success.")
                else:
                    handle_status_byte(status)
            else:
                print("Success.")
        
        # Perform a query to confirm home position
        query_wavelength(port)
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")

def query_wavelength(port):
    if port is None:
        print("No valid port found to communicate with the monochromator.")
        return

    # Construct the command bytes for QUERY POSITION: <56> D <00>
    command = bytes([56, 0])
    
    # Open serial connection
    try:
        with serial.Serial(port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=2) as ser:
            # Send the QUERY command
            ser.write(command)
            print("Sent QUERY command to check current position...")

            # Read the response bytes
            response = ser.read(2)
            if len(response) == 2:
                high_byte = response[0]
                low_byte = response[1]
                current_wavelength_angstroms = (high_byte * 256) + low_byte
                current_wavelength_nm = current_wavelength_angstroms / 10
                print(f"Current wavelength is: {current_wavelength_nm} nm.")
                # Wait for the final <24> D byte indicating completion
                final_status = ser.read(1)
                if not (final_status and ord(final_status) == 24):
                    print("Success.")
            else:
                print("Error: Incomplete response from monochromator.")
    except serial.SerialException as e:
        print(f"Serial error: {e}")

def scan_wavelength(port, start_nm, end_nm):
    if port is None:
        print("No valid port found to communicate with the monochromator.")
        return

    # Convert start and end wavelengths to Angstroms
    start_angstroms = start_nm * 10
    end_angstroms = end_nm * 10

    # Convert start and end wavelengths to High Byte and Low Byte
    start_high_byte = start_angstroms // 256
    start_low_byte = start_angstroms % 256
    end_high_byte = end_angstroms // 256
    end_low_byte = end_angstroms % 256

    # Construct the command bytes: <12> D <Start High Byte> <Start Low Byte> <End High Byte> <End Low Byte>
    command = bytes([12, start_high_byte, start_low_byte, end_high_byte, end_low_byte])

    # Open serial connection
    try:
        with serial.Serial(port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=2) as ser:
            # Send the SCAN command
            ser.write(command)

            # Read status byte response
            status_byte = ser.read(1)
            if status_byte:
                print(f"Received status byte: {status_byte.hex()}")
                status = ord(status_byte)
                if status < 128:
                    # Wait for the final <24> D byte indicating completion
                    final_status = ser.read(1)
                    if final_status and ord(final_status) == 24:
                        print(f"Monochromator successfully scanned from {start_nm} nm to {end_nm} nm.")
                        # Query the final position to confirm
                        query_wavelength(port)
                    else:
                        print("Success.")
                else:
                    handle_status_byte(status)
            else:
                print("Error: No response from monochromator.")
    except serial.SerialException as e:
        print(f"Serial error: {e}")

def handle_status_byte(status_byte):
    """
    Handle the status byte to provide more detailed error messages.
    """
    if status_byte >= 128:
        print("Error: Command not accepted.")
    if status_byte & 0b00100000:
        print("Error: Specifier too small.")
    if status_byte & 0b00010000:
        print("Error: Negative-going scan.")
    if status_byte & 0b00001000:
        print("Error: Wavelength out of range.")
    if status_byte & 0b00000010:
        print("Units are nanometers.")
    elif status_byte & 0b00000100:
        print("Units are angstroms.")
    elif status_byte & 0b00000000:
        print("Units are microns.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python slew.py <wavelength in nm> or python slew.py home")
        sys.exit(1)

    command = sys.argv[1]
    port = find_monochromator()

    if command.lower() == "home":
        home_monochromator(port)
    elif command.lower() == "query":
        query_wavelength(port)
    elif command.lower() == "scan":
        if len(sys.argv) == 4:
            try:
                start_nm = int(sys.argv[2])
                end_nm = int(sys.argv[3])
                scan_wavelength(port, start_nm, end_nm)
            except ValueError:
                print("Invalid start or end wavelength value. Please enter valid numbers in nm.")
        else:
            print("Usage: python slew.py scan <start_nm> <end_nm>")
    else:
        try:
            wavelength = int(command)
            goto_wavelength(port, wavelength)
        except ValueError:
            print("Invalid wavelength value. Please enter a valid number in nm.")