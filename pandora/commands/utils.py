config_file_path = '../../default.yaml'

def get_config_section(section):
    import yaml
    # Load the configuration file
    with open(config_file_path, 'r') as file:
        config = yaml.safe_load(file)

    # Extract the specified section
    section_config = config.get(section, {})
    return section_config

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
    # Initialize the logger
    _initialize_logger(args.verbose)
    
    # Create an instance of the ShutterController
    shutter_config = get_config_section('shutter')
    shutter = ShutterState(**shutter_config)

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
    # Initialize the logger
    _initialize_logger(args.verbose)
    
    # Create an instance of the ShutterController
    shutter_config = get_config_section('shutter')
    shutter = ShutterState(**shutter_config)

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
    mono.get_wavelength(sleep=0.5)

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