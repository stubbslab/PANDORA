import logging
import pyvisa
import numpy as np
import time

from pandora.utils.socket_helper import is_port_open

FREQ = 60 # hz

# Available charge ranges for B2985B/B2987B electrometers (coulomb meter mode)
CHARGE_RANGES = [
    2e-9,   # 2 nC  (resolution: 1 fC)
    2e-8,   # 20 nC (resolution: 10 fC)
    2e-7,   # 200 nC (resolution: 100 fC)
    2e-6,   # 2 µC  (resolution: 1 pC)
]

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
        self.tracked_properties = ['mode', 'nplc', 'rang', 'delay', 'nsamples']
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

    def acquire(self, verbose=False):
        """
        Acquire data from the instrument.

        Acquisition time is set by nplc and nsamples.
        """
        self.logger.info(f"Acquiring data for {self.t_acq:0.3f} sec.")
        self.write(':INIT:ACQ')

        if verbose:
            print('acquisition time:', self.t_acq)

    def discharge(self):
        """
        Zero the feedback capacitor before a new charge measurement.

        Only applicable in CHAR (charge) mode on B2985B/B2987B electrometers.
        This resets the integrating capacitor to start a fresh charge accumulation.
        """
        self.logger.info("Discharging feedback capacitor.")
        self.write('SENS:CHAR:DISCharge')

    def set_auto_discharge(self, enabled=True, level=None):
        """
        Configure automatic discharge to prevent range overflow.

        When enabled, the instrument automatically resets the integrator
        when accumulated charge reaches the threshold level.

        Args:
            enabled (bool): Enable or disable auto-discharge.
            level (float, optional): Threshold in Coulombs.
                Valid values: 2e-9, 2e-8, 2e-7, 2e-6 (2nC to 2µC).
        """
        state = 'ON' if enabled else 'OFF'
        self.logger.info(f"Setting auto-discharge to {state}.")
        self.write(f'SENS:CHAR:DISCharge:AUTO {state}')
        if level is not None:
            self.logger.info(f"Setting auto-discharge level to {level}.")
            self.write(f'SENS:CHAR:DISCharge:LEVel {level}')

    def acquire_charge(self, discharge_first=True, verbose=False):
        """
        Acquire charge data, optionally discharging the capacitor first.

        This is a convenience wrapper for charge measurements that ensures
        the feedback capacitor is zeroed before starting acquisition.

        Args:
            discharge_first (bool): If True, discharge capacitor before acquiring.
            verbose (bool): If True, print acquisition time.
        """
        if discharge_first:
            self.discharge()
            time.sleep(0.05)  # brief settling time after discharge
        self.acquire(verbose=verbose)

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

    def get_acquisition_time(self):
        """
        Calculate the acquisition time based on the number of samples and the interval.
        """
        self.logger.debug(f"Calculating acquisition time.")
        self.t_acq = float(self.params['nsamples']) * float(self.params['interval'])
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

    def set_rang(self, rang):
        self.logger.info(f"Setting range to {rang}.")
        self.params['rang'] = rang

        if rang == 'AUTO':
            self.write(f'SENS:{self.params["mode"]}:RANG:AUTO ON')
        else:
            rang = float(rang)
            self.write(f'SENS:{self.params["mode"]}:RANG:AUTO OFF')
            self.write(f'SENS:{self.params["mode"]}:RANG {rang}')
            # Settling time only applies to current mode (RC time constants)
            # Charge mode uses feedback capacitor with different characteristics
            if self.params.get('mode') == 'CURR':
                wait_for_settle(rang, margin=1.01)
    
    def set_nplc(self, nplc):
        self.logger.info(f"Setting NPLC to {nplc}.")
        self.params['nplc'] = nplc
        if nplc == 'AUTO' :
            self.write(f':SENS:{self.params["mode"]}:NPLC:AUTO ON')
        else:
            self.write(f':SENS:{self.params["mode"]}:NPLC:AUTO OFF')
            self.write(f':SENS:{self.params["mode"]}:NPLC {nplc}')
            self.set_interval_to_nplc(nplc)

    def set_interval_to_nplc(self, nplc, overhead_time=1e-3):
        """make sure the interval is greater or equal of the nplc
        """
        self.set_interval(nplc/FREQ+overhead_time)
    
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

    def set_acquisition_time(self, time):
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

    def auto_scale(self, rang0=2e-5):
        """
        Conservative auto-scale for smooth wavelength scans.
        Favors ranging up early to prevent overflows.
        """
        # Actual available current ranges for B2980B (2-20-200 pattern)
        AVAILABLE_RANGES = [
            2e-12,  # 2 pA
            2e-11,  # 20 pA  
            2e-10,  # 200 pA
            2e-9,   # 2 nA
            2e-8,   # 20 nA
            2e-7,   # 200 nA
            2e-6,   # 2 μA
            2e-5,   # 20 μA
            2e-4,   # 200 μA
            2e-3,   # 2 mA
        ]
        
        self.logger.info(f"Starting auto scale with initial value {rang0}")
        self.set_acquisition_time(10/FREQ)
        
        # Start at 2e-5 (20 μA) range by default
        try:
            rang_idx = AVAILABLE_RANGES.index(rang0)
        except ValueError:
            # If rang0 not in list, default to 2e-5 (20 μA)
            rang_idx = AVAILABLE_RANGES.index(2e-5)
            self.logger.info(f"Starting range {rang0} not available, defaulting to 2e-5")
        
        # Maximum iterations to prevent infinite loop
        for iteration in range(15):
            rang = AVAILABLE_RANGES[rang_idx]
            self.set_rang(rang)
            self.acquire()
            d = self.read_data()
            value = np.abs(np.mean(d[self.params['mode']]))
            self.logger.info(f"Range: {rang:e}, Value: {value:.2e}")
            
            # Conservative thresholds:
            # - Range UP at 80% to prevent overflow
            # - Range DOWN below 5% to avoid oscillation
            
            if value > 0.80 * rang:
                # Value approaching limit, go to less sensitive range
                if rang_idx < len(AVAILABLE_RANGES) - 1:
                    rang_idx += 1
                    continue
                else:
                    self.logger.warning("Signal approaching maximum range")
                    break
                    
            elif value < 0.05 * rang:
                # Value too small, go to more sensitive range
                if rang_idx > 0:
                    rang_idx -= 1
                    continue
                else:
                    self.logger.info("At minimum range")
                    break
            else:
                # Value is within safe zone (5% to 80%)
                self.logger.info(f"Optimal range found: {rang:e}")
                break
        
        # Ensure we're set to the final determined range
        self.set_rang(AVAILABLE_RANGES[rang_idx])
        return AVAILABLE_RANGES[rang_idx]

    def auto_scale_charge(self, rang0=2e-8):
        """
        Conservative auto-scale for charge mode wavelength scans.
        Similar to auto_scale() but uses charge ranges (2nC to 2µC).

        Only works on B2985B/B2987B electrometers in CHAR mode.

        Args:
            rang0 (float): Initial range to start scaling from.
                Default is 2e-8 (20 nC).

        Returns:
            float: The optimal charge range found.
        """
        if self.params.get('mode') != 'CHAR':
            self.logger.warning("auto_scale_charge called but mode is not CHAR. Switching to CHAR mode.")
            self.set_mode('CHAR')

        self.logger.info(f"Starting charge auto-scale with initial range {rang0}")
        self.set_acquisition_time(10/FREQ)

        # Start at specified range or default to 20 nC
        try:
            rang_idx = CHARGE_RANGES.index(rang0)
        except ValueError:
            rang_idx = CHARGE_RANGES.index(2e-8)
            self.logger.info(f"Starting range {rang0} not available, defaulting to 2e-8 (20 nC)")

        # Maximum iterations to prevent infinite loop
        for iteration in range(10):
            rang = CHARGE_RANGES[rang_idx]
            self.set_rang(rang)
            self.discharge()  # Zero capacitor before test measurement
            time.sleep(0.05)
            self.acquire()
            d = self.read_data(wait=True)
            value = np.abs(np.mean(d[self.params['mode']]))
            self.logger.info(f"Charge range: {rang:e}, Value: {value:.2e}")

            # Conservative thresholds:
            # - Range UP at 80% to prevent overflow
            # - Range DOWN below 5% to avoid oscillation

            if value > 0.80 * rang:
                # Value approaching limit, go to less sensitive range
                if rang_idx < len(CHARGE_RANGES) - 1:
                    rang_idx += 1
                    continue
                else:
                    self.logger.warning("Charge signal approaching maximum range (2 µC)")
                    break

            elif value < 0.05 * rang:
                # Value too small, go to more sensitive range
                if rang_idx > 0:
                    rang_idx -= 1
                    continue
                else:
                    self.logger.info("At minimum charge range (2 nC)")
                    break
            else:
                # Value is within safe zone (5% to 80%)
                self.logger.info(f"Optimal charge range found: {rang:e}")
                break

        # Ensure we're set to the final determined range
        self.set_rang(CHARGE_RANGES[rang_idx])
        return CHARGE_RANGES[rang_idx]


# factory numbers (seconds) – keys are the nominal range limits
_EXP_SETTLING = {
    -12: 16.0,       #  2 pA range
    -11: 1.4,        # 20 pA
    -10: 1.4,        # 200 pA
     -9: 0.013,      #   2 nA / 20 nA
     -8: 0.013,      #  20 nA (same decade)
     -7: 0.0012,     # 200 nA
     -6: 0.00055,    #   2 µA
     -5: 0.00060,    #  20 µA
     -4: 0.00060,    # 200 µA
     -3: 0.00010,    #   2 mA
}

def wait_for_settle(current_range, margin=1.01):
    """
    Pause long enough for the B2983A to settle after you switch to *current_range*.

    Parameters
    ----------
    current_range : float
        The full-scale range you just selected, in amperes.
    margin : float, optional
        Multiplicative safety factor (>1 stretches the wait).

    Raises
    ------
    KeyError
        If the range isn’t in the spec table.
    """
    rang_power = int(np.log10(current_range))-1
    try:
        delay = _EXP_SETTLING[rang_power] * margin
    except KeyError as exc:
        raise KeyError(f"Range {current_range} A not in spec table") from exc
    # print(f"Delay time {delay}, {current_range}, {rang_power}")
    time.sleep(delay)

        
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