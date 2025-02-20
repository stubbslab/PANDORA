import sys
import numpy as np
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")

from pandora.pandora_controller import PandoraBox
from pandora.utils.random import head, line

head("Test: Characterization of the Attenuation System")
print("Description: This test will loop over zaber ND filters and monochromator wavelengths.")
line()

##### Exposure Time Setup
expTime = 1.0 # sec
expTimeDark = 1.0 # sec

##### Wavelength Scan Setup
wavelength0 = 350 # nm
wavelengthEnd = 1100 # nm
step = 1 # nm [it depends on the slit size]
wavelengthScan = np.arange(wavelength0,wavelengthEnd+step, step)

##### ND filters loop
NDs = ["CLEAR"]#, "ND05", "ND10", "ND15", "ND20"]

##### Keysight Fine-Tunning
range1 = 200e-9 # B2987B
range2 = 2e-9 # B2983B

line()
# Create a PandoraBox object
pandora_box = PandoraBox(config_file="../default.yaml", verbose=True)
# pandora_box.start_run(run_id) # makes a catalog with name run_id:05d

# Initialize the Pandora System Components
pandora_box.initialize_subsystems()

# Flip the wavelength ordering filter
pandora_box.flipMount.f1.activate()

# Flip mount the photodiode (ND20)
# pandora_box.flipMount.f3.activate()

# Clear the optical path
pandora_box.move_nd_filter("CLEAR")

# # Loops over ND05, ND10, ND15, ND20
NDs = ["CLEAR"]#, "ND05", "ND10", "ND15", "ND20"]
for i, ND in enumerate(NDs):
    for wav in wavelengthScan:
        head(f"Starting wavelength: {wav} nm")
        # Move monochromator to 400 nm
        pandora_box.set_wavelength(wav)
        pandora_box.keysight.k1.set_rang(range1)
        pandora_box.keysight.k2.set_rang(range2)
        pandora_box.move_nd_filter(ND)

        pandora_box.take_dark(expTimeDark)
        pandora_box.take_exposure(expTime)
        pandora_box.take_dark(expTimeDark)
        
    print(f"Finsihed wavelength {wav} nm")
    line()

pandora_box.close_all_connections()
head("Optical measurement cycle completed.")

head("Wavelength cycle completed.")
print(f"Measurements saved on {pandora_box.pdb.run_data_file}")
print("Goodbye!")