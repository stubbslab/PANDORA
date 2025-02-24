"""

Command line interface for measuring pandora throughput.

Usage:
    pb measure-pandora-throughput --lambda0 300 --lambdaEnd 700 --step 1 --maskPorts

"""
def measurePandoraThroughput(args):
    from pandora.pandora_controller import PandoraBox   
    pandora_box = PandoraBox(config_file="../default.yaml", verbose=True)

    pandora_box.move_nd_filter("CLEAR")
    pandora_box.turn_on_sollar_cell()
    pandora_box.wavelegth_scan(args.lambda0, args.lambdaEnd, args.step, observation_type="throughput")
    saveNDTransmissionCalibrationFile(pandora_box)

    pass

## TODO: Make a calibration folder
## TODO: Make a standard calibration file name
def saveNDTransmissionCalibrationFile(pandora_box):
    """
    Save the ND transmission calibration file.

    """
    df = pandora_box.get_database()
    df.to_csv("NDTransmissionCalibration.csv")