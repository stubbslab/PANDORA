import socket
import pyvisa

TIMEOUT = 2 # sec
def _is_port_open(host, port=4880, timeout=TIMEOUT):
    """
    Quickly check if a TCP port is open on the given host within `timeout` seconds.
    Returns True if the port is open, False otherwise.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False
    else:
        return True
    finally:
        s.close()

# Example usage
rm = pyvisa.ResourceManager('@py')  # Use '@py' for PyVISA-py backend
host = "169.254.60.164"
if _is_port_open(host, 4880, timeout=2):
    # Now open the VISA resource
    instrument = rm.open_resource("TCPIP::{}::hislip0,4880::INSTR".format(host), timeout=5000)
    print("Yeup! i am connected to this ")
else:
    raise Exception("Cannot reach Keysight device at {}:4880".format(host))