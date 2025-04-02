import os, sys
import numpy as np
import time

sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.controller.monochromator import MonochromatorController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime

root = "/Users/pandora_ctrl/Desktop/monochromator"

### Setup
nrepetitions = 100
lambdaCen = 400
lambda0 = 300
lambdaEnd = 500
exptime = 20 # ms
buffer = 50 # ms

# Set up the sequence
sequence1 = [lambda0, lambdaCen, lambdaEnd]
sequence2 = [lambdaEnd, lambdaCen, lambda0]

# Set up logging
initialize_central_logger("monochroamtorcalib.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
path = f"{root}/backlash_{timestamp}"
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

for ii in range(nrepetitions):
    for lbd in sequence1:
        print(f"Moving to {lbd} nm")
        mono.move_to_wavelength(lbd)
        if lbd==lambdaCen:
            wav, counts = spectrometer.get_spectrum()
            spectrometer.save_spectrum(wav, counts, f"{path}/{timestamp}_{exptime}ms_wav_right_{ii:02d}_{lbd*10:04d}angs", exptime=exptime)
        time.sleep(buffer/1000)

    for lbd in sequence2:
        print(f"Moving to {lbd} nm")
        mono.move_to_wavelength(lbd)
        if lbd==lambdaCen:
            wav, counts = spectrometer.get_spectrum()
            spectrometer.save_spectrum(wav, counts, f"{path}/{timestamp}_{exptime}ms_wav_left_{ii:02d}_{lbd*10:04d}angs", exptime=exptime)
        time.sleep(buffer/1000)