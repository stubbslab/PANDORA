import argparse
from measure_solar_cell_qe import measureSolarCellQE
from measure_pandora_throughput import measurePandoraThroughput
from measure_nd_transmission import measureNDTransmission
from expose import exposeFocalPlane
from spectrograph_calib import spectrographCalib
from monochromator_calib import monochromatorCalib

def measure_solar_cell_qe(args):
    """
    Perform the solar cell QE measurement routine.
    Typically includes scanning wavelengths, taking darks, measuring
    the ratio of photocurrents between a reference photodiode and the solar cell, etc.
    """
    print(f"[measureSolarCellQE] Wavelength range: {args.lambda0} - {args.lambdaEnd} nm")
    print(f"[measureSolarCellQE] Step: {args.step} nm | Repeats: {args.repeats}")


def main():
    parser = argparse.ArgumentParser(
        description="PandoraBox Command-Line Interface (commands)",
        epilog="Use `pb <command> --help` for more details on each command."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # command: measure-solar-cell-qe
    sc_qe_parser = subparsers.add_parser(
        "measure-solar-cell-qe", 
        help="Measure the solar cell QE (ratio vs. wavelength)."
    )
    
    sc_qe_parser.add_argument("--lambda0", type=float, default=300.0, help="Start wavelength (nm).")
    sc_qe_parser.add_argument("--lambdaEnd", type=float, default=800.0, help="End wavelength (nm).")
    sc_qe_parser.add_argument("--step", type=float, default=10.0, help="Wavelength step (nm).")
    sc_qe_parser.add_argument("--repeats", type=int, default=5, help="Number of repeats per measurement point.")
    sc_qe_parser.set_defaults(func=measureSolarCellQE)

    # command: measure-pandora-throughput
    pt_parser = subparsers.add_parser(
        "measure-pandora-throughput",
        help="Measure throughput linking main beam flux to monitor diode flux."
    )
    pt_parser.add_argument("--lambda0", type=float, default=300.0, help="Start wavelength (nm).")
    pt_parser.add_argument("--lambdaEnd", type=float, default=700.0, help="End wavelength (nm).")
    pt_parser.add_argument("--maskPorts", action="store_true", 
                           help="Whether to mask 2 of the 3 output ports.")
    pt_parser.set_defaults(func=measurePandoraThroughput)

    # command: measure-nd-transmission
    nd_parser = subparsers.add_parser(
        "measure-nd-transmission",
        help="Measure wavelength-dependent transmission of ND filters."
    )
    nd_parser.add_argument("--lambda0", type=float, default=400.0, help="Start wavelength (nm).")
    nd_parser.add_argument("--lambdaEnd", type=float, default=700.0, help="End wavelength (nm).")
    nd_parser.add_argument("--filters", type=str, default="ND1", help="Comma-separated ND filters (e.g., ND1,ND2).")
    nd_parser.set_defaults(func=measureNDTransmission)

    # command: expose
    expose_parser = subparsers.add_parser("expose", help="Expose telescope with a known photon dose.")
    expose_parser.add_argument("--wavelength", type=float, default=500.0, help="Wavelength for exposure (nm).")
    expose_parser.add_argument("--dose", type=float, default=1e12, help="Desired photon dose.")
    expose_parser.add_argument("--filters", type=str, default="ND3", help="ND filters to use.")
    expose_parser.add_argument("--aperture", type=str, default="10um", help="Aperture mask (e.g., 10um).")
    expose_parser.set_defaults(func=exposeFocalPlane)

    # command: spectrograph-calib
    spec_calib_parser = subparsers.add_parser(
        "spectrograph-calib",
        help="Calibrate the spectrograph using arc lamp emission lines."
    )
    spec_calib_parser.set_defaults(func=spectrographCalib)

    # command: monochromator-calib
    mono_calib_parser = subparsers.add_parser(
        "monochromator-calib",
        help="Calibrate the monochromator via the spectrograph readings."
    )
    mono_calib_parser.set_defaults(func=monochromatorCalib)

    # Parse arguments and dispatch
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()