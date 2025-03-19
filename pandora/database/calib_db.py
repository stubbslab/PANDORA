import os
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# TODO: Convert Diode QE data to calibration format
# TODO: Convert solar cell QE data to calibration format

class PandoraCalibrationDatabase:
    """
    Class to manage and track calibration files for the Pandora system.

    Calibration files are stored in structured directories:
    ├── calib/
    │   ├── throughput/
    │   ├── transmission_ND01/
    
    A log file keeps track of all created calibration files and their defaults.

    Example Usage:
    --------------
    # Initialize the calibration database
    calib_db = PandoraCalibrationDatabase(root_path="/Users/pandora_ctrl/Desktop")

    # Simulated calibration data
    wavelengths = np.linspace(400, 700, 10)
    transmission = np.random.uniform(0.8, 0.95, size=len(wavelengths))
    transmission_err = np.random.uniform(0.01, 0.02, size=len(wavelengths))

    df_calib = pd.DataFrame({
        "wavelength": wavelengths,
        "transmission": transmission,
        "transmission_err": transmission_err
    })

    # Save calibration file
    calib_db.add_calibration(tag="throughput", data=df_calib)

    # Retrieve the latest calibration
    latest_df = calib_db.get_latest_calibration("throughput")
    print("Latest Calibration Data:\n", latest_df)

    # List all calibrations
    print("Calibration Log:\n", calib_db.list_calibrations())

    # Get a specific calibration file
    fname = calib_db.calib_log['filename'][0]
    specific_df = calib_db.get_calibration_file(fname)
    print("Specific Calibration Data:\n", specific_df)

    # Set a calibration file as default
    calib_db.set_default("throughput", fname)
    """
    def __init__(self, root_path: str = "./", type: str = None):
        """
        Initializes the calibration database.

        Parameters
        ----------
        root_path : str
            Root folder where calibration data is stored. Default is "./".
        """
        self.root_path = os.path.abspath(root_path)
        self.calib_path = os.path.join(self.root_path, "calib")
        self.log_file = os.path.join(self.calib_path, "calibration_log.csv")
        
        # Create main calibration directory if it does not exist
        os.makedirs(self.calib_path, exist_ok=True)
        
        # Initialize logger
        self.logger = logging.getLogger("pandora.calibration")
        self.logger.info(f"Initialized PandoraCalibrationDatabase at {self.calib_path}")
        
        # Load or create the calibration log
        self._load_calibration_log()

    def _load_calibration_log(self):
        """Loads the calibration log file if it exists, otherwise creates a new log."""
        if os.path.exists(self.log_file):
            self.calib_log = pd.read_csv(self.log_file)
        else:
            self.calib_log = pd.DataFrame(columns=["tag", "filename", "timestamp", "lambda0",
                                                   "lambdaEnd", "lambdaWidth", "rms", "is_default"])
            self.calib_log.to_csv(self.log_file, index=False)
            self.logger.info(f"Created new calibration log at {self.log_file}")

    def add_calibration(self, tag: str, data: pd.DataFrame):
        """
        Saves a calibration file and records it in the log.

        Parameters
        ----------
        tag : str
            The tag identifying the type of calibration (e.g., "throughput", "transmission_ND01").
        data : pd.DataFrame
            The processed calibration data to save.

        Returns
        -------
        str
            The filename of the saved calibration file.
        """
        # Create a subfolder for this calibration type
        tag_folder = os.path.join(self.calib_path, tag)
        os.makedirs(tag_folder, exist_ok=True)

        # Generate filename with timestamp
        t0 = datetime.now()
        fname = t0.strftime("%Y%m%d_%H%M%S")
        timestamp = t0.isoformat()
        filename = f"{fname}.csv"
        filepath = os.path.join(tag_folder, filename)
        
        # Save the calibration data
        data.to_csv(filepath, index=False)
        self.logger.info(f"Saved calibration file: {filepath}")

        # Determine if this should be the default (if it's the only file for the tag)
        is_default = False
        if self.calib_log[self.calib_log["tag"] == tag].empty:
            is_default = True

        # Update the log file
        log_entry = {"tag": tag, "filename": filename, "timestamp": timestamp, "is_default": is_default}
        log_entry["rms"] = data["transmission_err"].mean() if "transmission_err" in data.columns else None
        log_entry["lambda0"] = data["wavelength"].min() if "wavelength" in data.columns else None
        log_entry["lambdaEnd"] = data["wavelength"].max() if "wavelength" in data.columns else None
        log_entry["lambdaWidth"] = (data["wavelength"].max() - data["wavelength"].min())/len(data) if "wavelength" in data.columns else None

        self.calib_log = pd.concat([self.calib_log, pd.DataFrame([log_entry])], ignore_index=True)
        self.save_calibration_log()

        return filename

    def set_default(self, tag: str, filename: str = None):
        """
        Sets the default calibration file for a given tag. If no filename is provided,
        it selects the most recent calibration file as the default.

        Parameters
        ----------
        tag : str
            The calibration tag (e.g., "throughput", "transmission_ND01").
        filename : str, optional
            The filename to set as default. If None, the most recent file is selected.
        """
        tag_entries = self.calib_log[self.calib_log["tag"] == tag]

        if tag_entries.empty:
            self.logger.warning(f"No calibration files found for tag: {tag}")
            return

        if filename is None:
            # Select the most recent calibration file
            filename = tag_entries.sort_values("timestamp", ascending=False).iloc[0]["filename"]

        if filename not in tag_entries["filename"].values:
            self.logger.error(f"Filename {filename} not found for tag {tag}. Cannot set as default.")
            raise ValueError(f"Filename {filename} not found for tag {tag}.")

        # Update the log to mark this file as default
        self.calib_log.loc[self.calib_log["tag"] == tag, "is_default"] = False
        self.calib_log.loc[(self.calib_log["tag"] == tag) & (self.calib_log["filename"] == filename), "is_default"] = True
        self.save_calibration_log()

        self.logger.info(f"Set {filename} as the default calibration file for tag: {tag}")

    def get_latest_calibration(self, tag: str) -> pd.DataFrame:
        """
        Retrieves the most recent calibration file for a given tag.

        Parameters
        ----------
        tag : str
            The calibration tag (e.g., "throughput", "transmission_ND01").

        Returns
        -------
        pd.DataFrame
            The latest calibration data as a DataFrame.
        """
        tag_entries = self.calib_log[self.calib_log["tag"] == tag]

        if tag_entries.empty:
            self.logger.warning(f"No calibration files found for tag: {tag}")
            return None
        
        latest_file = tag_entries.sort_values("timestamp", ascending=False).iloc[0]["filename"]
        filepath = os.path.join(self.calib_path, tag, latest_file)

        self.logger.info(f"Loading latest calibration file: {filepath}")
        return read_pd_csv(filepath)

    def get_default_calibration(self, tag: str) -> pd.DataFrame:
        """
        Retrieves the default calibration file for a given tag.

        Parameters
        ----------
        tag : str
            The calibration tag (e.g., "throughput", "transmission_ND01").

        Returns
        -------
        pd.DataFrame
            The default calibration data as a DataFrame.
        """
        tag_entries = self.calib_log[(self.calib_log["tag"] == tag) & (self.calib_log["is_default"] == True)]
        
        if tag_entries.empty:
            self.logger.warning(f"No default calibration file set for tag: {tag}. Using latest.")
            return self.get_latest_calibration(tag)

        default_file = tag_entries.iloc[0]["filename"]
        filepath = os.path.join(self.calib_path, tag, default_file)

        self.logger.info(f"Loading default calibration file: {filepath}")
        return read_pd_csv(filepath)

    def get_calibration_file(self, filename: str) -> pd.DataFrame:
        """
        Retrieves a specific calibration file by tag and filename.

        Parameters
        ----------
        tag : str
            The calibration tag (e.g., "throughput", "transmission_ND01").
        filename : str
            The filename of the calibration file.

        Returns
        -------
        pd.DataFrame
            The calibration data as a DataFrame.
        """
        tag_entries = self.calib_log[self.calib_log["filename"] == filename]
        if tag_entries.empty:
            self.logger.warning(f"Calibration file {filename} not found.")
            return None

        default_file = tag_entries.iloc[0]["filename"]
        tag = tag_entries.iloc[0]["tag"]
        filepath = os.path.join(self.calib_path, tag, default_file)

        self.logger.info(f"Loading calibration file: {filepath}")
        return read_pd_csv(filepath)
                           
    def list_calibrations(self, tag: str = None) -> pd.DataFrame:
        """
        Lists all calibration files, optionally filtering by tag.

        Parameters
        ----------
        tag : str, optional
            If provided, filters the list by this calibration type.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing details of available calibration files.
        """
        if tag:
            return self.calib_log[self.calib_log["tag"] == tag]
        return self.calib_log

    def save_calibration_log(self):
        """Saves the calibration log to disk."""
        self.calib_log.to_csv(self.log_file, index=False)
        self.logger.info("Calibration log saved.")

