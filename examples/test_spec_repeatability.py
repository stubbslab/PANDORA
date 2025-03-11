import sys, os
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime
from pandora.utils.random import line, head

root = '/Users/pandora_ctrl/Desktop/spectrometer/repeatability'
os.makedirs(root, exist_ok=True)

# Set parameters
exptime = 35 #ms
## Repeatability test
nreaptss = [10000, 1000, 100, 10]
scanvgs = [1, 10, 100, 1000]

# Set up logging
initialize_central_logger("stellarnet.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

# Set up the spectrometer
spectrometer = spectrometerController()

# 35ms integration time
spectrometer.set_integration_time(exptime)

## Repeatability test
for scanavg, nsteps in zip(scanvgs, nreaptss):
    line()
    head(f"Part 1 - Scan avg = {scanavg}, exptime = {exptime}ms, nrepeats = {nsteps}")
    # 1 average scan test
    spectrometer.set_scan_avg(scanavg)

    for i in range(nsteps):
        # Get spectrum
        wav, counts = spectrometer.get_spectrum()
        # Save the spectrum
        spectrometer.save_spectrum(wav, counts, f"{root}/{timestamp}_scanavg_{scanavg:05d}_rep_{(i+1):05d}", exptime)

# Close the spectrometer
spectrometer.close()
print("Done!")