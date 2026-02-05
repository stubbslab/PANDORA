# Keysight B2980B — Charge Measurement Notes

## Instrument Overview

The Keysight B2980B Series includes Femto/Picoammeters (B2981B, B2983B) and Electrometers/High Resistance Meters (B2985B, B2987B). **Charge measurement is only available on the B2985B and B2987B** (Electrometer models).

Official documentation is available from Keysight:

- [User's Guide (PDF)](https://www.keysight.com/us/en/assets/9921-01472/user-manuals/B2980B-Femto-Picoammeter-and-Electrometer-High-Resistance-Meter-Users-Guide.pdf) — Manual Part Number B2980-90110, Edition 2, May 2023
- [Programming Guide (PDF)](https://www.keysight.com/us/en/assets/9921-01474/programming-guides/B2980B-Femto-Picoammeter-and-Electrometer-High-Resistance-Meter-Programming-Guide.pdf)
- [SCPI Command Reference (PDF)](https://www.keysight.com/us/en/assets/9921-01475/programming-guides/B2980B-Femto-Picoammeter-and-Electrometer-High-Resistance-Meter-SCPI-Command-Reference.pdf)

---

## How Charge Measurement Works

### Principle of Operation

The coulomb meter uses an **integrating feedback capacitor** on the input amplifier. The voltage across the capacitor is proportional to the integral of the input current:

$$V = \frac{1}{C} \int i \, dt = \frac{Q_s}{C}$$

The capacitance *C* is known and accurate. By measuring the voltage, the instrument calculates the accumulated charge *Qs*.

There are **two separate processes** happening:

1. **Analog integration** — the feedback capacitor continuously accumulates charge as long as the coulomb meter is enabled. This runs indefinitely until the instrument is disabled or the automatic discharge resets it.
2. **A/D digitization** — periodically, the A/D converter reads the capacitor voltage using the aperture time window. This is where NPLC matters for AC noise rejection.

### Measurement Ranges

| Range | Max Value | Resolution |
|-------|-----------|------------|
| 2 nC  | ±2.1 nC   | 1 fC       |
| 20 nC | ±21 nC    | 10 fC      |
| 200 nC| ±210 nC   | 100 fC     |
| 2 µC  | ±2.1 µC   | 1 pC       |

### Connection

Uses the **Ammeter triaxial input**. Common terminal is connected to chassis ground via banana-to-lug cable. For floating measurements, leave Common disconnected from chassis ground.

---

## Aperture Time and NPLC

The aperture time (set via `SENS:CHAR:NPLC`) controls the A/D observation window for each charge reading — **not** how long charge accumulates on the feedback capacitor.

- Described by **Number of Power Line Cycles (NPLC)**
- One PLC = 20 ms (50 Hz) or 16.667 ms (60 Hz)
- Setting to 1 PLC or integer multiples rejects AC power line noise
- Available manual values: 0.001, 0.01, 0.1, 1.0, 10.0, 100.0 PLC
- Automatic modes: Quick, Normal, Stable

The NPLC-based aperture time system is **identical for both current and charge measurements**. The difference is only what the A/D digitizes: instantaneous current vs. voltage across the feedback capacitor.

---

## Key Setup Parameters

### Automatic Discharge
Prevents range overflow by resetting the integrator when charge reaches a threshold.

- Enable/disable: `SENS:CHAR:DISCharge:AUTO ON|OFF`
- Threshold levels: 2 nC, 20 nC, 200 nC, or 2 µC (`SENS:CHAR:DISCharge:LEVel`)

### Manual Discharge
Zeroes the feedback capacitor before a new measurement: `SENS:CHAR:DISCharge`

### Measurement Filter
Averaging/smoothing of readings for noise reduction. Recommended for precise measurement.

### Null / Offset Cancel
Stores a reference measurement and subtracts it from subsequent readings.

---

## Relevant Manual Sections

From the User's Guide (B2980-90110):

| Section | Page | Content |
|---------|------|---------|
| Chapter 3: Charge Measurement | p. 120 | Ranges, connections, step-by-step procedure |
| Setup Parameters | p. 122 | Auto discharge, measure coulomb range, aperture time, filter |
| About Charge Measurement | p. 123 | Theory of operation (feedback capacitor integration) |
| Chapter 5: Aperture Time | p. 206 | NPLC explanation, AC noise rejection |
| Chapter 5: Null, Offset Cancel (Charge) | p. 210 | Zero correction for current and charge |

---

## Adapting the PANDORA Keysight Controller for Charge Mode

The existing `KeysightController` in [`pandora/controller/keysight.py`](https://github.com/stubbslab/PANDORA/blob/main/pandora/controller/keysight.py) is designed for current measurements. Most of its SCPI plumbing is already mode-agnostic (commands use `self.params["mode"]`), so switching to charge requires minimal changes.

### What Works As-Is
- `set_mode('CHAR')` — sends `SENSe:FUNCtion:ON "CHAR"`
- `set_nplc()` — sends `SENS:CHAR:NPLC ...`
- `set_rang()` — sends `SENS:CHAR:RANG ...`
- `acquire()` and `read_data()` — parametrize on mode
- Trigger/interval/nsamples setup is mode-independent

### What Needs to Change

1. **Add a discharge method** (most important) — zero the feedback capacitor before each acquisition:
   ```python
   def discharge(self):
       self.write('SENS:CHAR:DISCharge')
   ```

2. **Add auto-discharge configuration:**
   ```python
   def set_auto_discharge(self, enabled=True, level=None):
       state = 'ON' if enabled else 'OFF'
       self.write(f'SENS:CHAR:DISCharge:AUTO {state}')
       if level is not None:
           self.write(f'SENS:CHAR:DISCharge:LEVel {level}')
   ```

3. **Add a charge-aware acquire wrapper:**
   ```python
   def acquire_charge(self, discharge_first=True, **kwargs):
       if discharge_first:
           self.discharge()
       self.acquire(**kwargs)
   ```

4. **`auto_scale()` needs a charge range table** — current ranges (2 pA–2 mA) don't apply. Charge ranges are 2 nC, 20 nC, 200 nC, 2 µC.

5. **`wait_for_settle()` / `_EXP_SETTLING`** — keyed to current range exponents. Charge ranges have different settling characteristics and would error or give wrong delays.

### Example Charge Workflow
```python
keysight.set_mode('CHAR')
keysight.set_rang(2e-8)       # 20 nC range
keysight.set_nplc(0.1)
keysight.set_nsamples(1000)
keysight.acquire_charge()     # discharges, then acquires
d = keysight.read_data(wait=True)
```

---

## Reference Scripts

Two reference scripts were reviewed from a collaborator's implementation:

- **`keysight.py`** (Telnet-based driver) — low-level SCPI controller showing `SENS:CHAR:DISCharge` reset, `CHAR` mode NPLC, and triggered acquisition with `FETC:ARR:CHAR?` readback.
- **`electrometer_for_chrisW.ipynb`** (LSST SAL/CSC notebook) — higher-level interface using `setMode(mode=1)` for charge, `setIntegrationTime(intTime=0.1)` for NPLC, scan-based acquisition returning FITS files. Per-sample read time observed at ~12 ms (consistent with 0.1 NPLC at 60 Hz plus overhead).
