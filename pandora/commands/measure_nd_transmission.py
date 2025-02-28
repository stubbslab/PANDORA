"""

Command line interface for measuring ND filter transmission.

Usage:
    pb measure-nd-transmission --lambda0 400 --lambdaEnd 700 --filters ND1,ND2

    Steps:
    1. Move to a specific ND filter
    2. Measure the transmission of the ND filter (wavelength scan)
    3. Save the transmission data to a file
    4. Repeat for all specified ND filters

"""
import numpy as np
from pandora.calibration.transmission import measureTransmission
from pandora.calibration.transmission import measureNDFactor

def measureNDTransmission(args):
    from pandora.pandora_controller import PandoraBox   
    pandora_box = PandoraBox(config_file="../../default.yaml", verbose=True)

    # Take the measurements with no ND filter
    pandora_box.move_nd_filter("CLEAR")
    pandora_box.turn_on_sollar_cell()

    # Select the optical mask
    # TODO: Implement move_optical_mask
    pandora_box.move_optical_mask(args.maskPorts)

    for i, ND in enumerate(args.filters.split(",")):
        pandora_box.move_nd_filter(ND)
        # Scan the wavelength in linear steps from lambda0 to lambdaEnd
        # Takes one dark, one exposure, one dark, moves to the next wavelength
        pandora_box.wavelegth_scan(args.lambda0, args.lambdaEnd, args.step, 
                                   observation_type="throughput", nrepeats=args.nrepeats)

    # Compute the transmission for each ND filter
    lambdaBins = np.arange(args.lambda0-args.step/2, args.lambdaEnd+args.step*3/2, args.step)
    
    # Load the latest throughput calibration if fname is None
    th = pandora_box.load_pandora_throughput(args.fname)
    
    # Get the ND filter data
    df = pandora_box.get_database()
    # Get the QE curve
    qeCurve = pandora_box.get_qe_solarcell()

    # Compute the transmission for each ND filter
    for i, ND in enumerate(args.filters.split(",")):
        df_nd = df[df['ND'] == ND].copy()
        transmission = measureTransmission(df_nd, qeCurve, specBins=lambdaBins)
        nd_ratio = measureNDFactor(transmission, th)
        pandora_box.write_calibration(nd_ratio, f"transmission_{ND}")
    pass
