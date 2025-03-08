import sys
import numpy as np
import time

sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.controller.monochromator import MonochromatorController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime

root = "/Users/pandora_ctrl/Desktop/monochromator"

### Setup
buffer = 100 # ms
exptime = 28 # ms

lambda0 = 300
lambdaEnd = 1000
steps = 100

# Create a vector of wavelengths
lambdaVec = np.arange(lambda0, lambdaEnd+steps, steps)

# Set up logging
initialize_central_logger("monochroamtorcalib.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

# Set up the spectrometer
spectrometer = spectrometerController()
spectrometer.set_scan_avg(10)
spectrometer.set_integration_time(exptime)

# Create an instance of the MonochromatorController
SERIAL_PORT = "/dev/tty.usbserial-FTDI1CB2" # Serial port name
mono = MonochromatorController(SERIAL_PORT)

mono.go_home()
wav0, _ = spectrometer.get_spectrum()
counts0 = np.zeros_like(wav0)

for lbd in lambdaVec:
    print(f"Moving to {lbd} nm")
    mono.move_to_wavelength(lbd)
    time.sleep(buffer/1000)
    wav, counts = spectrometer.get_spectrum()
    spectrometer.save_spectrum(wav, counts, f"{root}/calib_{timestamp}_{exptime}ms_wav_{lbd*10:04d}angs")
    counts0 = np.max([counts0, counts], axis=0)

spectrometer.save_spectrum(wav0, counts0, f"{root}/calib_{timestamp}_{exptime}ms")