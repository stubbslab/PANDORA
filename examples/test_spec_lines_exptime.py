import sys, os
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime
from pandora.utils.random import line, head

root = '/Users/pandora_ctrl/Desktop/spectrometer/exptime'
os.makedirs(root, exist_ok=True)

# Set parameters
exptimes = [2,3,5,6,9,12]
exptimes+= [12+5*(i+1) for i in range(10)]
exptimes+= [62+20*(i+1) for i in range(4)]
scanvg = 1000

# Set up logging
initialize_central_logger("stellarnet.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

# Set up the spectrometer
spectrometer = spectrometerController()
spectrometer.set_scan_avg(scanvg)
spectrometer.set_xtiming(3)

for exptime in exptimes:
    line()
    head(f"Part 1 - Scan avg = {scanvg}, exptime = {exptime}ms")
    # 35ms integration time
    spectrometer.set_integration_time(exptime)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"{root}/{timestamp}_{exptime}ms", exptime)

# Close the spectrometer
spectrometer.close()
print("Done!")