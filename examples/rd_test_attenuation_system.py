import sys
import numpy as np
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")

from pandora.pandora_controller import PandoraBox
from pandora.utils.random import head, line

head("Test: Characterization of the Attenuation System")
print("Description: This test will loop over zaber ND filters and monochromator wavelengths.")
line()

# Start measurement cycle
# run_id = int(input("Enter the run ID: "))
expTime = 1.0 # sec
expTimeDark = 1.0 # sec
line()

# Create a PandoraBox object
pandora_box = PandoraBox(config_file="../default.yaml", verbose=False)
# pandora_box.start_run(run_id) # makes a catalog with name run_id:05d

# Initialize the Pandora System Components
pandora_box.initialize_subsystems()

# Clear the optical path
pandora_box.move_nd_filter("CLEAR")


# Loops over ND05, ND10, ND15, ND20
NDs = ["CLEAR", "ND05", "ND10", "ND15", "ND20"]
# NDs = ["CLEAR"]
for i, ND in enumerate(NDs):
    scale = 1
    for wav in np.arange(400,700+10, 10):
        head(f"Starting wavelength: {wav} nm")
        # Move monochromator to 400 nm
        pandora_box.set_wavelength(wav)
        pandora_box.keysight.k1.set_rang(200e-9)
        pandora_box.keysight.k2.set_rang(20e-9/scale)
        pandora_box.move_nd_filter(ND)
        pandora_box.take_dark(expTimeDark)
        pandora_box.take_exposure(expTime)
        pandora_box.take_dark(expTimeDark)
        # print(f"Scale set to be: {scale:0.2f}")
        
    print(f"Finsihed wavelength {wav} nm")
    line()

pandora_box.close_all_connections()
head("Optical measurement cycle completed.")

head("Wavelength cycle completed.")
print(f"Measurements saved on {pandora_box.pdb.run_data_file}")
print("Goodbye!")