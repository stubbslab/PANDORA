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
    "FM1": str,
    "FM2": str,
    "FM3": str,
    "zaber": str,
    "maskSlot": str,
    "shutter_opened": bool,
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
    "zarber": "",
    "FM1": 'OFF',
    "FM2": 'OFF',
    "FM3": 'OFF',
    "maskSlot": "",
    "shutter": False,
    "alt": np.nan,
    "az": np.nan,
    "description": ""
}