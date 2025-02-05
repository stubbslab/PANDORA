import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
from pandora.commands.zaberstages import ZaberController
from pandora.utils.logger import initialize_central_logger  

# Set up logging
initialize_central_logger("zaberstage-main.log", "INFO")

# Create an instance of ZaberController
zb = ZaberController("169.254.47.12", speed_mm_per_sec=12)
# zb.go_home()
