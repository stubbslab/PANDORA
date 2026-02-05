import argparse
# from measure_solar_cell_qe import measureSolarCellQE
from measure_pandora_throughput import measurePandoraThroughput, measurePandoraThroughputBeta
# "final" (overflow-safe) throughput routine
try:
    from measure_pandora_throughput_2 import measurePandoraTputFinal
except ImportError:
    # fallback if the function was added to the original module
    from measure_pandora_throughput import measurePandoraTputFinal  # type: ignore
# charge measurement (coulomb meter mode)
from measure_pandora_charge import measurePandoraCharge
# from measure_nd_transmission import measureNDTransmission
# from expose import exposeFocalPlane
# from spectrograph_calib import spectrographCalib
# from monochromator_calib import monochromatorCalib

from utils import set_wavelength, get_wavelength
from utils import open_shutter, close_shutter
from utils import get_keysight_readout
from utils import get_spectrometer_readout
from utils import flip
from utils import zaber
from utils import (
    mount_status, mount_goto, mount_home, mount_park, mount_unpark,
    mount_stop, mount_set_park, mount_get_position,
    mount_set_alt_limit, mount_get_alt_limit
)
from keysight_continous_readout import start_acquisition, stop_acquisition

"""Main function to handle command-line arguments and dispatch to the appropriate function.

alias pb='python -p pandora/commands/pb.py'

pb --help
pb measure-solar-cell-qe --help
pb measure-solar-cell-qe --lambda0 300 --lambdaEnd 800 --step 10 --repeats 5
pb measure-pandora-throughput --lambda0 300 --lambdaEnd 700 --step 10 --nrepeats
pb measure-nd-transmission --lambda0 400 --lambdaEnd 700 --filters ND05,ND10,ND15,ND20 --step 10 --nrepeats 5
pb set-wavelength 500 --verbose
pb get-wavelength
pb open-shutter
pb close-shutter

"""

