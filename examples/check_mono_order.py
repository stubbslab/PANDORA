"""
This scripts tests the impact of changing the order of monochromator. 

The measurements steps are:
- Set to wav 500nm
- Measure the spectrum
- Move order clockwise
- Measure the spectrum
- Move order clockwise
- Measure the spectrum
- x2 Move order counterclockwise
- Move order counterclockwise
- Measure the spectrum
- Move order counterclockwise
- Measure the spectrum
- x2 Move order clockwise
"""

import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.controller.monochromator import MonochromatorController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime

def take_spectrum(order, axis=None):
    if axis is not None:
        mono.change_order(axis)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()
    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"clockordertest_{timestamp}_500nm_{order}")

# Set up logging
initialize_central_logger("clockordertest.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

# Set up the spectrometer
spectrometer = spectrometerController()
spectrometer.set_scan_avg(100)
spectrometer.set_integration_time(28)

# Create an instance of the MonochromatorController
SERIAL_PORT = "/dev/tty.usbserial-FTDI1CB2" # Serial port name
mono = MonochromatorController(SERIAL_PORT)

print("Starting test")
# Set the monochromator to a new wavelength
mono.move_to_wavelength(500)

# Take the first spectrum at zero order
take_spectrum("m0")

# Move order clockwise
take_spectrum("m1", "clockwise")

# Move order clockwise
take_spectrum("m2","clockwise")

# Return to zero order
mono.change_order("counterclockwise")
mono.change_order("counterclockwise")

# Set to -1 order
take_spectrum("m-1","counterclockwise")

# Move order counterclockwise
take_spectrum("m-2","counterclockwise")