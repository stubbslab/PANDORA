import socket
import telnetlib
import time

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

class SimpleSocketSCPI:
    """
    A simple TCP socket interface for SCPI-based instruments on port 5025.
    Opens one connection, reuses it for multiple commands.
    """
    def __init__(self, ip, port=5025, timeout=2.0):
        """
        :param ip: The instrument's IP address
        :param port: Default 5025 for SCPI over TCP
        :param timeout: Socket timeout in seconds
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self):
        """Open a TCP connection to the instrument."""
        self.sock = socket.create_connection((self.ip, self.port), self.timeout)
        self.sock.settimeout(self.timeout)

    def write(self, cmd):
        """
        Send a command (string) to the instrument, appending a newline.
        """
        if not self.sock:
            raise ConnectionError("Socket not connected.")
        if not cmd.endswith('\n'):
            cmd += '\n'
        self.sock.sendall(cmd.encode('ascii'))

    def read(self):
        """
        Read a single line from the instrument, until newline or timeout.
        Returns the line as a string (stripped of trailing newline).
        """
        if not self.sock:
            raise ConnectionError("Socket not connected.")
        data = b''
        while True:
            chunk = self.sock.recv(1)
            if not chunk:
                # No more data or socket closed
                break
            data += chunk
            if chunk == b'\n':
                # Stop at newline
                break
        return data.decode('ascii', errors='ignore').rstrip('\n\r')

    def query(self, cmd):
        """
        A convenience: write the command, then read a line of response.
        """
        self.write(cmd)
        return self.read()

    def close(self):
        """Close the socket connection."""
        if self.sock:
            self.sock.close()
            self.sock = None

class SimpleTelnetSCPI:
    """
    A simple Telnet interface for SCPI-based instruments, nominally on port 5025.
    Opens one Telnet connection, reuses it for multiple commands.
    """

    def __init__(self, ip, port=5025, timeout=2.0):
        """
        :param ip: Instrument's IP address
        :param port: Often 5025 for SCPI. This example tries Telnet on that port.
        :param timeout: Telnet timeout in seconds
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.tn = None

    def connect(self):
        """Open a Telnet connection to the instrument."""
        # telnetlib.Telnet(host, port=None, timeout=None)
        self.tn = telnetlib.Telnet(self.ip, self.port, self.timeout)

    def write(self, cmd):
        """
        Send a SCPI command to the instrument, appending '\n'.
        """
        if not self.tn:
            raise ConnectionError("Telnet session not connected.")
        if not cmd.endswith('\n'):
            cmd += '\n'
        # telnetlib expects bytes
        self.tn.write(cmd.encode('ascii'))

    def read(self, read_until=b'\n'):
        """
        Read until the given delimiter (default: newline) or until timeout.
        Returns the raw bytes read (decode it if desired).
        """
        if not self.tn:
            raise ConnectionError("Telnet session not connected.")
        data = self.tn.read_until(read_until, self.timeout)
        return data

    def query(self, cmd):
        """
        Write the command, then read a single line of response (delimited by newline).
        Returns a decoded ASCII string (stripped of trailing newline).
        """
        self.write(cmd)
        data = self.read(b'\n')
        # For a typical SCPI line, we can decode ASCII and strip trailing whitespace
        return data.decode('ascii', errors='ignore').rstrip('\r\n')

    def close(self):
        """Close the Telnet connection."""
        if self.tn:
            self.tn.close()
            self.tn = None
