import numpy as np
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
config_file_path = os.path.join(script_dir, "../../default.yaml")


def get_config_section(section):
    import yaml
    # Load the configuration file
    with open(config_file_path, 'r') as file:
        config = yaml.safe_load(file)

    # Extract the specified section
    section_config = config.get(section, {})
    return section_config

def get_config_value(section, key):
    section_config = get_config_section(section)
    return section_config.get(key, None)

def _initialize_logger(verbose=True):
    from pandora.utils.logger import initialize_central_logger
    import os
    print(os.getcwd())
    # Setup and return a logger instance for the Pandora class
    logging_config = get_config_section('logging')
    logger = initialize_central_logger(logging_config['logfile'], logging_config['level'], verbose)
    return logger

def open_shutter(args):
    """
    Opens the shutter.

    Args:
        verbose (bool): Whether to print verbose output.
    """
    from pandora.states.shutter_state import ShutterState
    from pandora.states.labjack_handler import LabJack

    # Initialize the logger
    _initialize_logger(args.verbose)
    
    # Create an instance of the ShutterController
    labjack_ip = get_config_value('labjack', 'ip_address')
    labjack = LabJack(ip_address=labjack_ip)
    shutter_port = get_config_value('labjack', 'flipShutter')
    shutter = ShutterState(shutter_port,labjack=labjack)

    # Open the shutter
    shutter.deactivate()
    print("Shutter opened")

def close_shutter(args):
    """
    Close the shutter.

    Args:
        verbose (bool): Whether to print verbose output.
    """
    from pandora.states.shutter_state import ShutterState
    from states.labjack_handler import LabJack
    
    # Initialize the logger
    _initialize_logger(args.verbose)
    
    # Create an instance of the ShutterController
    labjack_ip = get_config_value('labjack', 'ip_address')
    labjack = LabJack(ip_address=labjack_ip)
    shutter_port = get_config_value('labjack', 'flipShutter')
    shutter = ShutterState(shutter_port,labjack=labjack)

    # Open the shutter
    shutter.activate()
    print("Shutter closed")

def set_wavelength(args):
    """
    Initializes only the monochromator controller 
    and sets it to the specified wavelength.

    Args:
        wavelength (float): The wavelength to set the monochromator to in nm.
        verbose (bool): Whether to print verbose output.
    """
    from pandora.controller.monochromator import MonochromatorController
    # Initialize the logger
    _initialize_logger(args.verbose)
    
    # Create an instance of the MonochromatorController
    mono_config = get_config_section('monochromator')
    mono = MonochromatorController(**mono_config)

    # Set the monochromator to a new wavelength
    mono.move_to_wavelength(args.wavelength)

    # Get the current wavelength
    mono.get_wavelength()

    print(f"Monochromator set to {mono.wavelength:0.2f} nm")


def get_wavelength(args):
    """
    Initializes only the monochromator controller 
    and get the current wavelength.
    """
    from pandora.controller.monochromator import MonochromatorController
    # Initialize the logger
    _initialize_logger(False)
    
    # Create an instance of the MonochromatorController
    mono_config = get_config_section('monochromator')
    mono = MonochromatorController(**mono_config)

    # Set the monochromator to a new wavelength
    mono.get_wavelength(sleep=0.5)

    print(f"Current wavelentgh is {mono.wavelength:0.2f} nm")

def get_configuration_file(args):
    """
    Get the configuration file path.
    """
    print(f"Configuration file is {config_file_path}")

def get_keysight_readout(args):
    """
    Get the readout from the Keysight multimeter.
    """
    from pandora.controller.keysight import KeysightController
    name = args.name
    nplc = args.nplc
    exptime = args.exptime
    verbose = args.verbose
    rang0 = args.rang0

    # Initialize the logger
    _initialize_logger(verbose)

    # Create an instance of the KeysightController
    _kconfig = get_config_section('keysight')
    kconfig = get_config_section(name, config=_kconfig)
    keysight = KeysightController(**kconfig)

    # Make sure keysight is on
    keysight.on()   

    # Finding the optimal scale
    if rang0 is not None:
        keysight.auto_scale(verbose=verbose,rang0=rang0)

    # Get the readout from the Keysight multimeter
    # Set the NPLC and the integration time
    keysight.set_nplc(nplc)
    keysight.set_acquisition_time(exptime)

    # Get the readout
    keysight.acquire()
    d = keysight.read_data(wait=True)

    print(f"Readout stats from {name}: {d.mean():0.2f} +/- {d.std():0.2f} A")
    # print(f"Readout from {name}: {d}")
    pass

def get_spectrometer_readout(args):
    """
    Get the spectrometer readout.
    """
    from pandora.controller.stellarnet import spectrometerController
    epxtime = args.exptime
    scanavg = args.scanavg
    xtiming = args.xtiming
    is_plot = args.is_plot

    # Initialize the logger
    _initialize_logger(args.verbose)
    
    # Create an instance of the SpectrometerController
    # spec_config = get_config_section('spectrometer')
    spectrometer = spectrometerController()

    # Set up the spectrometer
    spectrometer.set_scan_avg(scanavg)
    spectrometer.set_xtiming(xtiming)
    spectrometer.set_integration_time(epxtime)

    # Get the spectrometer data
    wav, counts = spectrometer.get_spectrum()

    # print(f"Spectrometer stats: {wav.mean():0.2f} +/- {wav.std():0.2f} nm")
    print(f"Spectrometer stats counts (mean/std): {counts.mean():0.2f} / {counts.std():0.2f} counts")
    print(f"                   counts (max/min): {counts.max():0.2f} / {counts.min():0.2f} counts")
    print(f"                   wav nm (max    ): {counts[np.argmax(counts)]:0.2f}")
    
    if is_plot:
        spectrometer.plot_spectrum(wav, counts)

    pass