def main():
    parser = argparse.ArgumentParser(
        description="PandoraBox Command-Line Interface (commands)",
        epilog="Use `pb <command> --help` for more details on each command."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # # command: measure-solar-cell-qe
    # sc_qe_parser = subparsers.add_parser(
    #     "measure-solar-cell-qe", 
    #     help="Measure the solar cell QE (ratio vs. wavelength)."
    # )
    # sc_qe_parser.add_argument("--lambda0", type=float, default=300.0, help="Start wavelength (nm).")
    # sc_qe_parser.add_argument("--lambdaEnd", type=float, default=800.0, help="End wavelength (nm).")
    # sc_qe_parser.add_argument("--step", type=float, default=10.0, help="Wavelength step (nm).")
    # sc_qe_parser.add_argument("--repeats", type=int, default=5, help="Number of repeats per measurement point.")
    # sc_qe_parser.set_defaults(func=measureSolarCellQE)

    # command: measure-pandora-throughput
    pt_parser = subparsers.add_parser(
        "measure-pandora-throughput",
        help="Measure throughput linking main beam flux to monitor diode flux."
    )
    pt_parser.add_argument("exptime", type=float, help="Exposure time (s).")
    pt_parser.add_argument("lambda0", type=float, help="Start wavelength (nm).")
    pt_parser.add_argument("lambdaEnd", type=float, help="End wavelength (nm).")
    pt_parser.add_argument("--step", type=float, default=1, help="Wavelength step (nm).")
    pt_parser.add_argument("--ndFilter", type=str, default="CLEAR", help="ND filter to use on zaber stage (e.g., ND05, ND10, ND15, ND20, CLEAR).")
    # pt_parser.add_argument("--pinholeMask", type=str, default="CLEAR", help="pinhole mask name to use on zaber stage (e.g., P200UM, P100UM, CLEAR).")
    pt_parser.add_argument("--nrepeats", type=int, default=5, help="Number of repeats per measurement point.")
    pt_parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    # pt_parser.add_argument("--maskPorts", action="store_true", 
    #                        help="Whether to mask 2 of the 3 output ports.")
    pt_parser.set_defaults(func=measurePandoraThroughput)

    # command: measure-pandora-throughput
    pt_parser_beta = subparsers.add_parser(
        "measure-pandora-throughput-beta",
        help="Measure throughput linking main beam flux to monitor diode flux."
    )
    pt_parser_beta.add_argument("exptime", type=float, help="Exposure time (s).")
    pt_parser_beta.add_argument("lambda0", type=float, help="Start wavelength (nm).")
    pt_parser_beta.add_argument("lambdaEnd", type=float, help="End wavelength (nm).")
    pt_parser_beta.add_argument("--step", type=float, default=1, help="Wavelength step (nm).")
    pt_parser_beta.add_argument("--ndFilter", type=str, default="CLEAR", help="ND filter to use on zaber stage (e.g., ND05, ND10, ND15, ND20, CLEAR).")
    # pt_parser_beta.add_argument("--pinholeMask", type=str, default="CLEAR", help="pinhole mask name to use on zaber stage (e.g., P200UM, P100UM, CLEAR).")
    pt_parser_beta.add_argument("--nrepeats", type=int, default=100, help="Number of repeats per measurement point.")
    pt_parser_beta.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    pt_parser_beta.add_argument("--darktime", type=float, default=None, help="Dark time between measurements (s).")
    pt_parser_beta.add_argument("--flip", type=str, default=None, help="Name of the flip mount to activate before measurement (e.g., flipPD2).")
    # pt_parser_beta.add_argument("--maskPorts", action="store_true", 
    #                        help="Whether to mask 2 of the 3 output ports.")
    pt_parser_beta.set_defaults(func=measurePandoraThroughputBeta)

    # command: measure-pandora-tput-final (overflow-aware, dark-after-range-change)
    pt_parser_final = subparsers.add_parser(
        "measure-pandora-tput-final",
        help="Throughput scan with automatic overflow handling: dark-before/after range change, repeat failed light blocks."
    )
    pt_parser_final.add_argument("exptime", type=float, help="Light block exposure time (s).")
    pt_parser_final.add_argument("lambda0", type=float, help="Start wavelength (nm).")
    pt_parser_final.add_argument("lambdaEnd", type=float, help="End wavelength (nm).")
    pt_parser_final.add_argument("--step", type=float, default=1, help="Wavelength step (nm).")
    pt_parser_final.add_argument("--ndFilter", type=str, default="CLEAR", help="ND filter on Zaber stage (e.g. ND05, ND10, ND15, ND20, CLEAR).")
    pt_parser_final.add_argument("--nrepeats", type=int, default=100, help="Repeats per wavelength (successful light blocks only are counted).")
    pt_parser_final.add_argument("--darktime", type=float, default=None, help="Dark block time (s). If None, use exptime.")
    pt_parser_final.add_argument("--verbose", action="store_true", help="Verbose logging.")
    pt_parser_final.set_defaults(func=measurePandoraTputFinal)

    # command: measure-pandora-charge (coulomb meter mode)
    charge_parser = subparsers.add_parser(
        "measure-pandora-charge",
        help="Measure accumulated charge vs wavelength using the B2985B/B2987B electrometer in coulomb meter mode."
    )
    charge_parser.add_argument("exptime", type=float,
        help="Integration time per measurement (s).")
    charge_parser.add_argument("lambda0", type=float,
        help="Start wavelength (nm).")
    charge_parser.add_argument("lambdaEnd", type=float,
        help="End wavelength (nm).")
    charge_parser.add_argument("--step", type=float, default=1,
        help="Wavelength step (nm).")
    charge_parser.add_argument("--nrepeats", type=int, default=100,
        help="Number of repeats per wavelength.")
    charge_parser.add_argument("--darktime", type=float, default=None,
        help="Dark exposure time (s). Defaults to exptime if not specified.")
    charge_parser.add_argument("--discharge", action="store_true", default=True,
        help="Discharge capacitor before each acquisition (default: enabled).")
    charge_parser.add_argument("--no-discharge", dest="discharge", action="store_false",
        help="Skip discharge for continuous charge accumulation.")
    charge_parser.add_argument("--verbose", action="store_true",
        help="Enable verbose output.")
    charge_parser.set_defaults(func=measurePandoraCharge)

    # # command: measure-nd-transmission
    # nd_parser = subparsers.add_parser(
    #     "measure-nd-transmission",
    #     help="Measure wavelength-dependent transmission of ND filters."
    # )
    # nd_parser.add_argument("--lambda0", type=float, default=400.0, help="Start wavelength (nm).")
    # nd_parser.add_argument("--lambdaEnd", type=float, default=700.0, help="End wavelength (nm).")
    # nd_parser.add_argument("--filters", type=str, default="ND05,ND10,ND15,ND20", help="Comma-separated ND filters (e.g., ND1,ND2).")
    # pt_parser.add_argument("--step", type=float, default=10.0, help="Wavelength step (nm).")
    # pt_parser.add_argument("--nrepeats", type=int, default=5, help="Number of repeats per measurement point.")    
    # nd_parser.set_defaults(func=measureNDTransmission)

    # command: set-wavelength
    set_wavelength_parser = subparsers.add_parser(
        "set-wavelength",
        help="Set the monochromator to a specific wavelength."
    )
    set_wavelength_parser.add_argument("wavelength", type=float, help="Wavelength to set (nm).")
    set_wavelength_parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    set_wavelength_parser.set_defaults(func=set_wavelength)

    # command: get-wavelength
    get_wavelength_parser = subparsers.add_parser(
        "get-wavelength",
        help="Get the current wavelength of the monochromator."
    )
    get_wavelength_parser.set_defaults(func=get_wavelength)
    
    # command: open-shutter
    open_shutter_parser = subparsers.add_parser(
        "open-shutter",
        help="Open the shutter."
    )
    open_shutter_parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    open_shutter_parser.set_defaults(func=open_shutter)

    # command: close-shutter
    close_shutter_parser = subparsers.add_parser(
        "close-shutter",
        help="Close the shutter."
    )
    close_shutter_parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    close_shutter_parser.set_defaults(func=close_shutter)

    # command: get-keysight-readout
    keysight_readout_parser = subparsers.add_parser(
        "get-keysight-readout",
        help="Get the readout from the Keysight electrometer."
    )
    keysight_readout_parser.add_argument("exptime", type=float, help="Exposure time.")
    keysight_readout_parser.add_argument("--name", type=str, default="K1", help="Name of the keysight device (K1 or K2).")
    keysight_readout_parser.add_argument("--nplc", type=int, default=10, help="Number of power line cycles.")
    keysight_readout_parser.add_argument("--rang0", type=float, default=None, help="If not none, set auto range with initial range.")
    keysight_readout_parser.add_argument("--autoRange", action="store_true", help="Enable verbose output.")
    keysight_readout_parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    keysight_readout_parser.add_argument("--printAll", action="store_true", help="Print all points in the exptime")
    keysight_readout_parser.set_defaults(func=get_keysight_readout)

    spectrometer_readout_parser = subparsers.add_parser(
        "get-spectrometer-readout",
        help="Get the readout from the StellarNet spectrometer."
    )
    spectrometer_readout_parser.add_argument("exptime", type=int, help="Exposure time in ms.")
    spectrometer_readout_parser.add_argument("--scanavg", type=int, default=10, help="Number of scans to average.")
    spectrometer_readout_parser.add_argument("--xtiming", type=int, default=3, help="Spectrometer resolution modes, 1, 2 or 3.")
    spectrometer_readout_parser.add_argument("--is_plot", action="store_true", default=False, help="Enable plotting.")
    spectrometer_readout_parser.add_argument("--verbose", action="store_true", default=True, help="Enable verbose output.")
    spectrometer_readout_parser.set_defaults(func=get_spectrometer_readout)
    
    flipper_parser = subparsers.add_parser(
        "flip",
        help="Control flip mounts (on/off/state, or list mount names)."
    )

    # inside your pb.py’s main():
    kc_parser = subparsers.add_parser(
        "run-keysight",
        help="Run continuously the Keysight B2980A control script",
        description="Keysight B2980A control script"
    )
    kc_parser.add_argument(
        "--name", default="K1",
        help="Name of the electrometer (for config file)"
    )
    kc_subparsers = kc_parser.add_subparsers(
        dest="kc_action", required=True,
        help="start or stop continuous acquisition"
    )
    sp_start = kc_subparsers.add_parser(
        "start", help="Start continuous acquisition"
    )
    sp_start.add_argument(
        "--points", type=int, default=100000,
        help="Number of trace buffer points (max 100000)"
    )
    sp_start.add_argument(
        "--nplc", type=int, default=10,
        help="Number of power line cycles per measurement"
    )
    sp_start.add_argument(
        "--rang0", type=float, default=2e-9,
        help="If not None, set initial current range (A)"
    )
    # sp_start.add_argument(
    #     "--autoRange", action="store_true",
    #     help="Enable auto current range"
    # )
    sp_start.set_defaults(func=start_acquisition)

    sp_stop = kc_subparsers.add_parser(
        "stop", help="Stop acquisition and save data"
    )
    sp_stop.set_defaults(func=stop_acquisition)


    # Make 'name' optional, so users can do `pb flip --listNames` with no name
    flipper_parser.add_argument(
        "name",
        nargs="?",
        help="Name of the flip mount to control (e.g., pd2, fm1)."
    )
    # Mutually exclusive group for setting or checking state
    flip_group = flipper_parser.add_mutually_exclusive_group()
    flip_group.add_argument("--on", action="store_true", help="Activate the flip mount.")
    flip_group.add_argument("--off", action="store_true", help="Deactivate the flip mount.")
    flip_group.add_argument("--state", action="store_true", help="Show the current flip mount state.")

    # Option to list all known flip mounts
    flipper_parser.add_argument("--listNames", action="store_true", help="List all flip mount names.")
    flipper_parser.add_argument("--verbose", action="store_true", default=False, help="Enable verbose output.")

    # Hook up the handler function
    flipper_parser.set_defaults(func=flip)

    # command: zaber
    # Define the "zaber" subcommand
    zaber_parser = subparsers.add_parser(
        "zaber",
        help="Control Zaber stages."
    )
    # Positional argument: controller name (optional if using --listZaberNames)
    zaber_parser.add_argument(
        "controller",
        nargs="?",
        help="Name of the Zaber controller (e.g., nd-filters, pinhole, focus)."
    )
    # Optional positional argument for slot name (only used if no other flag is specified)
    zaber_parser.add_argument(
        "slot",
        nargs="?",
        help="Slot name to move to (if not using --move)."
    )
    # Optional flags
    zaber_parser.add_argument(
        "--listZaberNames",
        action="store_true",
        help="List all Zaber controller names."
    )
    zaber_parser.add_argument(
        "--listSlotTable",
        action="store_true",
        help="List the slot table for the specified Zaber controller."
    )
    zaber_parser.add_argument(
        "--move",
        type=float,
        help="Move the controller to a given position in mm."
    )
    zaber_parser.add_argument(
        "--getPosition",
        action="store_true",
        help="Get the current position of the Zaber controller in mm."
    )
    zaber_parser.add_argument("--verbose", action="store_true", default=False, help="Enable verbose output.")
    zaber_parser.set_defaults(func=zaber)

    # command: mount (iOptron telescope mount control)
    mount_parser = subparsers.add_parser(
        "mount",
        help="Control iOptron HAZ-series Alt-Az telescope mount",
        description="iOptron mount control commands"
    )
    mount_subparsers = mount_parser.add_subparsers(
        dest="mount_action", required=True,
        help="Mount control actions"
    )

    # mount status
    mount_status_parser = mount_subparsers.add_parser(
        "status", help="Show current Alt/Az position and state"
    )
    mount_status_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_status_parser.set_defaults(func=mount_status)

    # mount goto <alt> <az>
    mount_goto_parser = mount_subparsers.add_parser(
        "goto", help="Slew to specified Alt/Az position"
    )
    mount_goto_parser.add_argument(
        "altitude", type=float, help="Target altitude in degrees (-90 to +90)"
    )
    mount_goto_parser.add_argument(
        "azimuth", type=float, help="Target azimuth in degrees (0 to 360)"
    )
    mount_goto_parser.add_argument(
        "--track", action="store_true", help="Enable tracking after slew"
    )
    mount_goto_parser.add_argument(
        "--status", action="store_true", help="Print status after slew completes"
    )
    mount_goto_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_goto_parser.set_defaults(func=mount_goto)

    # mount home
    mount_home_parser = mount_subparsers.add_parser(
        "home", help="Return to home (zenith) position"
    )
    mount_home_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_home_parser.set_defaults(func=mount_home)

    # mount park
    mount_park_parser = mount_subparsers.add_parser(
        "park", help="Park mount at stored parking position"
    )
    mount_park_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_park_parser.set_defaults(func=mount_park)

    # mount unpark
    mount_unpark_parser = mount_subparsers.add_parser(
        "unpark", help="Unpark mount to allow movements"
    )
    mount_unpark_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_unpark_parser.set_defaults(func=mount_unpark)

    # mount stop
    mount_stop_parser = mount_subparsers.add_parser(
        "stop", help="Emergency stop - halt all motion immediately"
    )
    mount_stop_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_stop_parser.set_defaults(func=mount_stop)

    # mount set-park <alt> <az>
    mount_set_park_parser = mount_subparsers.add_parser(
        "set-park", help="Define a new parking position"
    )
    mount_set_park_parser.add_argument(
        "altitude", type=float, help="Altitude for park position in degrees"
    )
    mount_set_park_parser.add_argument(
        "azimuth", type=float, help="Azimuth for park position in degrees"
    )
    mount_set_park_parser.add_argument(
        "--no-move", dest="move_first", action="store_false",
        help="Set park position without moving to it first"
    )
    mount_set_park_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_set_park_parser.set_defaults(func=mount_set_park)

    # mount get-position
    mount_get_position_parser = mount_subparsers.add_parser(
        "get-position", help="Query current Alt/Az position"
    )
    mount_get_position_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_get_position_parser.set_defaults(func=mount_get_position)

    # mount set-alt-limit <deg>
    mount_set_alt_limit_parser = mount_subparsers.add_parser(
        "set-alt-limit", help="Set minimum altitude safety limit"
    )
    mount_set_alt_limit_parser.add_argument(
        "limit", type=int, help="Altitude limit in degrees (-89 to 89)"
    )
    mount_set_alt_limit_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_set_alt_limit_parser.set_defaults(func=mount_set_alt_limit)

    # mount get-alt-limit
    mount_get_alt_limit_parser = mount_subparsers.add_parser(
        "get-alt-limit", help="Query current altitude safety limit"
    )
    mount_get_alt_limit_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output"
    )
    mount_get_alt_limit_parser.set_defaults(func=mount_get_alt_limit)

    # # command: expose
    # expose_parser = subparsers.add_parser("expose", help="Expose telescope with a known photon dose.")
    # expose_parser.add_argument("--wavelength", type=float, default=500.0, help="Wavelength for exposure (nm).")
    # expose_parser.add_argument("--dose", type=float, default=1e12, help="Desired photon dose.")
    # expose_parser.add_argument("--filters", type=str, default="ND3", help="ND filters to use.")
    # expose_parser.add_argument("--aperture", type=str, default="10um", help="Aperture mask (e.g., 10um).")
    # expose_parser.set_defaults(func=exposeFocalPlane)

    # # command: spectrograph-calib
    # spec_calib_parser = subparsers.add_parser(
    #     "spectrograph-calib",
    #     help="Calibrate the spectrograph using arc lamp emission lines."
    # )
    # spec_calib_parser.set_defaults(func=spectrographCalib)

    # # command: monochromator-calib
    # mono_calib_parser = subparsers.add_parser(
    #     "monochromator-calib",
    #     help="Calibrate the monochromator via the spectrograph readings."
    # )
    # mono_calib_parser.set_defaults(func=monochromatorCalib)

    # Parse arguments and dispatch
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
