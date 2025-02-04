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
expTimeDark = 0.25 # sec
line()

# Create a PandoraBox object
pandora_box = PandoraBox("../default.yaml")
# pandora_box.start_run(run_id) # makes a catalog with name run_id:05d
import logging
pandora_box.logger.addHandler(logging.NullHandler())

# Initialize the Pandora System Components
pandora_box.initialize_subsystems()

out = '../data/test/{:04d}_{}_{}'
for wav in [400, 500, 600, 700]:
    head(f"Starting wavelength: {wav} nm")
    # Move monochromator to 400 nm
    pandora_box.set_wavelength(wav)

    # Loops over OD05, OD10, OD15, OD20
    ods = ["CLEAR", "OD20", "OD15", "OD10", "OD05"]
    for od in ods:
        pandora_box.zaber.z1.move_to_slot(od)
        d1, d2 = pandora_box.take_exposure(expTime)
        np.save(out.format(wav, od, 'd1'),d1)
        np.save(out.format(wav, od, 'd2'),d2)

        # pandora_box.take_dark(expTimeDark)
        # pandora_box.take_measurement(expTime)
        # pandora_box.take_dark(expTimeDark)
    print(f"Finsihed wavelength {wav} nm")
    line()

pandora_box.close_all_connections()
head("Optical measurement cycle completed.")

head("Wavelength cycle completed.")
# print(f"Measurements saved on {pandora_box.run_info['output']}")
print("Goodbye!")