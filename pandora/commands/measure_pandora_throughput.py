"""

Command line interface for measuring pandora throughput.

Usage:
    pb measure-pandora-throughput --lambda0 300 --lambdaEnd 700 --step 1 --maskPorts A

"""

from pandora.calibration.transmission import measureTransmission
import numpy as np

def measurePandoraThroughput(args):
    print("Measuring Pandora throughput")

    from pandora.pandora_controller import PandoraBox   
    pandora_box = PandoraBox(config_file="../default.yaml", verbose=True)

    print("Clear the optical path, no ND filters")
    # Take the measurements with no ND filter
    pandora_box.move_nd_filter("CLEAR")
    pandora_box.turn_on_sollar_cell()

    # Select the optical mask
    # TODO: Implement move_optical_mask
    print("Select the optical mask")
    pandora_box.move_optical_mask(args.maskPorts)

    print(f"Scanning the wavelength from {args.lambda0} to {args.lambdaEnd} in steps of {args.step} with {args.nrepeats} repeats")
    print("this might take a while...")
    # Scan the wavelength in linear steps from lambda0 to lambdaEnd
    # Takes one dark, one exposure, one dark, moves to the next wavelength
    pandora_box.wavelegth_scan(args.lambda0, args.lambdaEnd, args.step, observation_type="throughput", nrepeats=args.nrepeats)

    # Compute the throughput
    lambdaBins = np.arange(args.lambda0-args.step/2, args.lambdaEnd+args.step*3/2, args.step)
    
    # get solar cell qe curve
    print("Getting solar cell QE curve")
    qeCurve = pandora_box.get_qe_solarcell()

    # get the data taken
    df = pandora_box.get_database()

    print("Calculating throughput")
    transmission = measureTransmission(df, qeCurve, specBins=lambdaBins)
    
    print("Saving throughput calibration file")
    # Save the throughput calibration file
    pandora_box.write_calibration(transmission, "throughput")

    print("Done! Thanks for waiting")
    pass