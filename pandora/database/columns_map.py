import numpy as np
from datetime import datetime


# External dictionary defining column names and their data types
COLUMN_DEFINITIONS = {
    "expid": int,
    "exptime": float,
    "effective_exptime": float,
    "timestamp": str,      # ISO formatted datetime string
    "photoInput": float,
    "photoInputErr": float,
    "photoOutput": float,
    "photoOutputErr": float,
    "solarCell": float,
    "solarCellErr": float,
    "wavelength": float,
    "alt": float,
    "az": float,
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
    "photoInput": np.nan,
    "photoInputErr": np.nan,
    "photoOutput": np.nan,
    "photoOutputErr": np.nan,
    "solarCell": np.nan,
    "solarCellErr": np.nan,
    "FM1": 'OFF',
    "FM2": 'OFF',
    "FM3": 'OFF',
    "zarber": "",
    "maskSlot": "",
    "shutter": False,
    "wavelength": np.nan,
    "alt": np.nan,
    "az": np.nan,
    "description": ""
}