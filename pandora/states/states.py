from enum import Enum

class State(Enum):
    UNINITIALIZED = "uninitialized"
    IDLE = "idle"
    ON = "on"
    OFF = "off"
    FAULT = "fault"
    MEASURING = "measuring"
    CALIBRATING = "calibrating"
    WAITING = "waiting"
    

