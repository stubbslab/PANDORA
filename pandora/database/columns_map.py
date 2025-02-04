import numpy as np
from datetime import datetime


# External dictionary defining column names and their data types
COLUMN_DEFINITIONS = {
    "expid": int,
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
    "FM1": bool,
    "FM2": bool,
    "FM3": bool,
    "zarber": str,
    "maskSlot": str,
    "shutter": bool,
    "description": str
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
    "FM1": False,
    "FM2": False,
    "FM3": False,
    "zarber": "",
    "maskSlot": "",
    "shutter": False,
    "wavelength": np.nan,
    "alt": np.nan,
    "az": np.nan,
    "description": ""
}