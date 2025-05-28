import numpy as np
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
config_filename = os.path.join(script_dir, "../../default.yaml")

def _load_config(config_file):
    # Parse a config file (JSON, YAML, etc.) with device parameters
    import yaml
    # get current working directory
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

configDefault = _load_config(config_file=config_filename)

def get_config_section(section, config=configDefault):
    return config.get(section, {})

def get_config_value(section, key, default=None, config=configDefault):
    return config.get(section, {}).get(key, default)

def _initialize_logger(verbose=True):
    from pandora.utils.logger import initialize_central_logger
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
    # print("Shutter opened")
    shutter.get_device_info()

def close_shutter(args):
    """
    Close the shutter.

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

    # Close the shutter
    shutter.activate()
    # print("Shutter closed")
    shutter.get_device_info()

def set_wavelength(args):
    """
    Initializes only the monochromator controller 
    and sets it to the specified wavelength.

    Args:
        wavelength (float): The wavelength to set the monochromator to in nm.
        verbose (bool): Whether to print verbose output.
    """
    from pandora.controller.monochromator import MonochromatorController
    from pandora.states.flipmount_state import FlipMountState
    from pandora.states.labjack_handler import LabJack

    # Initialize the logger
    _initialize_logger(args.verbose)
    
    # Create an instance of the MonochromatorController
    mono_config = get_config_section('monochromator') 
    mono = MonochromatorController(**mono_config)

    # Create an instance of the flip order block filter
    labjack_ip = get_config_value('labjack', 'ip_address')
    labjack = LabJack(ip_address=labjack_ip)
    flip_cfg = get_config_value('labjack', 'flipOrderBlockFilter')
    flip2ndOrderFilter = FlipMountState(flip_cfg, labjack=labjack)

    # Set the monochromator to a new wavelength
    if args.wavelength>float(mono.wav_second_order_filter):
        # print(flip2ndOrderFilter.get_state())
        flip2ndOrderFilter.activate()
    else:
        flip2ndOrderFilter.deactivate()

    # Set to the specified wavelength
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
    #nrepeats = args.nrepeats

    # Initialize the logger
    _initialize_logger(verbose)

    # Create an instance of the KeysightController
    _kconfig = get_config_section('keysights')
    if name not in _kconfig.keys():
        print(f"List of available keysight devices: {_kconfig.keys()}")
        raise ValueError(f"Keysight device {name} not found in config file.")

    kconfig = get_config_section(name, config=_kconfig)
    keysight = KeysightController(**kconfig)

    # Make sure keysight is on
    keysight.on()   

    # Finding the optimal scale
    if rang0 is not None:
        keysight.set_rang(rang0)

    # Auto scale the keysight;
    # override the rang0 if autoRange is True    
    if args.autoRange:
        keysight.auto_scale(verbose=verbose)

    # Get the readout from the Keysight multimeter
    # Set the NPLC and the integration time
    keysight.set_nplc(nplc)
    keysight.set_acquisition_time(exptime)

    # Get the readout
    keysight.acquire()
    d = keysight.read_data(wait=True)

    print(f"Readout stats from {name}: {d['CURR'].mean():0.2g} +/- {d['CURR'].std():0.2g} A")
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

def flip(args):
    """
    Change the flipmounts states
    """
    # Flip Mounts
    flipDict = {
        "spec-mount": "flipSpecMount",
        "order-block-filter": "flipOrderBlockFilter",
        "od2-first": "flipOD2First",
        "od2-second": "flipOD2Second",
        "pd2": "flipPD2",
        "pd3": "flipPD3",
        "quarter-wave-plate": "flipQuarterWavePlate"
    }
    if args.listNames:
        print("Available flip mounts:")
        namesList = list(flipDict.keys())
        print(", ".join(namesList))
        return
    
    from pandora.states.flipmount_state import FlipMountState
    from pandora.states.labjack_handler import LabJack
    name = args.name
    is_on = args.on
    is_off = args.off
    is_state = args.state
    
    # Initialize the logger
    logger = _initialize_logger(args.verbose)

    if name not in flipDict.keys():
        logger.error(f"Flip mount {name} not found in flipDict")
        raise ValueError(f"Flip mount {name} not found in flipDict, run pb flip --listNames to see the available flip mounts")

    # Port names for each subsystem
    _lbjack_config = get_config_section('labjack')

    labjack_ip = get_config_value('labjack', 'ip_address')
    fport = get_config_value('labjack', flipDict[name])
    flogic = get_config_value('labjack', flipDict[name]+'InvertLogic')

    # Initialize the LabJack connection
    labjack = LabJack(ip_address=labjack_ip)

    # Initialize the flip mount
    flipper = FlipMountState(fport, labjack=labjack, invert_logic=flogic)

    # Set the flip mount to the desired state
    if is_on:
        flipper.activate()
        print(f"Flip mount {name} is now {flipper.state.value}")
    elif is_off:
        flipper.deactivate()
        print(f"Flip mount {name} is now {flipper.state.value}")
    else:
        flipper.get_state()
        print(f"Flip mount {name} is {flipper.state.value}")
    pass

#!/usr/bin/env python3
import sys

def zaber(args):
    ZMAP = {
        "nd-filter": "Z1",
        "pinhole-mask": "Z3",
        "focusing": "Z2"
    }

    # Option 1: List Zaber controller names
    if args.listZaberNames:
        print("Listing available Zaber controller names:")
        # Insert logic to query and print controller names, e.g.:
        print("nd-filter\n" + "pinhole-mask\n"+"focusing\n")
        return

    # For other options, the controller name must be provided
    if not args.controller:
        print("Error: A zaber controller name must be provided unless using --listZaberNames.")
        sys.exit(1)

    from pandora.controller.zaberstages import ZaberController
    # Initialize the logger
    logger = _initialize_logger(args.verbose)
    controller_name = args.controller

    if controller_name not in ZMAP.keys():
        logger.error(f"Zaber controller '{controller_name}' not found in ZMAP.\n Available controllers: {list(ZMAP.keys())}")
        sys.exit(1)

    zcode = ZMAP[controller_name] 

    logger.info(f"Initializing Zaber controller {controller_name}...")
    zb_config = get_config_section('zaber_stages', config=configDefault)
    zconfig = get_config_section(zcode, config=zb_config)
    zaber = ZaberController(**zconfig)

    # Get the slot map for the specified controller
    slot_dict = zconfig['slot_map']

    # Option 2: List the slot table for the given controller
    if args.listSlotTable:
        print(f"Listing slot table for controller '{args.controller}':")
        print(10*'---')
        print(f'Slot Map for {controller_name}:')
        print('Slot home: 0.00 mm')
        for slot_name, position in slot_dict.items():
            print(f"Slot {slot_name}: {position:.2f} mm")
        return

    # Option 2: Get the current position
    if args.getPosition:
        current_position = zaber.get_position_mm()    
        print(f"Current position of controller {args.controller}: {current_position:.2f} mm")
        # match the slot name if it exists
        for slot_name, position in slot_dict.items():
            if abs(current_position - position) < 0.01:
                print(f"Current position matches slot '{slot_name}' at {position:.2f} mm")
        return
    
    # Option 3: Move to a given position in mm (if --move flag is used)
    if args.move is not None:
        print(f"Moving controller '{args.controller}' to position {args.move} mm...")
        # Insert code to move to the specified position
        current_position = zaber.get_position_mm()    
        zaber.move_zaber_axis(args.move-current_position)  # Move relative to current position
        new_position = zaber.get_position_mm()
        print(f"Moved to new position: {new_position:.2f} mm")
        return
    
    # Option 5:  move to home position
    if args.slot=="home":
        print(f"Moving controller {args.controller} to home position...")
        zaber.go_home()
        return
    
    # Option 4: If no flag is given but a slot name is provided, move to that slot
    if args.slot:
        print(f"Moving controller {args.controller} to slot '{args.slot}'...")
        # Insert code to move to the specified slot
        zaber.move_to_slot(args.slot.upper())  # Ensure slot name is uppercase
    else:
        print("Error: You must specify a slot name or use --move or --listSlotTable.")
        sys.exit(1)
