"""
Here you can find the tools to measure the Pandora transmission.
"""
import pandas as pd
import numpy as np

from dark import correctDarkCurrent
# from solarcell import qeCurve

def measureTransmission(df, qeCurve, specBins=None):
    """
    Measure the transmission of the Pandora Optical; System.

    Args:
        df (pandas.DataFrame): The raw data frame with the pandora measurements.
        qeCurve (function): The quantum efficiency curve of the solar cell.
        specBin (int): The spectral bin to analyze.

    Returns:
        transmission (pandas.Series): The transmission of the Pandora optical system.
    """
    # Correct the dark current
    df = correctDarkCurrent(df, ycol='currentOutput')
    df = correctDarkCurrent(df, ycol='currentInput')
    df = correctDarkCurrent(df, ycol='currentSolarCell')

    # Drop the dark exposures
    data = df[df['Description'] != 'dark'].copy()

    # Compute number of photons
    data['solarCellQE'] = qeCurve(data['wavelength'])
    data['photonsSolarCell'] = data['fluxSolarCell'] / data['solarCellQE']

    # Compute the transmission
    ratio = data['fluxInput'] / data['fluxSolarCell']
    data['transmission'] = ratio / data['solarCellQE']

    # Compute the transmission mean/error
    # Bin the wavelength column
    data['wavelengthBin'] = pd.cut(data['wavelength'], bins=specBins)

    # Compute mean and standard deviation for each bin, including mean wavelength
    transmission_stats = df.groupby('wavelengthBin').agg(
        wavelength=('wavelength', 'mean'),  # Compute the mean wavelength per bin
        transmission=('transmission', 'mean'),
        transmission_std=('transmission', 'std')
    ).reset_index()

    return transmission_stats


def measureNDFactor(ndt, th):
    """
    Compute the ND factor from the transmission of the ND filters and the throughput.

    Args:
        ndt (pandas.DataFrame): The transmission of the ND filters.
        th (pandas.DataFrame): The throughput of the Pandora.

    Returns:
        nd_ratio (pandas.DataFrame): The ND factor of the ND filters.
    """
    from scipy.interpolate import interp1d
    wav1 = ndt['wavelength'].values
    wav2 = th['wavelength'].values
    
    trans1 = ndt['transmission'].values
    trans2 = th['transmission'].values
    
    trans1Err = ndt['transmission_std'].values
    trans2Err = th['transmission_std'].values

    # The throuput is the transmission with no ND filter
    # Interpolate the transmission of the ND filters to the throughput wavelengths
    trans2_interp = interp1d(wav2, trans2, kind='cubic', fill_value=np.nan)(wav1)
    trans2Err_interp = interp1d(wav2, trans2Err, kind='cubic', fill_value=np.nan)(wav1)
    
    # Compute the ratio and its error
    # The transmission of the ND filters is the transmission of the ND filter divided by the throughput
    ratio = trans1 / trans2_interp
    ratioErr = ratio * np.sqrt((trans1/trans1Err)**2 + (trans2_interp/trans2Err_interp)**2)
    
    # Create the output DataFrame
    out = ndt.copy()
    out['transmission'] = ratio
    out['transmission_std'] = ratioErr
    return out