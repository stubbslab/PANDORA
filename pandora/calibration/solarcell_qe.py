"""

Script to measure the quantum efficiency of the solar cell

"""
from dark import correctDarkCurrent
from nist_qe import getNISTQE

def computeSolarCellQE(df):
    """
    Measure the quantum efficiency of the solar cell

    Args:
        df (pandas.DataFrame): The raw data frame with the pandora measurements from `solar_cell_qe_curve` task.

    Returns:
        df (pandas.DataFrame): The data frame with the quantum efficiency of the solar cell.
    """
    # Get the data with NIST diode on the beam
    nist_df = df[df['NIST'] == True].copy()

    # Get the data with NIST diode off the beam
    solarcell_df = df[df['NIST'] == False].copy()
    
    # Get the NIST QE curve
    qeNIST = getNISTQE()

    # TBD
    # return transmission_stats
    # qe = solarCellCurrent/nistCurrent * qeNIST(wavelength)
