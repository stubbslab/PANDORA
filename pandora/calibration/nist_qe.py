"""

Script to get the quantum efficiency of the NIST photodiode

"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

def getNISTQE():
    """
    Get the quantum efficiency of the NIST photodiode

    Returns:
        qe (function): The quantum efficiency of the NIST photodiode.

        fname: pandora/calibration/7J048_292819_hamatsu_qe.csv
    """
    # Load the NIST QE data
    qe_data = pd.read_csv("./data/7J048_292819_hamatsu_qe.csv")
    wav = qe_data['Wavelength (nm)'].values
    qe = qe_data['QE'].values

    # Interpolate the data
    f = interp1d(wav, qe, bounds_error=False, fill_value=0)
    return f

def plotNISTQE(ax=None, **kwargs):
    """
    Plot the quantum efficiency of the NIST photodiode
    Args:
        ax (matplotlib.axes.Axes): The axes to plot on. If None, a new figure is created.
        kwargs: Additional keyword arguments to pass to the plot function.

    Returns:
        ax (matplotlib.axes.Axes): The axes with the plot.
    """
    if ax is None:
        fig, ax = plt.subplots()
    qe = getNISTQE()

    wav = np.arange(300, 1100+5, 5)
    ax.plot(wav, qe(wav), 'k', **kwargs)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Quantum Efficiency")
    ax.set_title("Quantum Efficiency of the NIST Photodiode")
    ax.grid()
    return ax

if __name__ == "__main__":
    plotNISTQE()
    plt.show()