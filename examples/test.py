import sys
sys.path.append("/Users/pandora_ctrl/Documents/dev/versions/v1.0/PANDORA")
# from pandora.pandora_controller import PandoraBox
# pandora_box = PandoraBox("../default.yaml")

from pandora.commands.keysight import KeysightState
settings = {
            'mode': "CURR",
            'rang': 'AUTO',
            'nplc': 1.,
            'nsamples': 10,
            'delay': 0.,
            'interval': 2e-3,
            }

k1 = KeysightState(name="K01", keysight_ip="169.254.5.2", timeout_ms=5000)
k2 = KeysightState(name="K02", keysight_ip="169.254.124.255", timeout_ms=5000)
k1.get_device_info()
k2.get_device_info()

k1.on()
k2.on()

k1.acquire()
k2.acquire()
d = k1.read_data(wait=True)
print(d)
d = k2.read_data(wait=True)

k1.close()
k2.close()