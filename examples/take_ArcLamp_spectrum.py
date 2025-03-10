import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime

root = '/Users/pandora_ctrl/Desktop/spectrometer'
is_very_short_exposure = True
is_short_exposure = True
is_long_exposure = True
is_very_long_exposure = True

# Set up logging
initialize_central_logger("stellarnet.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

# Set up the spectrometer
spectrometer = spectrometerController()

# 1000 average scans
spectrometer.set_scan_avg(1000)

# Take a short exposure
if is_very_short_exposure:
    exptime = 5
    # 9ms integration time
    spectrometer.set_integration_time(exptime)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"{root}/ArcLamp_spectrum_{exptime}ms_exposure_{timestamp}", exptime)

if is_short_exposure:
    exptime = 35
    # 9ms integration time
    spectrometer.set_integration_time(exptime)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"{root}/ArcLamp_spectrum_{exptime}ms_exposure_{timestamp}", exptime)

if is_long_exposure:
    exptime = 49
    # 49ms integration time
    spectrometer.set_integration_time(exptime)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"{root}/ArcLamp_spectrum_{exptime}ms_exposure_{timestamp}", exptime)

if is_very_long_exposure:
    exptime = 100
    # 130ms integration time
    spectrometer.set_integration_time(exptime)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"{root}/ArcLamp_spectrum_{exptime}ms_exposure_{timestamp}", exptime)

# Plot spectrum
# spectrometer.plot_spectrum(wav, counts)

# Close the spectrometer
spectrometer.close()