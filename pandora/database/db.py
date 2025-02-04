import os
import csv
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from columns_map import COLUMN_DEFINITIONS, DEFAULT_VALUES

class PandoraDatabase:
    """
    Class to handle reading/writing Pandora photodiode and mount measurements.
    The run_id follows the pattern: YYYYMMDDXXX (XXX = 001..999).

    File structure:
        ./.run_cache.csv
        ./data/<run_id>.csv
        ./lightcurves/<run_id>/<expid>.csv
    """
    
    def __init__(self, 
                 date: str = None,     # expected format 'YYYYMMDD'
                 root_path: str = "~/",
                 run_id: str = None,
                 writing_mode: bool = True):
        """
        Parameters
        ----------
        date : str, optional
            A date string in the format YYYYMMDD. If None, today's date is used.
        root_path : str, optional
            The root folder where the data structure will be created. Default is "./".
        run_id : str, optional
            If provided, this exact run_id is used (if valid). Otherwise, we generate/find one.
        writing_mode : bool, optional
            If True, we create a new run_id if one is not provided. 
            If False, we just load the latest or a given run_id for reading.
        """
        # Set up logging
        self.logger = logging.getLogger(f"pandora.database")

        # Use today's date if none provided
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        self.date_str = date
        
        # Root path
        self.logger.info(f"Root path: {root_path}")
        self.root_path = os.path.abspath(root_path)
        
        # Path to hidden cache of run_ids
        self.cache_file = os.path.join(self.root_path, ".run_cache.csv")
        
        # Initialize or set run_id
        self.set_run_id(run_id=run_id, writing_mode=writing_mode)
        
        # Initialize folder structure and file paths
        self.init_paths()
        
        # Load or create the main run CSV
        self._load_or_init_run_db()
        
        # Determine the next exposure ID (start at 0 if empty)
        self.set_next_expid()
    
        # Initialize a temporary dict to hold current exposure's properties
        self.current_exposure = DEFAULT_VALUES.copy()
        
        print(f"Initialized PandoraDatabase with run_id={self.run_id}")

    def init_paths(self):
        """
        Sets up all relevant paths and directories for the data, run, and lightcurves.
        """
        self.logger.info(f"Initializing paths for run_id={self.run_id}")
        # Directories
        self.data_path = os.path.join(self.root_path, "data")
        self.lightcurves_dir = os.path.join(self.root_path, "lightcurves", self.run_id)
        
        # Files
        self.run_data_file = os.path.join(self.data_path, f"{self.run_id}.csv")
        
        # Create directories if they don't exist
        os.makedirs(self.root_path, exist_ok=True)
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.lightcurves_dir, exist_ok=True)

        self.logger.debug(f"Paths initialized: {self.data_path}, {self.lightcurves_dir}")
        self.logger.debug(f"Directories created: {self.root_path}, {self.data_path}, {self.lightcurves_dir}")

    def add(self, key: str, value):
        """
        Adds or updates a property for the current exposure.

        Parameters
        ----------
        key : str
            The name of the property to add/update.
        value :
            The value of the property.
        """
        if key not in COLUMN_DEFINITIONS:
            raise KeyError(f"'{key}' is not a valid column name.")
        
        if key != "timestamp" :
            if not isinstance(value, COLUMN_DEFINITIONS[key]):
                raise TypeError(f"Value for '{key}' must be of type {COLUMN_DEFINITIONS[key].__name__}.")
        else:
            if not isinstance(value, (str, datetime)):
                value = value.isoformat()
            
        self.current_exposure[key] = value
        self.logger.debug(f"Added property '{key}' with value '{value}' to current exposure.")

    def write_exposure(self) -> int:
        """
        Writes the current exposure to the database using the properties set via `add`.
        Applies default values for any missing properties.

        Returns
        -------
        int
            The expid assigned to this new exposure.
        """
        # Assign a new expid
        self.current_expid += 1
        expid = self.current_expid

        # Initialize a new row with default values
        new_row = DEFAULT_VALUES.copy()
        
        # Update the new_row with any properties set via `add`
        new_row.update(self.current_exposure)
        new_row["expid"] = expid

        # Append to in-memory DataFrame
        new_row_df = pd.DataFrame([new_row])

        # Ensure self.run_db is correctly initialized before concatenation
        if self.run_db.empty:
            self.run_db = new_row_df
        else:
            self.run_db = pd.concat([self.run_db, new_row_df], ignore_index=True)

        # Save to individual CSV
        # exp_file = os.path.join(self.lightcurves_dir, f"{expid:04d}.csv")
        # pd.DataFrame([new_row]).to_csv(exp_file, index=False)

        # Update the main run CSV
        self.run_db.to_csv(self.run_data_file, index=False)
        self.logger.info(f"Wrote exposure expid={expid} to run_id={self.run_id}")

        # Reset the current exposure
        self.current_exposure = {}
        pass

    def get_exposure(self, expid: int) -> pd.Series:
        """
        Retrieve a single exposure (row) from the in-memory DB by expid.
        
        Raises
        ------
        ValueError if expid is not found.
        """
        row = self.run_db.loc[self.run_db["expid"] == expid]
        if row.empty:
            raise ValueError(f"Exposure ID {expid} not found in run {self.run_id}.")
        return row.iloc[0]

    def set_run_id(self, run_id: str = None, writing_mode: bool = True):
        """
        Sets the run_id for this instance. If run_id is None and we are in writing_mode,
        generate a new one. Otherwise, use the provided or load the latest for this date.
        
        Parameters
        ----------
        run_id : str
            A run_id of the form YYYYMMDDXXX, or None.
        writing_mode : bool
            If True, we create a new run_id if none is provided.
        """
        # If a run_id is explicitly provided, trust that it is valid
        if run_id is not None:
            self.logger.info(f"Using provided run_id: {run_id}")
            self.run_id = run_id
            return
        
        # If no run_id is provided, either generate new or load the latest from cache
        if writing_mode:
            self.logger.info(f"Generating new run_id for date {self.date_str}")
            self.run_id = generate_new_run_id(self.date_str, self.cache_file)
        else:
            self.logger.info(f"Loading latest run_id for date {self.date_str}")
            # Load the most recent run_id for this date from the cache (or default)
            self.run_id = self._latest_run_id_for_date(self.date_str)

        self.logger.info(f"Set run_id to {self.run_id}")

    def set_next_expid(self):
        if self.run_db.empty:
            self.logger.info(f"Run database is empty, starting with expid=0")
            self.current_expid = 0
        else:
            self.logger.info(f"Loading latest expid from run database")
            self.current_expid = self.run_db["expid"].max()
        self.logger.info(f"Set expid to {self.current_expid}")
        pass

    def save_lightcurve(self, data, tag="k1"):
        """
        Saves a lightcurve for a given expid to the appropriate directory.
        
        Parameters
        ----------
        expid : int
            The exposure ID.
        data : pd.DataFrame
            The lightcurve data to save.
        """
        expid = self.current_expid
        lc_path = os.path.join(self.lightcurves_dir, f"{tag}_{expid:03d}")
        np.save(data, lc_path)
        self.logger.info(f"Saved lightcurve for expid={expid} to {lc_path}")

    def _latest_run_id_for_date(self, date_str: str) -> str:
        """
        Finds the highest run_id for the given date in the cache file.
        If none is found, defaults to date_str + "001" (but does not write to the cache).
        """
        run_ids_for_date = []
        
        # If the cache doesn't exist, just return "DATE001"
        if not os.path.exists(self.cache_file):
            return f"{date_str}001"
        
        with open(self.cache_file, mode="r") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                rid = row["run_id"]
                if rid.startswith(date_str):
                    run_ids_for_date.append(rid)
        
        if not run_ids_for_date:
            return f"{date_str}001"
        else:
            existing_suffixes = [int(r[-3:]) for r in run_ids_for_date if len(r) == 11]
            max_suffix = max(existing_suffixes)
            return f"{date_str}{max_suffix:03d}"

    def _load_or_init_run_db(self):
        """Loads or creates a DataFrame corresponding to this run_id."""
        if os.path.exists(self.run_data_file):
            # When loading, specify dtype where possible
            self.run_db = pd.read_csv(self.run_data_file, dtype=self._get_dtype_dict())
        else:
            # Create a new DataFrame with columns from COLUMN_DEFINITIONS
            self.run_db = pd.DataFrame({col: pd.Series(dtype=dt) for col, dt in COLUMN_DEFINITIONS.items()})
            self.run_db.to_csv(self.run_data_file, index=False)

    def _get_dtype_dict(self):
        """
        Constructs a dtype dictionary for pandas based on COLUMN_DEFINITIONS.
        Converts Python types to pandas-compatible types if necessary.
        """
        dtype_map = {}
        for col, dtype in COLUMN_DEFINITIONS.items():
            if dtype == int:
                dtype_map[col] = 'Int64'  # Pandas nullable integer
            elif dtype == float:
                dtype_map[col] = 'float'
            elif dtype == str:
                dtype_map[col] = 'string'
            else:
                dtype_map[col] = 'object'
        return dtype_map

    def save(self):
        """Saves the in-memory DataFrame to the main run CSV file."""
        self.run_db.to_csv(self.run_data_file, index=False)
        self.logger.info(f"Saved run database for run_id={self.run_id}")

    def close(self):
        """Closes the database by saving the current data to disk."""
        self.save()
        self.logger.info(f"Closed PandoraDatabase for run_id={self.run_id}")
        self.run_db = None

