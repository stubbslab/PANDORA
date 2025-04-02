import logging
import pyvisa
import numpy as np


from pandora.utils.socket_helper import is_port_open

class KeysightController():
    DEFAULT = {"mode": 'CURR',
               "rang": 'AUTO',
               'nplc': 1,
               'nsamples': 10,
               'delay': 0,
               'interval': 2e-3,
               'aper': 'AUTO'
               }
    """KeysightController class to handle communication with Keysight devices.

    Args:
        name (str): Name of the Keysight device.
        keysight_ip (str): IP address of the Keysight device.
        timeout_ms (int): Timeout in milliseconds for the connection.
    
    Example:
        keysight = KeysightController(name="K01", keysight_ip="169.254.56.239")
        keysight.get_device_info()
        keysight.activate()
        keysight.deactivate()
        keysight.close()

    """
    def __init__(self, name, keysight_ip="169.254.56.239", timeout_ms=5000, settings=DEFAULT):
        if name is None:
            raise ValueError("Keysight name cannot be None.")
        if keysight_ip is None:
            raise ValueError("Keysight IP address cannot be None.")
        
        ## Initialize the Keysight State Parameters
        self.name = name
        self.keysight_ip = keysight_ip
        self.resource_string = f"TCPIP::{keysight_ip}::hislip0,4880::INSTR"
        self.timeout_ms = timeout_ms

        self.logger = logging.getLogger(f"pandora.keysight.{name}")

        ## Initialize the Keysight State
        self.tracked_properties = ['mode', 'nplc', 'rang', 'delay', 'interval', 'nsamples']
        self.params = settings
        self.initialize()

        self.get_acquisition_time()

    def initialize(self):
        self.logger.info(f"Initializing Keysight State.")
        self.rm = pyvisa.ResourceManager('@py')  # Use '@py' for PyVISA-py backend
        self.instrument = None
        self._connect()
        self.on()

        # Set default settings
        self.set_default_settings()

    def set_default_settings(self):
        """
        Synchronizes the instrument's settings with the expected parameters.
        """
        self.logger.info(f"Setting default settings.")
        for p in self.tracked_properties:
            getattr(self, f'set_{p}')(self.params[p])
        self.get_params(verbose=False)

    def close(self):
        if self.instrument is not None:
            self.logger.info(f"Closing Keysight connection.")
            self.instrument.close()
            print("Keysight connection closed.")
        else:
            self.logger.warning(f"No connection to close.")

    def _connect(self):
        """Establish a connection to the instrument."""
        if not is_port_open(self.keysight_ip, 4880, timeout=self.timeout_ms/1000):
            self.logger.error(f"Cannot reach {self.keysight_ip}:4880 within {self.timeout_ms/1000:.2f} sec. Aborting connection.")
            self.instrument = None
            raise ConnectionError(f"Cannot reach keysight {self.name} with ip adress {self.keysight_ip}. Please check if the instrument is on")
        try:
            self.instrument = self.rm.open_resource(self.resource_string, timeout=self.timeout_ms)
            self.logger.info(f"Connected to Keysight device at {self.keysight_ip}")
        except Exception as e:
            self.logger.error(f"Error connecting to {self.resource_string}: {e}")
            self.instrument = None

    def _reconnect(self):
        """Re-establish the connection."""
        self.logger.info(f"Reconnecting to Keysight device.")
        self._connect()

    def write(self, message):
        """
        Write a command to the instrument.

        :param message: SCPI command to send.
        """
        if self.instrument is None:
            self._reconnect()
        try:
            self.logger.debug(f"Writing message to Keysight: {message}")
            self.instrument.write(message)
        except pyvisa.errors.VisaIOError as e:
            self.logger.error(f"Write error: {e}. Reconnecting...")
            self._reconnect()
            self.instrument.write(message)

    def read(self, message):
        """
        Send a command and read the response.

        :param message: SCPI command to send.
        :return: Response from the instrument.
        """
        if not self.instrument:
            self._reconnect()
        try:
            self.logger.debug(f"Reading message from Keysight: {message}")
            return self.instrument.query(message).strip()
        except pyvisa.errors.VisaIOError as e:
            self.logger.error(f"Read error: {e}. Reconnecting...")
            self._reconnect()
            return self.instrument.query(message).strip()

    def acquire(self, freq=50, verbose=False):
        """
        Acquire data from the instrument.

        Acquisition time is set by nplc and nsamples.
        """
        self.logger.info(f"Acquiring data for {self.t_acq:0.3f} sec.")
        self.write(':INIT:ACQ')

        if verbose: 
            print('acquisition time:', self.t_acq)
    
    def read_data(self, wait=False):
        """Read data from the instrument.
        :param wait: If True, wait for the acquisition to complete.
        :return: Data from the instrument.
        """
        if wait:
            self.logger.info(f"Waiting for acquisition to complete.")
            opc = int(self.read('*OPC?'))

        self.logger.info(f"Reading data from exposure.")        
        t = self.instrument.query_ascii_values(':FETC:ARR:TIME?')
        t = np.array(t, dtype=float)
        d = self.instrument.query_ascii_values(f':FETC:ARR:{self.params["mode"]}?')
        d = np.array(d, dtype=float)
        return np.rec.fromarrays([t, d], names=['time', self.params["mode"]])

    def get_acquisition_time(self, freq=50):
        """
        Calculate the acquisition time based on the number of samples and the interval.
        """
        self.logger.debug(f"Calculating acquisition time.")
        self.t_acq = float(self.params['nsamples']) * (float(self.params['nplc'])*1/freq + float(self.params['interval']))
        self.logger.info(f"Acquisition time defined to be {self.t_acq:0.3f} sec.")

    def get_power(self):
        self.logger.debug(f"Getting power from Keysight.")
        return int(self.read(':INP?').decode()[0])
    
    def get_device_info(self):
        self.logger.info(f"Getting device info from Keysight.")
        response = self.instrument.query("*IDN?").strip()
        print(f"Device Response: {response}")
        
        if response:
            details = response.split(',')
            model = details[1] if len(details) > 1 else "Unknown Model"
            serial_number = details[2] if len(details) > 2 else "Unknown Serial Number"
            print(f"Model: {model}")
            print(f"Serial Number: {serial_number}")
        else:
            self.logger.warning(f"No response received from the device.")

    def set_trigger_out(self):
        self.logger.info(f"Setting trigger output configuration.")
        self.write('TRIG:ACQ:TOUT 1')
        self.write('TRIG:ACQ:TOUT:SIGN TOUT')

    def set_mode(self, mode):
        self.logger.info(f"Setting mode to {mode}.")
        if mode not in ['CURR', 'CHAR', 'VOLT', 'RES']:
            raise ValueError("Invalid mode. Choose from 'CURR', 'CHAR', 'VOLT', 'RES'.")
        self.params["mode"] = mode
        self.write(f'SENSe:FUNCtion:ON "{mode}"')

    def set_rang(self, charge_range):
        self.logger.info(f"Setting range to {charge_range}.")
        self.params['rang'] = charge_range
        
        if charge_range == 'AUTO' :
            self.write(f'SENS:{self.params["mode"]}:RANG:AUTO ON')
        else :
            charge_range = float(charge_range)
            self.write(f'SENS:{self.params["mode"]}:RANG:AUTO OFF')
            self.write(f'SENS:{self.params["mode"]}:RANG {charge_range}')
    
    def set_nplc(self, nplc):
        self.logger.info(f"Setting NPLC to {nplc}.")
        self.params['nplc'] = nplc
        if nplc == 'AUTO' :
            self.write(f':SENS:{self.params["mode"]}:NPLC:AUTO ON')
        else:
            self.write(f':SENS:{self.params["mode"]}:NPLC:AUTO OFF')
            self.write(f':SENS:{self.params["mode"]}:NPLC {nplc}')
    
    def set_nsamples(self, nsamples=5500):
        self.logger.info(f"Setting number of samples to {nsamples}.")
        nsamples = int(nsamples)
        self.params['nsamples'] = nsamples
        self.write(f':TRIG:ACQ:COUN {nsamples}')
        self.params['nsamples'] = nsamples
    
    def set_delay(self, delay):
        self.logger.info(f"Setting delay to {delay}.")
        delay_time = float(delay)
        self.write(f':TRIG:ACQ:DEL {str(delay_time)}')
        self.write(f':TRIG:SOUR TIM')
        self.params['delay'] = delay
    
    def set_interval(self, interval):
        self.logger.info(f"Setting interval to {interval}.")
        interval = float(interval)
        self.write(f':TRIG:ACQ:TIM {interval}')
        self.params['interval'] = interval

    def get_params(self, verbose=False):
        self.logger.info(f"Getting current parameters from Keysight.")
        self.params = {
            'power': self.get_power(),
            "mode": self.get_mode(),
            'aper': self.get_aper(),
            'nplc': float(self.get_nplc()),
            'rang': self.get_rang(),
            'delay': self.get_delay(),
            'interval': self.get_interval(),
            'nsamples': int(self.get_nsamples())
        }

        if verbose:
            print('\nCurrent instrument parameters:')
            for param, value in self.params.items():
                print(f"{param}: {value}")
            print("")

    def set_acquisition_time(self, time, freq=50):
        self.logger.info(f"Setting acquisition time to {time} seconds.")
        nsamples = int(time / float(self.params['interval'])) + 1
        self.set_nsamples(nsamples)
        self.t_acq = time
        # print(f"Acquisition time set to {time:0.3f} sec with nsamples {self.params['nsamples']} and {self.params['nplc']}")

    def on(self):
        self.logger.info(f"Turning Keysight input ON.")
        self.write(':INP ON')

    def off(self):
        self.logger.info(f"Turning Keysight input OFF.")
        self.write(':INP OFF')

    def get_power(self):
        self.logger.info(f"Getting power reading from Keysight.")
        return int(self.read(':INP?'))

    def get_mode(self):
        self.logger.info(f"Getting current mode from Keysight.")
        res = str(self.read(f'SENS:FUNC?'))
        return res.strip('"')

    def get_aper(self):
        self.logger.info(f"Getting aperture setting from Keysight.")
        res = self.read(f'SENS:{self.params["mode"]}:APER?')
        return 

    def get_nplc(self):
        self.logger.info(f"Getting NPLC setting from Keysight.")
        return self.read(f'SENS:{self.params["mode"]}:NPLC?')

    def get_rang(self):
        self.logger.info(f"Getting range setting from Keysight.")
        return self.read(f'SENS:{self.params["mode"]}:RANG?')

    def get_delay(self):
        self.logger.info(f"Getting delay setting from Keysight.")
        return self.read(f'TRIG:ACQ:DEL?')

    def get_interval(self):
        self.logger.info(f"Getting interval setting from Keysight.")
        return self.read(':TRIG:ACQ:TIM?')

    def get_nsamples(self):
        self.logger.info(f"Getting number of samples setting from Keysight.")
        return int(self.read(':TRIG:ACQ:COUN?'))
    
    def get_powerline_freq(self):
        self.logger.info(f"Getting power line frequency setting from Keysight.")
        return float(self.read(':SYST:POWE:FREQ?'))

    def auto_scale(self, verbose=False, rang0=20e-4):
        self.logger.info(f"Starting auto scale with initial value {rang0}")
        self.set_acquisition_time(0.1)

        rang = rang0 # 20 microA
        for i in range(9):
            self.set_rang(rang)
            self.acquire()
            d = self.read_data()
            value = np.abs(np.mean(d[self.params['mode']]))
            self.logger.info(f"Range: {rang:e}, Value: {value:.2e}")

            if np.log10(np.abs(value))>15:
                # print("")
                # print(f"Optimal range is {rang*10:e}")
                self.set_rang(rang*100)
                self.logger.info(f"Range is set to {100*rang}")
                break
            else:
                rang /= 10
            
            if rang < 1e-15:
                self.logger.warning("Range is beyond the limit")
                break
    
        
if __name__ == "__main__":
    settings = {
                'mode': "CURR",
                'rang': 'AUTO',
                'nplc': 1.,
                'nsamples': 10,
                'delay': 0.,
                'interval': 2e-3,
                }
    
    keysight = KeysightController(name="K01", keysight_ip="169.254.5.2")
    # keysight = KeysightController(name="K02", keysight_ip="169.254.124.255")
    keysight.get_device_info()
    keysight.on()
    keysight.set_mode('CURR')
    keysight.acquire()
    d = keysight.read_data(wait=True)
    print(d)
    keysight.close()