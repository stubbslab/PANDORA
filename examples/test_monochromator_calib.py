import sys
import numpy as np
import time
import os

sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.controller.monochromator import MonochromatorController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime

root = "/Users/pandora_ctrl/Desktop/monochromator"

### Setup
buffer = 50 # ms
exptime = 20 # ms

# Check lambda changes
lambda0 = 300
lambdaEnd = 1100
steps = 5

# Create a vector of wavelengths
lambdaVec = np.arange(lambda0, lambdaEnd+steps, steps)

# Set up logging
initialize_central_logger("monochroamtorcalib.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
path = f"{root}/calib_{timestamp}"
os.makedirs(path, exist_ok=True)

# Set up the spectrometer
spectrometer = spectrometerController()
spectrometer.set_scan_avg(100)
spectrometer.set_integration_time(exptime)

# Create an instance of the MonochromatorController
SERIAL_PORT = "/dev/tty.usbserial-FTDI1CB2" # Serial port name
mono = MonochromatorController(SERIAL_PORT)

mono.go_home()
mono.move_to_wavelength(180)
wav0, counts0 = spectrometer.get_spectrum()
spectrometer.save_spectrum(wav0, counts0, f"{path}/{timestamp}_{exptime}ms_dark", exptime=exptime)
np.savetxt(f"{path}/{timestamp}_wavelength.txt", lambdaVec)

for lbd in lambdaVec:
    print(f"Moving to {lbd} nm")
    mono.move_to_wavelength(lbd)
    time.sleep(buffer/1000)
    wav, counts = spectrometer.get_spectrum()
    spectrometer.save_spectrum(wav, counts, f"{path}/{timestamp}_{exptime}ms_wav_{lbd*10:04d}angs", exptime=exptime)