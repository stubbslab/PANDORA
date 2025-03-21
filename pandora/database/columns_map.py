import numpy as np
from datetime import datetime


# External dictionary defining column names and their data types
COLUMN_DEFINITIONS = {
    "expid": int,
    "exptime": float,
    "alt": float,
    "az": float,
    "effective_exptime": float,
    "timestamp": str,      # ISO formatted datetime string
    "currentInput": float,
    "currentInputErr": float,
    "currentOutput": float,
    "currentOutputErr": float,
    "solarCell": float,
    "solarCellErr": float,
    "wavelength": float,
    'shutter': bool, 
    'flipSpecMount': bool, 
    'flipOrderBlockFilter': bool,
    'flipOD2First': bool, 
    'flipOD2Second': bool, 
    'flipPD2': bool,
    'flipQuarterWavePlate': bool, 
    'flipPD3': bool,
    'ndFilter': str,
    'pinholeMask': str,
    'focusPosition': str,
    "Description": str
}

# External dictionary defining default values for columns
DEFAULT_VALUES = {
    "timestamp": datetime.now().isoformat(),
    "expid": -99,
    "exptime": -99,
    "effective_exptime": -99,
    "wavelength": np.nan,
    "currentInput": np.nan,
    "currentInputErr": np.nan,
    "currentOutput": np.nan,
    "currentOutputErr": np.nan,
    "solarCell": np.nan,
    "solarCellErr": np.nan,
    'shutter': None, 
    'flipSpecMount': False, 
    'flipOrderBlockFilter': False,
    'flipOD2First': False, 
    'flipOD2Second': False, 
    'flipPD2': False,
    'flipQuarterWavePlate': False, 
    'flipPD3': False,
    'ndFilter': None,
    'pinholeMask': None,
    'focusPosition': None,    
    "alt": np.nan,
    "az": np.nan,
    "description": ""
}