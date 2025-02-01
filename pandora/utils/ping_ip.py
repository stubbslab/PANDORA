import socket
TIMEOUT = 2 # sec
def is_port_open(host, port=4880, timeout=TIMEOUT):
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
