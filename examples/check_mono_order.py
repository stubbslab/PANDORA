"""
This scripts tests the impact of changing the order of monochromator. 

The measurements steps are:
- Set to wav 500nm
- Measure the spectrum
- Move order clockwise
- Measure the spectrum
- Move order clockwise
- Measure the spectrum
- x2 Move order counterclockwise
- Move order counterclockwise
- Measure the spectrum
- Move order counterclockwise
- Measure the spectrum
- x2 Move order clockwise
"""

import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.controller.stellarnet import spectrometerController
from pandora.controller.monochromator import MonochromatorController
from pandora.utils.logger import initialize_central_logger  
from datetime import datetime

def take_spectrum(order, axis=None):
    if axis is not None:
        mono.change_order(axis)

    # Get spectrum
    wav, counts = spectrometer.get_spectrum()
    # Save the spectrum
    spectrometer.save_spectrum(wav, counts, f"clockordertest_{timestamp}_500nm_{order}")

# Set up logging
initialize_central_logger("clockordertest.log", "INFO", verbose=True)

# Make a timestamp
timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")

# Set up the spectrometer
spectrometer = spectrometerController()
spectrometer.set_scan_avg(100)
spectrometer.set_integration_time(28)

# Create an instance of the MonochromatorController
SERIAL_PORT = "/dev/tty.usbserial-FTDI1CB2" # Serial port name
mono = MonochromatorController(SERIAL_PORT)

print("Starting test")
# Set the monochromator to a new wavelength
mono.move_to_wavelength(500)

# Take the first spectrum at zero order
take_spectrum("m0")

# Move order clockwise
take_spectrum("m1", "clockwise")

# Move order clockwise
take_spectrum("m2","clockwise")

# Return to zero order
mono.change_order("counterclockwise")
mono.change_order("counterclockwise")

# Set to -1 order
take_spectrum("m-1","counterclockwise")

# Move order counterclockwise
take_spectrum("m-2","counterclockwise")

# Analysis
# names = ["m0","m1","m2","m-1","m-2"]
# colors = ["k","firebrick","red","tab:blue","blue"]
# lss = ["-","--","--","--","--"]
# data = dict().fromkeys(names)
# for i,n in enumerate(names):
#     data[n] = np.genfromtxt(files[i])

# import matplotlib.pyplot as plt
# def plot_spec(d,axis=None, is_norm=True):
#     if axis is None: axis = plt.gca()
#     shift = 0
#     for i,n in enumerate(names):
#         if is_norm:
#             if i>1: shift= (i-1)*0.2
#             axis.plot(d[n][50:,0],shift+(d[n][50:,1]-np.median(d[n][:,1]))/np.max(d[n][:,1]),ls=lss[i],label=n,color=colors[i])
#         else:
#             axis.plot(d[n][50:,0],d[n][50:,1],ls=lss[i],label=n,color=colors[i])
#     axis.set_xlabel('wavelength [nm]')
    
#     wavpeaks = []
#     for i,n in enumerate(names):
#         peak = np.nanmax(data[n][:,1])
#         argpeak = np.nanargmax(data[n][:,1])
#         wavpeak = data[n][argpeak,0]
#         wavpeaks.append(wavpeak)

#     if is_norm:
#         peak_offset= d[names[0]][:,1]-d[names[1]][:,1]
#         axis.set_ylabel('Relative Strength normalized by the peak')
#         axis.set_title('Peak offset is {:.2f} nm'.format(wavpeaks[1]-wavpeaks[0]))

#     else:
#         argpeak = np.nanargmax(data[names[0]][:,1])
#         wavpeak = data[names[0]][argpeak,0]
#         axis.set_ylabel('Counts [ADU]')
#         axis.set_title(f"measured/commanded: {wavpeak} nm/500 nm")
#     axis.legend()
# def plot_line_peak(data,axis=None,**kwargs):
#     if axis is None: axis = plt.gca()
#     wavpeaks = []
#     for i,n in enumerate(names):
#         peak = np.nanmax(data[n][:,1])
#         argpeak = np.nanargmax(data[n][:,1])
#         wavpeak = data[n][argpeak,0]
#         wavpeaks.append(wavpeak)
#         axis.plot(n, peak, color=colors[i], marker="o")
#     axis.set_yscale('log')
#     axis.set_ylim(1e3, 1e5)
#     axis.set_xlabel('Monochromator Order')
#     axis.set_ylabel('Peak Strength [ADU]')
    
    
# fig, axis = plt.subplots(2,1,figsize=(10,10))
# plot_spec(data, axis=axis[0])
# plot_line_peak(data, axis=axis[1])

