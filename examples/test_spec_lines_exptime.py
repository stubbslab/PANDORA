import sys, os
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime
from pandora.utils.random import line, head

root = '/Users/pandora_ctrl/Desktop/spectrometer/exptime'
os.makedirs(root, exist_ok=True)

# Set parameters
# exptimes = [2,3,5,6,9,12]
# exptimes+= [12+5*(i+1) for i in range(10)]
# exptimes+= [62+20*(i+1) for i in range(4)]
# exptimes = [142+50*(i+1) for i in range(4)]
exptimes = [1000+500*i for i in range(4)]
scanvg = 10

# Set up logging
initialize_central_logger("stellarnet.log", "INFO", verbose=True)

# Make a timestamp
# timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
timestamp = "20250311T153442"

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

hg2_lines = {
    # Mercury (Hg) lines
    "Hg01": 253.65200,
    "Hg02": 296.72840,
    "Hg03": 302.15060,
    "Hg04": 313.15560,
    "Hg05": 334.14820,
    "Hg06": 365.01520,
    # "Hg07": 404.65650,
    "Hg08": 435.83430,
    "Hg09": 546.07350,
    "Hg10": 576.95980,
    # "Hg11": 579.06630,

    # Argon (Ar) lines
    "Ar01":  696.54310,
    "Ar02":  706.72180,
    "Ar03":  714.70420,
    "Ar04":  727.29360,
    "Ar05":  738.39800,
    "Ar06":  750.38690,
    "Ar07":  763.51100,
    "Ar08":  772.37610,
    "Ar09":  794.81760,
    "Ar10":  800.61580,
    "Ar11":  811.53110,
    "Ar12":  826.45180,
    "Ar13":  842.46480,
    "Ar14":  912.29670,
    "Ar15":  922.44990,
    "Ar16":  935.42200,
    "Ar17":  949.74290,
    "Ar18":  965.77860,
    "Ar19":  978.45100,
    "Ar20": 1047.00000,
    "Ar21": 1066.66000,
    "Ar22": 1088.46000,
    "Ar23": 1090.65000,
}

# compute the mean and std of the counts for each wavelength
import numpy as np
def readtxt(file):
    data = np.loadtxt(file, skiprows=1)
    return data[:, 1]  # Return counts

wav = readtxt(f"{root}/{timestamp}_{exptime}ms.txt")[0]  # Assuming all files have the same wavelength array
window = 4

def crop_line(wav, counts, line_wavelength, window):
    # Crop the data around the line
    mask = (wav >= line_wavelength - window) & (wav <= line_wavelength + window)
    return wav[mask], counts[mask]

line_strength = {}
line_positions = {}

# Loop over lines
for line_name, line_wavelength in hg2_lines.items():
    print(f"{line_name}: {line_wavelength}")
    # loop over the exptimes
    lineheights = []
    linepositions = []
    for exptime in exptimes:
        print(f"  Exptime: {exptime} ms")
        # load the spectrum
        data = readtxt(f"{root}/{timestamp}_{exptime}ms.txt")
        # crop the data around the line
        # Assuming the wavelength range is around the line wavelength
        # For simplicity, let's assume a 10 nm window around the line
        cropped_wav, cropped_counts = crop_line(wav, data, line_wavelength, window)

        # get the peak position and the peak height
        peak_height = np.max(cropped_counts)
        peak_position = cropped_wav[np.argmax(cropped_counts)]
        # print(f"    Peak position: {peak_position:.2f} nm, Peak height: {peak_height:.2f}")
        lineheights.append(peak_height)
        linepositions.append(peak_position)
    # print the max/min counts for this line
    print(f"  {line_name}: Max counts: {max(lineheights):.2f}, Min counts: {min(lineheights):.2f}")
    # print the max/mean/min positions for this line
    print(f"  {line_name}: Max position: {max(linepositions):.2f} nm, Mean position: {np.mean(linepositions):.2f} nm, Min position: {min(linepositions):.2f} nm")
    line_strength[line_name] = lineheights
    line_positions[line_name] = linepositions

# Save the dictionaries as pandas dataframes
import pandas as pd
line_strength_df = pd.DataFrame(line_strength, index=exptimes)
line_positions_df = pd.DataFrame(line_positions, index=exptimes)

# append the two dataframes
result_df = pd.concat([line_strength_df, line_positions_df], axis=1, keys=['Strength', 'Position'])
result_df.to_csv(f"{root}/{timestamp}_line_strength_positions.csv")