def read_pd_csv(filepath):
    """
    Reads a CSV file into a pandas DataFrame.

    Parameters
    ----------
    filepath : str
        The path to the CSV file.

    Returns
    -------
    pd.DataFrame
        The loaded data as a DataFrame.
    """
    return pd.read_csv(filepath)

# Example Usage
if __name__ == "__main__":
    from pandora.utils.logger import initialize_central_logger
    initialize_central_logger("calibration.log", "INFO", verbose=True)

    # Initialize the calibration database
    # calib_db = PandoraCalibrationDatabase(root_path="/Users/pandora_ctrl/Desktop")
    calib_db = PandoraCalibrationDatabase(root_path="/Users/esteves/Documents/")

    # # Simulated calibration data
    wavelengths = np.linspace(400, 700, 10)
    transmission = np.random.uniform(0.8, 0.95, size=len(wavelengths))
    transmission_err = np.random.uniform(0.01, 0.02, size=len(wavelengths))

    df_calib = pd.DataFrame({
        "wavelength": wavelengths,
        "transmission": transmission,
        "transmission_err": transmission_err
    })

    # # Save calibration file
    calib_db.add_calibration(tag="throughput", data=df_calib)

    # Retrieve the latest calibration
    latest_df = calib_db.get_latest_calibration("throughput")
    print("Latest Calibration Data:\n", latest_df)

    # List all calibrations
    print("Calibration Log:\n", calib_db.list_calibrations())

    # Get a specific calibration file
    fname = calib_db.calib_log['filename'][0]
    specific_df = calib_db.get_calibration_file(fname)
    print("Specific Calibration Data:\n", specific_df)

    # Set a calibration file as default
    calib_db.set_default("throughput", fname)
