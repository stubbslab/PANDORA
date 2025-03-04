import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.monochromator import MonochromatorController
from pandora.utils.logger import initialize_central_logger  

new_wavelength = int(input("Enter the wavelength: "))
# Set up logging
initialize_central_logger("monochromator.log", "INFO", verbose=True)

# Serial port name
SERIAL_PORT = "/dev/tty.usbserial-FTDI1CB2"

# Create an instance of the MonochromatorController
mono = MonochromatorController(SERIAL_PORT)


# Make sure the units are angstroms
mono.set_units("angstroms")

# Get the current wavelength
mono.get_wavelength(sleep=0.0)

# Set the monochromator to a new wavelength
mono.move_to_wavelength(new_wavelength)