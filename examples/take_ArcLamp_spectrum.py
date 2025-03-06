from pandora.controller.spectrometer import spectrometerController
from datetime import datetime

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%d")

# Set up the spectrometer
spectrometer = spectrometerController()

# 10ms integration time
spectrometer.set_integration_time(10)

# 100 average scans
spectrometer.set_scan_avg(100)

# Get spectrum
wav, counts = spectrometer.get_spectrum()

# Save the spectrum
spectrometer.save_spectrum(wav, counts, f"ArcLamp_spectrum_raw_{timestamp}")

# Plot spectrum
spectrometer.plot_spectrum(wav, counts)

# Close the spectrometer
spectrometer.close()