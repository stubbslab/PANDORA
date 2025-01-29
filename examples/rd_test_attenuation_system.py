from pandora.pandora_controller import PandoraBox

# Create a PandoraBox object
pandora_box = PandoraBox("default.yaml")

# Start measurement cycle
run_id = int(input("Enter the run ID: "))
pandora_box.start_run(run_id) # makes a catalog with name run_id:05d

# Initialize the Pandora System Components
# Attenuators (FlipMounts) out of the beam
# Shutter closed
# Photodiodes on idle state
# Monochromator at 0 nm
# Zaber stage with home position
pandora_box.initialize_subsystems()

# Move zaber stage to Clear
pandora_box.zaber_od.move_to_slot("CLEAR")

# Move monochromator to 400 nm
pandora_box.monochromator.move_to_wavelength(400)

# Loops over OD05, OD10, OD15, OD20
ods = ["OD05", "OD10", "OD15", "OD20"]
for od in ods:
    pandora_box.zaber_od.move_to_slot(od)
    pandora_box.take_measurement(od, include_dark=True)

pandora_box.close_all_connections()
print("Measurement cycle completed.")
print(f"Measurements saved on {pandora_box.run_info['output']}")
print("Goodbye!")