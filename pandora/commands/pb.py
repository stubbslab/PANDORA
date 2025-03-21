import argparse
# from measure_solar_cell_qe import measureSolarCellQE
# from measure_pandora_throughput import measurePandoraThroughput
# from measure_nd_transmission import measureNDTransmission
# from expose import exposeFocalPlane
# from spectrograph_calib import spectrographCalib
# from monochromator_calib import monochromatorCalib

from utils import set_wavelength, get_wavelength
from utils import open_shutter, close_shutter
from utils import get_keysight_readout
from utils import get_spectrometer_readout

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

    # # command: measure-pandora-throughput
    # pt_parser = subparsers.add_parser(
    #     "measure-pandora-throughput",
    #     help="Measure throughput linking main beam flux to monitor diode flux."
    # )
    # pt_parser.add_argument("--lambda0", type=float, default=300.0, help="Start wavelength (nm).")
    # pt_parser.add_argument("--lambdaEnd", type=float, default=700.0, help="End wavelength (nm).")
    # pt_parser.add_argument("--step", type=float, default=10.0, help="Wavelength step (nm).")
    # pt_parser.add_argument("--nrepeats", type=int, default=5, help="Number of repeats per measurement point.")
    # pt_parser.add_argument("--maskPorts", action="store_true", 
    #                        help="Whether to mask 2 of the 3 output ports.")
    # pt_parser.set_defaults(func=measurePandoraThroughput)

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
    close_shutter_parser.set_defaults(func=close_shutter)

    # command: get-keysight-readout
    keysight_readout_parser = subparsers.add_parser(
        "get-keysight-readout",
        help="Get the readout from the Keysight electrometer."
    )
    keysight_readout_parser.add_argument("name", type=str, help="Name of the measurement.")
    keysight_readout_parser.add_argument("nplc", type=float, help="Number of power line cycles.")
    keysight_readout_parser.add_argument("exptime", type=float, help="Exposure time.")
    keysight_readout_parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    keysight_readout_parser.add_argument("--rang0", type=float, default=None, help="If not none, set auto range with initial range.")
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