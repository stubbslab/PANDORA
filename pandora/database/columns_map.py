import numpy as np
from datetime import datetime

# External dictionary defining column names and their data types
COLUMN_DEFINITIONS = {
    "exp_id": int,
    "timestamp": str,      # ISO formatted datetime string
    "current": float,
    "wavelength": float,
    "alt": float,
    "az": float,
    "description": str
}

# External dictionary defining default values for columns
DEFAULT_VALUES = {
    "timestamp": datetime.now().isoformat(),
    "current": np.nan,
    "wavelength": np.nan,
    "alt": np.nan,
    "az": np.nan,
    "description": ""
}