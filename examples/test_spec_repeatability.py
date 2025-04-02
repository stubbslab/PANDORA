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

# # Get files
# # List all files in the directory
# import glob
# files = sorted(glob.glob(f"/Users/pandora_ctrl/Desktop/spectrometer/repeatability/20250311T122109_scanavg_00001*"))
# print(files)

# # compute the mean and std of the counts for each wavelength
# import numpy as np
# def readtxt(file):
#     data = np.loadtxt(file, skiprows=1)
#     return data[:, 0], data[:, 1]  # Return wavelengths and counts

# wav = readtxt(files[0])[0]  # Assuming all files have the same wavelength array
# data = np.array([readtxt(f)[1] for f in files])

# def get_stats(x):
#     mean_counts = np.median(x, axis=0)
#     std_counts = np.std(x-mean_counts, axis=0)
#     return mean_counts, std_counts

# mean_counts, std_counts = get_stats(data)
# residuals = data - mean_counts[:, np.newaxis]

# print("Mean counts shape:", mean_counts.shape)
# print("Std counts shape:", std_counts.shape)

# print("Mean signal:", np.mean(mean_counts))
# print("Std signal:", np.mean(std_counts))

# # plot the profiles
# import matplotlib.pyplot as plt
# plt.figure(figsize=(12, 6))
# plt.plot(wav, mean_counts, label='Mean Counts', color='blue')
# plt.fill_between(wav, mean_counts - std_counts/2, mean_counts + std_counts/2, color='blue', alpha=0.2, label='Std Dev')
# plt.xlabel('Wavelength (nm)')
# plt.ylabel('Counts')
# plt.title('Mean Spectrum with Std Dev')
# plt.legend()

# # Plot Residuals
# plt.figure(figsize=(12, 6))
# plt.fill_between(wav, -std_counts/2, std_counts/2, color='red', alpha=0.2, label='Residuals Std Dev')
# plt.xlabel('Wavelength (nm)')
# plt.ylabel('Residuals')
# plt.title('Residuals Spectrum')
# plt.legend()
