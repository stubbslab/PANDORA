"""

Here you find the script to correct the dark current.

The units of the current are in Amperes.
The units of the flux are in electrons per second.

The fluxes are dark corrected by subtracting the dark current from the acquisition data.
The current is only corrected for the columns with the string '_corrected' in the name.

"""

import numpy as np
e_charge = 1.60217662e-19

def correctDarkCurrent(df, ycol='currentOutput'):
    """
    Correct the dark current of the Pandora.

    Args:
        df (pandas.DataFrame): The data frame with the measurements.
        ycol (str): The column to correct.
    
    Returns:
        df (pandas.DataFrame): The data frame with the corrected values.
    
    New columns:
        - ycol_dark: The dark current.
        - ycol_corrected: The dark corrected current in units of Amperes.
        - replace current on ycol per flux: The flux in electrons per second.
    """
    # Define the columns
    dark_ycol = ycol + '_dark'
    ycol_corrected = ycol + '_corrected'
    ycol_electron = ycol.replace('current', 'flux')

    # Select the dark exposures
    dark_mask = df['Description'] == 'dark'

    # Ensure data is sorted
    df = df.sort_values(by="timestamp")

    # Step 1: Create new column with NaNs
    df[dark_ycol] = np.nan

    # Step 2: Fill values where 'Description' is 'dark'
    df[dark_ycol] = df[ycol].where(dark_mask)

    # Step 3: Compute the rolling average dark current (before and after each acq measurement)
    df[dark_ycol] = df[dark_ycol].interpolate(method='linear')

    # Step 4: Subtract the averaged dark current from the acquisition data
    df[ycol_corrected] = df[ycol] - df[dark_ycol]

    # Step 5: Recalculate electrons per second
    df[ycol_electron] = df[ycol_electron] / e_charge
    return df