def generate_new_run_id(date_str: str, cache_file: str) -> str:
    """
    Reads the .run_cache.csv file to find the highest 3-digit suffix used for
    this date (YYYYMMDD) and increments it by 1. Then writes the new run_id
    back to the cache.

    Parameters
    ----------
    date_str : str
        The date string in the format YYYYMMDD.
    cache_file : str
        Path to the .run_cache.csv file.

    Returns
    -------
    str
        The newly generated run_id of the form YYYYMMDDXXX.
    """
    run_ids_for_date = []

    # Ensure the cache file exists; if not, create it
    if not os.path.exists(cache_file):
        with open(cache_file, mode="w", newline='') as fp:
            writer = csv.writer(fp)
            writer.writerow(["run_id"])

    # Read all run_ids for this date
    with open(cache_file, mode="r") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            rid = row["run_id"]
            # Check if it starts with the given date_str
            if rid.startswith(date_str):
                run_ids_for_date.append(rid)

    # Determine the new suffix
    if not run_ids_for_date:
        new_suffix = 1
    else:
        # Parse the suffix from each run_id's last 3 digits
        existing_suffixes = [
            int(r[-3:]) for r in run_ids_for_date 
            if len(r) == 11  # length of YYYYMMDDXXX
        ]
        new_suffix = max(existing_suffixes) + 1

    if new_suffix > 999:
        raise ValueError(f"Exceeded 999 runs in one day ({date_str}).")

    new_run_id = f"{date_str}{new_suffix:03d}"

    # Append to the cache file
    with open(cache_file, mode="a", newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow([new_run_id])

    return new_run_id

# Example usage (comment out if integrating into a larger system):
if __name__ == "__main__":
    from datetime import datetime
    from utils.logger import initialize_central_logger     
    
    # Set up logging
    initialize_central_logger("../database.log", "INFO", verbose=True)

    # Instantiate (in writing mode, no run_id => auto-generate)
    pdb = PandoraDatabase(root_path="/Users/pandora_ctrl/Desktop", writing_mode=True)
        
    # Add properties one by one
    pdb.add("timestamp", datetime.now())
    pdb.add("current", 1.23)
    pdb.add("wavelength", 532.0)
    pdb.add("alt", 45.0)
    pdb.add("az", 100.0)
    pdb.add("description", "Test measurement")
    
    # Write the exposure
    pdb.write_exposure()
    
    # Optionally, add another exposure with some default values
    pdb.add("timestamp", datetime.now())
    pdb.add("current", 2.34)
    # Missing 'wavelength', 'alt', 'az', 'description' will use defaults
    pdb.write_exposure()
    
    # Save & close
    pdb.close()
