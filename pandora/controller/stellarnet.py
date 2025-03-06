import logging
import time
"""
This scripts provides a class to control the StellarNet Black Comet (BLACK CXR-SR-100) spectrometer.

Needs to install:
    Python SDK Stellarnet_driver3


Paramaters, Detailed Description:
    Detector integration time:
    This should be adjusted for each experiment to maximize the detector output and
    signal to noise ratio. The input is given in miliseconds, the minimum is 1.

    XTiming resolution control: 1/2/3
    This feature provides increased optical resolutions. Selection 1 is the lowest optical
    resolution and is synchronized with the selected detector integration. In general, if
    your requirements for optical resolution are greater than 1nm, then selection 1 is ok.
    Selection 2 or 3 slows the digitizer & detector clock by a factor of 2 and 4
    respectively. With XT levels 2 & 3 you will be able to observe increasingly higher
    resolutions. The detectors signal amplifier improves with slower throughput. When
    selecting XT level 2/3 the detector integration time must be increased to 30ms or
    longer to avoid sync delays.

    Smoothing level 0, 1, 2, 3, or 4
    This performs data smoothing by applying a moving average of adjacent pixels to the
    data arrays. For example, a Pixel Boxcar setting of 1 would average 5 total pixels: 2
    pixels on the left, 2 pixels on the right, and one in the center. 0 performs NO data
    smoothing.
    Smoothing/Total pixels averaged
            0/0
            1/5
            2/9
            3/17
            4/33

    Number of scans to average: (1…)
    Sets the number of spectra to signal average. Please note that the real-time display is
    updated AFTER these numbers of spectra have been acquired. This option provides a
    smoothing in the Y-axis, effectively increasing the system signal to noise by the
    square root of the number of scans being averaged. Set the averaging to the highest
    number

    Temperature: 
    Set temperature compensation to reflect on the returned on the spectrum data. There are
    15 “optically black” pixels on StellarNet’s SONY ILX-511b CMOS detectors which are
    not hit by light during an acquisition. They provide a continuous measurement of the
    average dark spectrum and can be used to adjust for baseline drift during an experiment.
    In other words, this feature compensates for changes in the baseline due to temperature.

Installation instructions:
    https://harvardwiki.atlassian.net/wiki/spaces/hufasstubbsgroup/pages/192447174/StellarNet+Spectrometer+Setup
    https://drive.google.com/file/d/1-irqmjaDd0maluRi3hEQq3wDTrWFC3lP/view?usp=sharing

"""
import stellarnet_driver3 as sn 
class spectrometerController:
    def __init__(self, inttime_ms=1, scan_avg=1, xtiming=3, smooth=0, type=None):
        """
        Initialize the spectrometerController object.

        Parameters:
            inttime_ms (int): Integration time in milliseconds.
            scan_avg (int): Number of scans to average.
            xtiming (int): 1/2 or 3, spectral resolution mode.
            smooth (int): Smoothing size.
            type (str): Place holder for the config file.
        
        Example:
            from pandora.controller.stellarnet import spectrometerController
            spectrometer = spectrometerController()
            
            # 10ms integration time
            spectrometer.set_integration_time(10)

            # 100 average scans
            spectrometer.set_scan_avg(100)
            
            # Get spectrum
            wav, counts = spectrometer.get_spectrum()

            # Plot spectrum
            spectrometer.plot_spectrum(wav, counts)
        """
        self.params = {'inttime': inttime_ms, 'scan_avg': scan_avg, 
                       'xtiming': xtiming, 'smooth': smooth}

        # Set up logging
        self.logger = logging.getLogger(f"pandora.spectrometer")
        self.logger.info("Initializing the spectrometer controller")
        self.initialize()

    def initialize(self):
        """
        Initialize the spectrometer (USB connection).
        """
        # self.logger.info("Initializing the spectrometer controller")
        spectrometer, wav = sn.array_get_spec(0) # 0 for first channel and 1 for second channel , up to 127 spectrometers

        # Call to Enable or Disable External Trigger to by default is Disbale=False -> with timeout
        # Enable or Disable Ext Trigger by Passing True or False, If pass True than Timeout function will be disable, so user can also use this function as timeout enable/disbale 
        sn.ext_trig(spectrometer, True)

        # Get current device class
        self.device = spectrometer
        self.wav = wav

        # Device ID
        self.deviceID = sn.getDeviceId(spectrometer)

        # Set initial params
        self.set_params()
        pass

    def set_params(self):
        # Only call this function on first call to get spectrum or when you want to change device setting.
        # -- Set last parameter to 'True' throw away the first spectrum data because the data may not be true for its inttime after the update.
        # -- Set to 'False' if you don't want to do another capture to throw away the first data, however your next spectrum data might not be valid.
        inttime, scansavg, smooth, xtiming = self.params['inttime'], self.params['scan_avg'], self.params['smooth'], self.params['xtiming']
        sn.setParam(self.device, inttime, scansavg, smooth, xtiming, True)

    def set_integration_time(self, inttime_ms):
        """Set integration time in ms."""
        self.device['device'].set_config(int_time=inttime_ms)
        self.params['inttime'] = inttime_ms
        self.set_params()
    
    def set_scan_avg(self, scan_avg):
        """Set number of samples to average."""
        # self.device['device'].set_config(scans_to_avg=scan_avg)
        self.params['scan_avg'] = scan_avg
        self.set_params()
        pass

    def set_smooth(self, smooth):
        """Set smooth spec size."""
        # self.device['device'].set_config(x_smooth=smooth)
        self.params['smooth'] = smooth
        self.set_params()
        pass

    def set_xtiming(self, xtiming):
        """Set xtiming"""
        self.params['xtiming'] = xtiming
        self.set_params()
        pass

    def set_temperature_compensation(self, enable):
        """Enable or disable temperature compensation."""
        sn.temp_comp(self.device, enable)
        pass

    def get_params(self):
        for key, value in zip(self.params.keys(), self.params.values()):
            print(f"{key}: {value}")
        pass

    def get_spectrum(self):
        # Get spectrometer data - Get BOTH X and Y in single return
        data = sn.array_spectrum(self.device, self.wav) # get specturm for the first time
        wavelengths = data[:,0] 
        counts = data[:,1]
        return wavelengths, counts
    
    def get_info(self):
        version = sn.version()
        print(version)
        print('Spec device ID: ', self.deviceID)

    def save_spectrum(self, wavelengths, counts, filename):
        """
        Save the spectrum to a file.
        
        Parameters:
            wavelengths (array): Array of wavelengths.
            counts (array): Array of counts.
            filename (str): Name of the file.
        """
        with open(f"{filename}.txt", "w") as f:
            # put a header in the file
            f.write(f"# Wavelength (nm)\tCounts\n")
            # put the date and time in the file
            # f.write(f"# Date: {time.strftime('%Y-%m-%d')}, Time: {time.strftime('%H:%M:%S')}\n")
            for i in range(len(wavelengths)):
                f.write(f"{wavelengths[i]:0.2f}\t{counts[i]:0.0f}\n")
        pass

    def is_connected(self):
        """ Check if the spectrometer is connected.
        
        Returns:
            bool: True if the spectrometer is connected, False otherwise.
        """
        return sn.deviceConnectionCheck(self.device)

    def close(self):
        """
        Resets the spectrometer and closes the USB connection.
        1. Reset the spectrometer.
        2. Close the USB connection.
        """
        # Release the spectrometer before ends the program
        sn.reset(self.device)
        self.device = None

    def plot_spectrum(self, wavelengths, counts):
        """
        Plot the spectrum.
        
        Parameters:
            wavelengths (array): Array of wavelengths.
            counts (array): Array of counts.
        """
        import matplotlib.pyplot as plt
        plt.plot(wavelengths, counts)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Counts')
        plt.title('Spectrum')
        plt.show()

if __name__ == "__main__":
    
    spectrometer = spectrometerController()
    
    # 10ms integration time
    spectrometer.set_integration_time(10)
    
    # 100 average scans
    spectrometer.set_scan_avg(100)
    
    # Get spectrum
    wav, counts = spectrometer.get_spectrum()

    # Plot spectrum
    spectrometer.plot_spectrum(wav, counts)
    
    # Close the spectrometer
    spectrometer.close()