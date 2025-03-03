The QE data was obtained from Hamatsu and is in the form of an Excel file. 
The following code converts the data to a CSV file.

Header of the Excel file:
Responsivity of Hamamatsu S2281 Si Photodiode, 7J048 (292819)		
Lab Temperature: 22.6 °C ± 0.5 °C		
Work. Stds.:	6J088	6J090
Test Date:	08-May-19	
Wavelength [nm]	Spectral power responsivity [A/W]	Relative expanded uncertainty   (k = 2) [%]


###############################################
Python Script to convert Hamatsu QE data to CSV
###############################################

import pandas as pd
fname = 'Downloads/7J048 (292819) asr email 2019-07-11.xlsx'
# fname = 'Downloads/7J048 (292819) asr email 2019-07-11.xlsx'

qe_df = pd.read_excel(fname)
qe_df.head()
qe_cleaned_df = qe_df.iloc[4:].reset_index(drop=True)
qe_cleaned_df.columns = ['Wavelength (nm)', 'Responsivity (A/W)', 'Uncertainty (%)']
# Convert columns to numeric
qe_cleaned_df['Wavelength (nm)'] = pd.to_numeric(qe_cleaned_df['Wavelength (nm)'])
qe_cleaned_df['Responsivity (A/W)'] = pd.to_numeric(qe_cleaned_df['Responsivity (A/W)'])

# The wavelenght is integer
qe_cleaned_df['Wavelength (nm)'] = np.round(qe_cleaned_df['Wavelength (nm)'],0).astype(int)

# Compute QE using the provided formula
qe_cleaned_df['QE'] = qe_cleaned_df['Responsivity (A/W)'] * (1240 / qe_cleaned_df['Wavelength (nm)'])
qe_cleaned_df['QE'] = qe_cleaned_df['QE'].round(5)
qe_cleaned_df.to_csv('Downloads/7J048_292819_hamatsu_qe.csv', index=False)