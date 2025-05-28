import sys
import numpy as np
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")

from pandora.pandora_controller import PandoraBox
from pandora.utils.random import head, line

head("Test: Characterization of the Attenuation System")
print("Description: This test will loop over zaber ND filters and monochromator wavelengths.")
line()

##### Exposure Time Setup
expTime = 0.5 # sec

##### Zaber ND Filter Position Setup
nd_speed = 1.0 # mm/s
dx = 1.0 # mm

# The ND filters are placed between following positions:
NDs = ["CLEAR", "ND20", "ND15", "ND10", "ND05"]
ndrange = {
    "CLEAR": np.arange(0, 10+dx, dx),
    "ND05": np.arange(146.8, 152.4+dx, dx),
    "ND10": np.arange(106.3, 115.6+dx, dx),
    "ND15": np.arange(73.5, 81.7+dx, dx),
    "ND20": np.arange(39.5, 47.1+dx, dx),
}

##### Wavelength Scan Setup
wav = 500 # nm

##### ND filters loop
line()
# Create a PandoraBox object
pandora_box = PandoraBox(config_file="./default.yaml", verbose=False)

# Initialize the Pandora System Components
pandora_box.initialize_subsystems()
pandora_box.flipPD2.activate()

# Clear the optical path
# pandora_box.set_nd_filter("CLEAR")

head(f"Starting wavelength: {wav} nm")
# Move monochromator to 400 nm
pandora_box.set_wavelength(wav)
pandora_box.wavelength = wav

# Loops over ND05, ND10, ND15, ND20
for i, ND in enumerate(NDs):
    head(f"Moving to ND filter: {ND}")
    print(f"ND Filter position: {ndrange[ND].mean():.2f} mm")
    pandora_box.zaberNDFilter.set_zaber_speed(10)
    pandora_box.zaberNDFilter.move_zaber_axis(ndrange[ND].mean())
    pandora_box.set_photodiode_scale()
    pandora_box.zaberNDFilter.move_zaber_axis(np.max([0, ndrange[ND].min()-20*dx]))

    # Reduce the speed
    pandora_box.zaberNDFilter.set_zaber_speed(nd_speed)
    for xi in ndrange[ND]:
        pandora_box.zaberNDFilter.move_zaber_axis(np.min([xi,152.4]))
        pandora_box.zaberNDFilter.position = f"{np.min([xi,152.4]):.2f}"
        print(f"ND Filter position: {xi:.2f} mm")
        pandora_box.take_exposure(expTime)
    line()

pandora_box.close_all_connections()
head("Optical measurement cycle completed.")

head("Wavelength cycle completed.")
print(f"Measurements saved on {pandora_box.pdb.run_data_file}")
print("Goodbye!")
