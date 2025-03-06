import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime

root = '/Users/pandora_ctrl/Desktop/spectrometer'

# Set up logging
initialize_central_logger("stellarnet.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

# Set up the spectrometer
spectrometer = spectrometerController()

# 100 average scans
spectrometer.set_scan_avg(100)

# Take a short exposure
is_short_exposure = True
if is_short_exposure:
    # 9ms integration time
    spectrometer.set_integration_time(9)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"{root}/ArcLamp_spectrum_short_exposure_{timestamp}")

is_long_exposure = False
if is_long_exposure:
    # 9ms integration time
    spectrometer.set_integration_time(90)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"ArcLamp_spectrum_long_exposure_{timestamp}")

# Plot spectrum
spectrometer.plot_spectrum(wav, counts)

# Close the spectrometer
spectrometer.close()