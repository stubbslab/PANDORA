"""

Command line interface for measuring pandora throughput.

Usage:
    pb measure-pandora-throughput --lambda0 300 --lambdaEnd 700 --step 1 --maskPorts A

"""

# from pandora.calibration.transmission import measureTransmission
import numpy as np
import os

script_dir = os.path.dirname(os.path.realpath(__file__))
default_cfg = os.path.join(script_dir, "../../default.yaml")


def measurePandoraThroughput(args):
    print("Measuring Pandora throughput")

    from pandora.pandora_controller import PandoraBox   
    pandora_box = PandoraBox(config_file=default_cfg, verbose=True)

    # print("Clear the optical path, no ND filters")
    # Take the measurements with no ND filter
    # pandora_box.set_nd_filter("CLEAR")

    # TODO: Implement turn_on_sollar_cell
    # pandora_box.turn_on_sollar_cell()

    # Select the pinhole mask
    # print("Select the pinhole mask")
    # pandora_box.set_pinhole_mask(args.maskPorts)

    print(f"Scanning the wavelength from {args.lambda0} to {args.lambdaEnd} in steps of {args.step} with {args.nrepeats} repeats")
    print("this might take a while...")
    # Scan the wavelength in linear steps from lambda0 to lambdaEnd
    # Takes one dark, one exposure, one dark, moves to the next wavelength
    pandora_box.wavelength_scan(args.lambda0, args.lambdaEnd, args.step, observation_type="throughput", nrepeats=args.nrepeats)
    print(f"wavelength-scan saved on {pandora_box.pdb.run_data_file}")

    # TODO: Implement the transmission curve calculation
    ####################################################
    # Compute the throughput
    # lambdaBins = np.arange(args.lambda0-args.step/2, args.lambdaEnd+args.step*3/2, args.step)
    # get solar cell qe curve
    # print("Getting solar cell QE curve")
    # TODO: Convert Diode QE data to calibration format
    # TODO: Convert solar cell QE data to calibration format
    # solarQE = pandora_box.get_qe_solarcell()
    # diodeQE = pandora_box.get_qe_diode()

    # get the data taken
    # df = pandora_box.get_database()

    # print("Calculating throughput")
    # transmission, dfCalib = measureTransmission(df, solarQE, diodeQE, specBins=lambdaBins)
    
    # print("Saving throughput calibration file")
    # Save the throughput calibration file
    # pandora_box.write_calibration(transmission, "throughput")

    print("Done! Thanks for waiting")
    pass