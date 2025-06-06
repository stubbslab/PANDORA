import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.pandora_controller import PandoraBox
from pandora.utils.logger import initialize_central_logger 

# Set up logging
initialize_central_logger("zaberstage-main.log", "INFO")

# Create a PandoraBox object
pandora_box = PandoraBox(config_file="./default.yaml", verbose=True)
# pandora_box.start_run(run_id) # makes a catalog with name run_id:05d

# Clear the optical path
pandora_box.set_nd_filter("CLEAR")

# Move the focus
# pandora_box.zaberFocus.move_to_slot("FOCUS")

# Move the pinhole mask
# pandora_box.set_pinhole_mask("CLEAR")

# # Create an instance of ZaberController
# zb = ZaberController("169.254.47.12", speed_mm_per_sec=12)
# zb.move_to_slot(mask_slot_name="ND15")
# # zb.move_to_slot(mask_slot_name="CLEAR")
# # zb.go_home()
