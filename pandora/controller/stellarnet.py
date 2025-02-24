import logging
import time
"""
This scripts provides a class to control the stellar net spectrometer.

"""
import stellarnet_driver3 as sn 
class spectrometerController:
    def __init__(self, inttime_ms=1, scan_avg=1, xtiming=3, smooth=0, type=None):
        """
        Initialize the spectrometerController object.

        Parameters:
            inttime_ms (int): Integration time in milliseconds.
            scan_avg (int): Number of scans to average.
            xtiming (int): Timing size.
            smooth (int): Smoothing size.
            type (str): Place holder for the config file.
        
        StellarNet installation on:
            https://harvardwiki.atlassian.net/wiki/spaces/hufasstubbsgroup/pages/192447174/StellarNet+Spectrometer+Setup
            https://drive.google.com/file/d/1-irqmjaDd0maluRi3hEQq3wDTrWFC3lP/view?usp=sharing

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
        self.params['inttime'] = inttime_ms
        self.set_params()
    
    def set_scan_avg(self, scan_avg):
        """Set number of samples to average."""
        self.params['scan_avg'] = scan_avg
        self.set_params()
        pass

    def set_smooth(self, smooth):
        """Set smooth spec size."""
        self.params['smooth'] = smooth
        self.set_params()
        pass

    def set_xtiming(self, xtiming):
        """Set xtiming"""
        self.params['xtiming'] = xtiming
        self.set_params()
        pass

    def get_params(self):
        for key, value in zip(self.params.keys, self.params.values):
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