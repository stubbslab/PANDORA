"""

Command line interface for measuring ND filter transmission.

Usage:
    pb measure-nd-transmission --lambda0 400 --lambdaEnd 700 --filters ND1,ND2

"""
def measureNDTransmission(args):
    from pandora.pandora_controller import PandoraBox   
    pandora_box = PandoraBox(config_file="../default.yaml", verbose=True)

    for i, ND in enumerate(args.filters.split(",")):
        pandora_box.move_nd_filter(ND)
        pandora_box.wavelegth_scan(args.lambda0, args.lambdaEnd, args.step)
    
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