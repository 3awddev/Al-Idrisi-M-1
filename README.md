# Al-Idrisi-M1 — CanSat Flight Control System

> A complete end-to-end CanSat competition platform: dual-ESP32 flight computer, 3D-printable enclosure, and PyQt6 ground control station with real-time telemetry, 3D visualisation, and simulation.

---

## Table of Contents

1. [For Absolute Beginners](#for-absolute-beginners)
2. [For Aerospace & Software Engineers](#for-aerospace--software-engineers)
   - [Project Overview](#project-overview)
   - [Flight Hardware — Dual ESP32 Architecture](#flight-hardware--dual-esp32-architecture)
   - [3D CAD — Parametric CanSat Enclosure](#3d-cad--parametric-cansat-enclosure)
   - [CFC Software — Ground Control Station](#cfc-software--ground-control-station)
   - [Flight Firmware — Main ESP32](#flight-firmware--main-esp32)
   - [Flight Firmware — ESP32-CAM Coprocessor](#flight-firmware--esp32-cam-coprocessor)
   - [Telemetry & Command Protocols](#telemetry--command-protocols)
   - [Power Budget](#power-budget)
   - [Build Guide](#build-guide)
   - [Competition Workflow](#competition-workflow)

---

## For Absolute Beginners

### What is a CanSat?

A CanSat is a **miniature satellite** that fits inside a standard soda can (67 mm diameter × 120 mm tall). It's launched on a small rocket to ~800 m altitude, then descends by parachute while transmitting sensor data to a ground station on Earth. University and high-school teams worldwide build CanSats for the annual **CanSat Competition** organised by the American Astronomical Society.

Every CanSat must contain:
- A **flight computer** (microcontroller + sensors)
- A **radio** to transmit data back to the ground
- A **parachute** deployment mechanism
- A **battery** to power everything
- A **structural frame** (the "can" body)

### What does this project do?

This project is a **complete CanSat engineering kit** with three main parts:

```
┌─────────────────────────────────────────────────────────┐
│              AL-IDRISI-M1 SYSTEM OVERVIEW                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐    433 MHz LoRa    ┌─────────────┐│
│  │  FLIGHT SYSTEM  │ ◄──────────────►   │  GROUND      ││
│  │  (in the can)   │                    │  STATION     ││
│  │                 │                    │  (laptop)    ││
│  │  • ESP32 (main) │                    │              ││
│  │  • ESP32-CAM    │                    │  • Real-time  ││
│  │  • BMP280       │                    │    plots     ││
│  │  • MPU-6050     │                    │  • 3D model   ││
│  │  • INA219       │                    │  • Telemetry  ││
│  │  • NEO-6M GPS   │                    │    console    ││
│  │  • LoRa SX1278  │                    │  • Simulation ││
│  │  • MG90S servo  │                    │  • CSV export ││
│  │  • microSD card │                    │  • Command    ││
│  │  • 2S LiPo batt.│                    │    uplink     ││
│  └────────┬────────┘                    └──────────────┘│
│           │                                              │
│           ▼                                              │
│  ┌─────────────────┐                                     │
│  │  3D-PRINTED     │                                     │
│  │  ENCLOSURE      │                                     │
│  │  (67mm × 120mm) │                                     │
│  │                 │                                     │
│  │  • Electronics  │                                     │
│  │    bay (73mm)   │                                     │
│  │  • Bulkhead     │                                     │
│  │  • Parachute    │                                     │
│  │    bay (38mm)   │                                     │
│  └─────────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

1. **Flight System** — two ESP32 microcontrollers, sensors, radio, and servo packed inside the can. This is what flies on the rocket.

2. **3D-Printed Enclosure** — the physical can body designed in OpenSCAD. It holds everything together and separates at apogee to deploy the parachute.

3. **Ground Control Station (CFC)** — a desktop application you run on a laptop. It receives radio data, shows live plots, displays a 3D model of the satellite, and lets you send commands back to the CanSat.

### How does it all work?

1. You **program** both ESP32s with the flight firmware (using the Arduino IDE)
2. You **3D-print** the enclosure parts
3. You **assemble** everything inside the can (sensors, batteries, wiring)
4. You **launch** the CanSat on a rocket
5. During ascent, the flight computer **reads sensors** (altitude, temperature, GPS, orientation) and **transmits** all data via LoRa radio every second
6. Your laptop's **ground station** receives, plots, and logs all data in real time
7. At apogee (~800 m), you send a **command via LoRa** to release the parachute
8. The CanSat **descends safely**, streaming data all the way down

---

## For Aerospace & Software Engineers

### Project Overview

**Al-Idrisi-M1** (named after the 12th-century cartographer Muhammad al-Idrisi) is a CanSat Competition 2026 entry. The design uses a **dual-ESP32 architecture** where one ESP32 (NodeMCU-32S) handles all sensors, radio, GPS, servo, and logging, while a second ESP32-CAM (AI-Thinker) handles only the camera — connected via UART.

This architecture was chosen because the ESP32-CAM's camera parallel bus occupies GPIOs 12–15 and 4–5, which would conflict with dedicated SPI (VSPI: 23/19/18/5) and SD card (GPIO15). Splitting the workload avoids all pin conflicts while allowing the main ESP32 full access to VSPI for the LoRa + SD bus.

### Flight Hardware — Dual ESP32 Architecture

#### Block Diagram

```
                         ┌──────────────────────────────────┐
                         │  2S LiPo 7.4V (1000mAh)          │
                         │  ──→ Pololu 5V 2A Regulator      │
                         │       ──→ 5V rail                │
                         └────────────┬──────────┬───────────┘
                                      │          │
               ┌──────────────────────┼──────────┼───────────────────┐
               │        5V            │    5V    │     5V            │
          ┌────▼────┐          ┌──────▼─────┐   ┌▼──────┐           │
          │  Main   │◄──UART──►│ ESP32-CAM  │   │ MG90S │           │
          │  ESP32  │  GPIO16/ │ AI-Thinker │   │ Servo │           │
          │Dev Board│   17     │  OV2640    │   │GPIO25 │           │
          └┬──┬──┬──┘          └────────────┘   └───────┘           │
           │  │  │                                                    │
      ┌────┘  │  └──────┐                                           │
      │       │         │                                            │
 ┌────▼──┐ ┌──▼──┐ ┌───▼──────┐  ┌────────┐                        │
 │ NEO-6M│ │ I2C │ │ LoRa     │  │microSD │                        │
 │  GPS  │ │ Bus │ │ SX1278   │  │(SPI CS │                        │
 │UART1  │ │21/22│ │433MHz SPI│  │GPIO15) │                        │
 │GPIO13/│ │     │ │CS=GPIO5  │  └────────┘                        │
 │  14   │ │ BMP │ │RST=GPIO2 │                                     │
 └───────┘ │280  │ │DIO0=GPIO4│                                     │
           │ MPU-│ └──────────┘                                     │
           │6050 │                                                  │
           │ INA │                                                  │
           │219  │                                                  │
           └─────┘                                                  │
└───────────────────────────────────────────────────────────────────┘
```

#### Component Details

| Component | Interface | Address / Freq | Purpose |
|---|---|---|---|
| **BMP280** | I2C (0x76) | 100 kHz | Barometric pressure + temperature → altitude via standard atmosphere equation |
| **MPU-6050** | I2C (0x68) | 100 kHz | 6-axis IMU: 3-axis gyroscope (±250°/s) + 3-axis accelerometer (±2g) for orientation and dynamics |
| **INA219** | I2C (0x40) | 100 kHz | 0–26V bus voltage, ±3.2A shunt current monitoring |
| **NEO-6M** | UART1 (GPIO13/14) | 9600 8N1 | GPS position, time, altitude, number of satellites. NMEA $GPGGA/$GNGGA parsed onboard |
| **SX1278** | SPI VSPI (CS=5, RST=2, DIO0=4) | 433 MHz, SF7, BW125kHz, CR4/5, 17dBm | LoRa telemetry downlink (1 Hz CSV) + command uplink receiver |
| **microSD** | SPI VSPI (CS=15, shared MOSI/MISO/SCLK) | — | Flight data CSV logging + JPEG image archival |
| **MG90S** | PWM (GPIO25) | 50 Hz | 180° servo for parachute release mechanism |
| **ESP32-CAM** | UART2 (GPIO16/17) | 115200 baud | OV2640 camera, SVGA (800×600) JPEG capture on command, flash LED on GPIO4 |

#### I2C Bus

All three I2C sensors share the same bus (GPIO21 SDA, GPIO22 SCL). Pull-up resistors to 3.3V (4.7 kΩ typical) are required if not present on breakout boards.

| Device | Address | Conflicts |
|---|---|---|
| BMP280 | 0x76 | Jumper to 0x77 if needed |
| MPU-6050 | 0x68 | AD0 high → 0x69 |
| INA219 | 0x40 | A0/A1 strapping → 0x40–0x4F |

#### UART Configuration

| Port | TX | RX | Baud | Device |
|---|---|---|---|---|
| Serial (UART0) | GPIO1 | GPIO3 | 115200 | USB debug / programming |
| UART1 | GPIO14 | GPIO13 | 9600 | NEO-6M GPS |
| UART2 | GPIO17 | GPIO16 | 115200 | ESP32-CAM |

#### SPI Bus

VSPI is shared between LoRa (CS=5) and SD card (CS=15). The bus runs at ESP32 default SPI clock (~10 MHz). Both devices share MOSI (GPIO23), MISO (GPIO19), and SCLK (GPIO18).

#### Key Design Decision — Dual ESP32

The single ESP32-CAM cannot simultaneously drive:
- OV2640 parallel camera bus (GPIOs: 0, 4, 5, 18, 19, 21, 22, 23, 25, 26, 27, 34, 35, 36, 39)
- And VSPI (GPIO 5, 18, 19, 23) for LoRa + SD

The camera bus overlaps with VSPI on GPIOs 5, 18, 19, 23, and with the servo on GPIO25. Adding an SD card would require GPIO15 (another conflict).

**Solution:** A dedicated main ESP32 (NodeMCU-32S) handles all peripherals; the ESP32-CAM handles only the camera. They communicate over UART2 at 115200 baud with a binary protocol.

### 3D CAD — Parametric CanSat Enclosure

#### Design Philosophy

The enclosure is designed exclusively with **OpenSCAD primitives** (cylinder, difference, hull, rotate_extrude) — no external libraries. Every dimension is parameterised at the top of the file. Resolution is set to `$fn=80` for printed parts.

#### Physical Specifications

| Parameter | Value | Tolerance |
|---|---|---|
| Outer diameter | 67 mm | ±0.2 mm (fits standard soda can launcher) |
| Wall thickness | 3 mm | 2 shells with 0.4 mm nozzle |
| Total height | 120 mm | 3 (cap) + 73 (electronics) + 3 (bulkhead) + 38 (parachute) + 3 (cap) |
| Internal diameter | 61 mm | Accommodates 60 mm PCB trays |
| PCB tray PCD | 52 mm | 4× M2.5 threaded inserts |
| Weight (printed) | ~80 g PETG | 0.15 mm layer height |

#### Height Budget

```
z=117 ┌────────────────────┐  ─── Top cap (3 mm)
       │                    │      M3 eye-bolt holes at x=±15
       │   PARACHUTE BAY    │
z= 79  │   38 mm internal   │      Spring seat ring at z=3
       │                    │      Vent hole at mid-height (0°)
       │                    │      Locking pin at z=2 (225°)
z= 76 ─╊━━━━ BULKHEAD 3mm ━╋───  4× M2.5 at 45°, locking pin 
       │                    │      hole at 225°, 6× vent slots
       │ ELECTRONICS BAY    │
       │   73 mm internal   │
       │                    │
       │ Tray 3 @ z=54      │      LoRa module, SD card
       │ Tray 2 @ z=36      │      Main ESP32, BMP280, MPU-6050
       │ Tray 1 @ z=18      │      ESP32-CAM, INA219, Pololu reg
       │                    │
       │ Battery @ z=0-12   │      2S LiPo 54×30×12 mm
z=  0 ─┼────────────────────┼───
z= -3 ─┴────────────────────┴─── Bottom cap (3 mm)
```

#### Cutout Positions (Electronics Bay)

| Feature | Z position (mm) | Angle (°) | Size | Purpose |
|---|---|---|---|---|
| Access port | 40 | 0 | 16×6 mm (rounded) | USB cable during development |
| Camera lens | 20 | 45 | 10 mm Ø | ESP32-CAM OV2640 lens |
| Servo horn | 53 | 75 | 8 mm Ø | MG90S spline access |
| SMA bulkhead | 63.5 | 135 | 11 mm hex | LoRa antenna connector |
| Slide switch | 9.5 | 180 | 13×4 mm (rounded) | Battery power switch |
| LED indicators | 15, 19 | 180 | 3 mm Ø | Status LEDs |
| Battery straps | 5, 15 | 90/270 | 3 mm Ø | Zip-tie anchor points |

#### Threaded Insert Specifications

| Location | Thread | Hole Ø | PCD | Count |
|---|---|---|---|---|
| PCB trays | M2.5 | 2.7 mm | 52 mm | 4 per tray |
| Bulkhead rim (both tubes) | M2.5 | 2.7 mm | 52 mm | 4 per side |
| Top cap (eye bolt) | M3 | 3.2 mm | 30 mm | 2 |
| Bottom cap (tray mount) | M2.5 | 2.7 mm | 52 mm | 4 |

#### Parachute Deployment Mechanism

```
BEFORE RELEASE:                    AFTER RELEASE:

┌────────────────────┐             ┌────────────────────┐
│ Top cap            │             │ Top cap (on ground)│
│ (tethered)         │             │  + parachute       │
│                    │             │                    │
│ Parachute pack     │  Spring     │ ◄─ Spring pushes   │
│  (compressed)      │  ────►      │     parachute out  │
│                    │             │                    │
│┄┄┄ Spring seat ┄┄┄│             │                    │
│                    │             │                    │
│ Locking pin ──►    │             │ Pin retracted      │
│  (through          │             │  by servo push-rod │
│   bulkhead+wall)   │             │                    │
╞═══ BULKHEAD ═══════╡             ╞═══ BULKHEAD ═══════╡
│ Electronics        │             │ Electronics        │
│  (undisturbed)     │             │  (undisturbed)     │
└────────────────────┘             └────────────────────┘

Mechanism:
1. A compression spring sits on the spring-seat ring at z=79
2. The parachute pack is compressed above the spring
3. A 3.5 mm locking pin passes through the upper tube wall at 
   z=78 (225°) and the bulkhead at the same position
4. The MG90S servo at z=53 (75°) actuates a push-rod or 
   Bowden cable that goes through the bulkhead at 225°
5. At apogee, GCS sends "MEC 1 ON" → servo rotates 180°
   → pin retracts → spring pushes parachute out
```

#### Print Settings (Recommended)

| Setting | Value |
|---|---|
| Material | PETG (preferred) or PLA+ |
| Layer height | 0.15 mm |
| Nozzle | 0.4 mm |
| Perimeters | 3 |
| Top/bottom layers | 4 |
| Infill | 20% gyroid |
| Supports | None (design is self-supporting when printed tube-axis-horizontal) |
| Orientation | Tube axis horizontal on bed (`rotate([0,-90,0])` in source) |
| Bed temp | 70°C PETG, 60°C PLA |
| Extruder temp | 235°C PETG, 210°C PLA |

#### OpenSCAD File Structure

The file `cansat_enclosure.scad` is structured as:

```
User Parameters ──► Derived Constants
       │
       ├── Helpers (cr, tube, rh, rs)
       ├── Modules (bottom_cap, top_cap, lower_tube, upper_tube, 
       │            bulkhead, pcb_tray, standoff, parachute_anchor)
       └── Assembly (positions all modules + transparent placeholders)
```

Key design patterns:
- **`rh(d, z, a)`** — Circular radial hole: cylinder of diameter `d` aligned along +X (via `rotate([0,90,0])`), spanning `tube_od×2` (guarantees wall penetration regardless of diameter), rotated to angle `a` about Z, translated to height `z`
- **`rs(w, h, cr, z, a)`** — Rounded-rectangular radial slot: hull of 8 spheres (4 corners × 2 depths ±tube_od) for guaranteed wall penetration
- **Chamfers**: `rotate_extrude` + `polygon` triangle for 1 mm 45° chamfers on tube edges (avoids `difference`-cancellation bug)

### CFC Software — Ground Control Station

The CFC (CanSat Flight Control) is a **PyQt6 desktop application** with pyqtgraph-based real-time plotting, an OpenGL 3D visualisation, serial/LoRa telemetry receiver, command uplink, simulation engine, and CSV logging.

#### Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              QMainWindow                 │
                    │  (src/ui_layout.py)                     │
                    ├──────────┬──────────┬───────────────────┤
                    │ Left     │ Central  │ Right Dock        │
                    │ Dock     │ Area     │ (320px min)       │
                    │ (240px)  │          │                   │
                    ├──────────┼──────────┤  3D Simulation    │
                    │Resources │ Plot Grid│  (GLViewWidget)   │
                    │ Tree     │ (5 plots)│                   │
                    │          │          │  ┌─────────────┐  │
                    │ Hardware │  Altitude│  │ CanSat body  │  │
                    │ Telemetry│   Voltage│  │ + orientation│  │
                    │ Commands │   Current│  │ + altitude   │  │
                    │          │  Accel(3)│  │ + ground     │  │
                    │          │  Gyro(3) │  │ + launch pad │  │
                    └──────────┴──────────┴───────────────────┘
                    │       Bottom Dock ("Console")            │
                    │  ┌──────────────────┬──────────────────┐ │
                    │  │ Message Console  │ Packet Monitor   │ │
                    │  │                  │ Rcvd / Lost / %  │ │
                    │  └──────────────────┴──────────────────┘ │
                    └──────────────────────────────────────────┘
```

#### Dependencies

| Package | Version | Purpose |
|---|---|---|
| `PyQt6` | ≥6.5 | GUI framework (QMainWindow, docks, signals/slots) |
| `pyqtgraph` | ≥0.13 | Real-time plotting + OpenGL 3D view |
| `pandas` | ≥2.0 | In-memory telemetry storage + CSV export |
| `pyserial` | ≥3.5 | Serial port enumeration (QSerialPortInfo) |
| `qdarkstyle` | ≥3.2 | Dark/light theme switching |
| `PyOpenGL` | ≥3.1 | OpenGL context for 3D visualizer |
| `numpy` | *(bundled with pyqtgraph)* | Mesh math, rotation matrices |

Install: `pip install -r requirements.txt`

#### File Map — `src/`

| File | Lines | Responsibility |
|---|---|---|
| `main.py` | 26 | App entry point, QApplication init, dark theme |
| `ui_layout.py` | 435 | MainWindow: toolbars, docks, wire signals, serial port dialog |
| `telemetry_engine.py` | 123 | QThread: serial I/O, mock generator, CSV parsing, poll timer |
| `telemetry_packet.py` | 84 | TelemetryPacket dataclass (22 fields) + `from_csv()` parser |
| `commands.py` | 37 | CommandBuilder (ST, CAL, SIM, SIMP, MEC, CX) + CommandSender signal |
| `mock_generator.py` | 115 | 4-phase flight profile: ascent (30s→300m), release, descent, landed |
| `simulation_engine.py` | 93 | QThread: pressure CSV reader, 1 Hz SIMP uplink |
| `data_logger.py` | 45 | pandas DataFrame: append, sequence checking, CSV export |
| `plots.py` | 132 | BasePlot + 5 specialised plot widgets (altitude, voltage, current, accel, gyro) |
| `visualizer_3d.py` | 430 | OpenGL 3D: Blender-style camera, CanSat mesh with fins + nose cone, auto-rotation |
| `ui_tree.py` | 68 | QTreeWidget: mission/hardware/telemetry/commands trees |
| `ui_console.py` | 77 | MessageConsole + PacketMonitor (received/lost/success %) |

#### Threading Model

```
 ┌──────────────────────┐
 │  MAIN THREAD         │
 │  (QApplication)      │
 │                      │
 │  • UI updates        │
 │  • Plot data append  │
 │  • 3D repaint        │
 │  • Signal handlers   │
 │  • 30ms refresh timer│
 └────────┬─────────────┘
          │ Signals
          │
 ┌────────▼─────────────┐     ┌──────────────────────────┐
 │  TELEMETRY ENGINE    │     │  SIMULATION ENGINE       │
 │  (QThread)           │     │  (QThread)               │
 │                      │     │                          │
 │  • 50ms poll timer   │     │  • 50ms poll timer        │
 │  • Serial read/write │     │  • CSV pressure loading   │
 │  • Mock generation   │     │  • 1 Hz SIMP emission    │
 │  • CSV parsing       │     │                          │
 │  • Command echo      │     │                          │
 └──────────────────────┘     └──────────────────────────┘
```

Both threads use **QTimers** for polling (not blocking loops), which allows clean start/stop from the main thread without join/detach issues. Cross-thread communication is via **Qt Signals** (thread-safe, queued connections).

- `packet_received(TelemetryPacket)` → UI updates, plots, data logger
- `status_message(str)` → Console log
- `serial_error(str)` → Error handling, disconnection
- `command_to_send(str)` → Serial write on telemetry thread
- `pressure_uplink(float)` → SIMP command to flight computer

#### Mock Telemetry Generator

When no serial hardware is available, the `MockGenerator` produces a realistic 4-phase flight profile:

| Time (s) | Phase | Altitude | State | Mode |
|---|---|---|---|---|
| 0–30 | Ascent | 0 → 300 m (linear) | ASCENT | FLIGHT |
| 30–35 | Apogee | 300 m ±5 | RELEASE | FLIGHT |
| 35–120 | Descent | 300 → 0 m (parabolic) | DESCENT | FLIGHT |
| 120+ | Landed | 0 ±0.5 | LANDED | IDLE |

Voltage decays linearly from 16.8 V at 0.6 mV/s (realistic for 2S LiPo under ~350 mA load). All sensor values include Gaussian noise (±0.5°C, ±10 Pa, ±0.02 V, ±0.01 A, ±2°/s gyro, ±1 m/s² accel).

#### 3D Visualizer

The `BlenderStyleGLViewWidget` (subclass of `GLViewWidget`) implements:

| Interaction | Action |
|---|---|
| MMB drag | Orbit camera |
| Shift + MMB drag | Pan (view-upright) |
| Ctrl + MMB drag | Zoom (via `distance` animation) |
| Scroll wheel | Zoom (animated, 0.999^delta factor) |
| Ctrl + scroll | FOV adjustment |
| MMB double-click | Reset to default view (distance=45, elev=15, azimuth=0) |

**Auto-rotation**: When no telemetry has arrived for 2+ seconds, the CanSat model slowly spins (0.5°/tick at 33 ms = ~15°/s) around the Y axis. Real orientation data (roll/pitch/yaw from MPU-6050) immediately suppresses auto-spin.

The 3D scene includes:
- Checkerboard ground plane (80×80 units at z=0)
- Launch pad (3-cylinder stage with green inner ring)
- CanSat body (cylinder mesh, 0.35 radius × 0.80 height, blue)
- Nose cone (red cone, 0.35 radius × 0.35 height)
- 4 tail fins (red, 0.4 span × 0.25 length)
- 2 white stripes (decorative rings)
- Vertical reference line (altitude indicator, translucent blue)
- Axis indicator (3-colour, in corner)

The altitude is scaled by `ALT_SCALE = 10` (1 unit = 10 m real altitude) to keep the model visible within the view frustum.

#### Telemetry Protocol — 22-field CSV

```
TEAM_ID, MISSION_TIME, PACKET_COUNT, MODE, STATE,
ALTITUDE, TEMPERATURE, PRESSURE, VOLTAGE, CURRENT,
GYRO_R, GYRO_P, GYRO_Y, ACCEL_R, ACCEL_P, ACCEL_Y,
GPS_TIME, GPS_ALTITUDE, GPS_LATITUDE, GPS_LONGITUDE,
GPS_SATS, CMD_ECHO
```

Transmitted via LoRa at 1 Hz (every 1000 ms, not polling-loop-gated to avoid drift). The main ESP32 formats the line with `snprintf` and sends it via `LoRa.beginPacket()` / `LoRa.print()` / `LoRa.endPacket()`.

#### Command Protocol

Commands are sent **from GCS → Flight Computer** via LoRa (or serial during testing).

```
CMD,<TEAM_ID>,<ACTION>[,<PARAMETER>]
```

| Command | Example | Action |
|---|---|---|
| ST | `CMD,1234,ST,3600` | Start mission; set mission_time to 3600 s; enter FLIGHT/ASCENT |
| CAL | `CMD,1234,CAL` | Zero IMU bias (gyro/accel) + altimeter |
| SIM ENABLE | `CMD,1234,SIM,ENABLE` | Enter simulation mode (accept SIMP overrides) |
| SIMP | `CMD,1234,SIMP,95000` | Override pressure sensor with 95000 Pa |
| MEC | `CMD,1234,MEC,1,ON` | Set servo to 180° (parachute release) |
| CX | `CMD,1234,CX,ON` | Request camera capture from ESP32-CAM |

#### Simulation Engine

The `SimulationEngine` QThread loads a CSV file with `TIME,PRESSURE` columns and uplinks pressure values at 1 Hz via SIMP commands. This simulates a realistic pressure profile during flight, allowing full GCS testing without a real CanSat or rocket.

The sample file `sample_pressure.csv` contains a 120-second profile: 30 s ascent (1013.25 → 977.00 hPa), 5 s apogee, 55 s descent, 30 s ground.

#### Data Logging

All telemetry is stored in a **pandas DataFrame** (max 600 rows rolling window) and can be exported to CSV via the Export button (`_on_export`). The `DataLogger` tracks packet sequence numbers and reports lost packets (gaps in `PACKET_COUNT`).

### Flight Firmware — Main ESP32

**File:** `flight/main_esp32/main_esp32.ino` (592 lines)

#### Initialisation Sequence

```
1. Serial.begin(115200)               // Debug output
2. Wire.begin(21, 22)                 // I2C at 100 kHz
3. BMP280.begin()                     // Read calib, set normal mode
4. MPU6050.begin()                    // Wake from sleep, set ±250°/s, ±2g
5. INA219.begin()                     // Config: 32V, 3.2A range
6. gps_ser.begin(9600, SERIAL_8N1, 13, 14)
7. cam_ser.begin(115200, SERIAL_8N1, 16, 17)
8. LoRa.setPins(5, 2, 4)             // CS, RST, DIO0
9. LoRa.begin(433E6)                  // SF7, BW125kHz, CR4/5, 17dBm
10. servo.attach(25); servo.write(0)  // MG90S: 0° = closed
11. SD.begin(15)                      // Create /flight/ dir, open CSV
```

#### Main Loop (1 Hz)

```
timer ≥ 1000ms?
├── Read BMP280 → temperature, pressure
│   └── If SIM mode: override pressure from SIMP command
│   └── altitude = 44330 × (1 - (p/p₀)^(1/5.255))
├── Read MPU-6050 → accel_r/p/y, gyro_r/p/y
│   └── Subtract calibration bias
├── Read INA219 → voltage, current
├── Flight state machine:
│   LAUNCH_WAIT + alt ≥ 10m → ASCENT + FLIGHT
├── Format 22-field CSV line
├── LoRa.beginPacket → LoRa.print → LoRa.endPacket
├── Append to SD CSV file
├── Serial.println (debug)
└── process_cam_uart()     // Check for JPEG from ESP32-CAM
```

#### Sensor Drivers (all inline, no libraries)

All three I2C sensor drivers are implemented **from scratch** using `Wire` — no Adafruit or SparkFun libraries. This keeps the firmware self-contained and avoids library version conflicts.

- **BMP280**: Full compensation from factory calibration registers (0x88–0x9F). 20-bit raw pressure/temperature → 32-bit compensated values per Bosch datasheet.
- **MPU-6050**: Direct register reads (0x3B–0x44). FIFO not used (polled reads at 1 Hz). Raw ±2g / ±250°/s.
- **INA219**: 12-bit shunt + bus voltage reads. Shunt voltage → current via 0.1 Ω sense resistor (0.1 mA/LSB).

#### GPS NMEA Parser

Parses `$GPGGA` and `$GNGGA` sentences (up to 256 bytes buffered). Extracts:
- Time (HH:MM:SS from UTC)
- Latitude/Longitude (DDMM.MMMM → DD.DDDDDD)
- Number of satellites
- GPS altitude

DM.MMMM → decimal conversion:
```
lat_dec = floor(raw/100) + (raw - floor(raw/100)*100) / 60
```

#### Image Reception State Machine

Handles the binary protocol from ESP32-CAM (`0xAA 0xBB <4-byte length> <JPEG data> DONE\r\n`). Images are saved to `/flight/img_<timestamp>.jpg` on the microSD card. Buffer: 60 kB (max SVGA JPEG fits within ~50 kB).

```
IMG_HDR1 → 0xAA → IMG_HDR2 → 0xBB → IMG_LEN → (4 bytes) → IMG_DATA → (len bytes) → save to SD → IMG_IDLE
     │          │          │
     └─ no ─────┴─ no ─────┴─ no ────→ IMG_HDR1 (reset)
```

### Flight Firmware — ESP32-CAM Coprocessor

**File:** `flight/esp32_cam/esp32_cam.ino` (123 lines)

#### UART Protocol

| Direction | Message | Response |
|---|---|---|
| Main → CAM | `CX ON\r\n` | `0xAA 0xBB <len:4> <JPEG> DONE\r\n` |
| Main → CAM | `CX OFF\r\n` | `OK\r\n` |

#### Camera Configuration

- **Resolution:** SVGA (800×600)
- **Format:** JPEG
- **Quality:** 12 (good balance of size/clarity)
- **PSRAM:** Required (AI-Thinker board has 4 MB PSRAM)
- **Clock:** XCLK at 20 MHz
- **Brown-out:** Disabled during JPEG transmission (high current draw)

#### Power States

| State | Camera Power | Current Draw |
|---|---|---|
| Idle (CX OFF) | Deinitialised via `esp_camera_deinit()` | ~20 mA |
| Capture (CX ON) | Active via `esp_camera_init()` | ~180 mA |

The flash LED on GPIO4 is illuminated during capture for 200 ms.

### Power Budget

| Component | Idle (mA) | Active (mA) | Notes |
|---|---|---|---|
| Main ESP32 | 50 | 80 | Wi-Fi off, LoRa + SD active |
| ESP32-CAM | 20 | 180 | Camera deinit'd / active + capture |
| LoRa SX1278 | 0.1 | 30 | LowPower idle / TX 17dBm |
| NEO-6M GPS | 45 | 45 | Always on, continuous fix |
| MG90S Servo | 5 | 250 (stalled) | Idle 0°, release 180° |
| 3× I2C sensors | 2 | 5 | BMP280+MPU6050+INA219 |
| **Total** | **~120 mA** | **~590 mA** | Peak with camera + servo |

A **2S 1000 mAh LiPo** provides ~1.7 hours endurance (at average 350 mA). The Pololu 5V 2A regulator handles all loads with margin.

### Build Guide

#### Step 1: 3D Printing

1. Install OpenSCAD from openscad.org
2. Open `C:\Users\El4v\Music\cansat_enclosure.scad`
3. Adjust parameters at top of file if needed (diameters, heights)
4. Press F6 to render (may take 30–60 seconds)
5. Press F7 to export STL
6. Slice in PrusaSlicer / Cura / OrcaSlicer with settings above
7. Print each part: bottom cap, lower tube, upper tube, bulkhead, 3× PCB trays, 12× standoffs, top cap
8. Tap M2.5 holes with M2.5 tap; insert heat-set threaded inserts where needed

#### Step 2: Program ESP32-CAM

1. Connect ESP32-CAM to USB-UART adapter (GPIO0→GND for flash)
2. Open `flight/esp32_cam/esp32_cam.ino` in Arduino IDE
3. Board: `AI-Thinker ESP32-CAM`, Partition: `Huge APP (3MB No OTA)`, PSRAM: Enabled
4. Upload at 115200 baud
5. Remove GPIO0 jumper, press RST

#### Step 3: Program Main ESP32

1. Connect NodeMCU-32S via USB
2. Open `flight/main_esp32/main_esp32.ino` in Arduino IDE
3. Board: `ESP32 Dev Module`, Partition: `Default 4MB with spiffs`
4. Upload at 921600 baud
5. Open Serial Monitor at 115200 baud — verify "BMP280 OK", "MPU6050 OK", "LoRa OK", etc.

#### Step 4: Assemble Electronics

Refer to wiring tables above. Assembly order:
1. Install threaded inserts in 3D-printed parts
2. Mount standoffs + PCB trays inside lower tube
3. Populate components per layout table:
   - Battery floor: 2S LiPo + switch + LEDs (zip-tie through strap holes)
   - Tray 1: ESP32-CAM + INA219 + Pololu regulator
   - Tray 2: Main ESP32 + BMP280 + MPU-6050
   - Tray 3: LoRa module + SD card module
4. Wire all power + I2C + SPI + UART buses
5. Fit bulkhead + upper tube with spring + parachute pack
6. Locking pin through 225° holes (bulkhead + upper tube wall)
7. Attach servo push-rod to locking pin
8. Close with top cap (eye-bolt through M3 holes, shock cord to parachute anchor)
9. Calibrate M2.5 rim screws to hold bulkhead securely

#### Step 5: Install & Run GCS

```bash
cd al-idrisi-m1
pip install -r requirements.txt
python main.py
```

Boot sequence:
1. Window appears with dark theme, 3D dock on right
2. Click **Mock OFF** → becomes **Mock ON** → telemetry starts
3. Plots populate with mock data, 3D model spins (auto-rotation)
4. Click **Connect** → select COM port → real telemetry from flight computer
5. Click **ST** → sends mission start time → flight enters ASCENT mode
6. Click **CAL** → calibrates IMU + altimeter bias
7. Click **SIM** → load pressure CSV → starts simulation mode
8. Click **MEC** → sends servo release command
9. Click **Export CSV** → save flight data for post-analysis

### Competition Workflow

```
PRE-LAUNCH:
1. Power on CanSat → mode = LAUNCH_WAIT
2. Connect GCS → verify telemetry (altitude ~0 m, voltage >7.0 V, GPS fix)
3. Click CAL → capture sensor biases
4. Wait for LCO (Launch Control Officer) countdown

LAUNCH:
5. Rocket lifts off; CanSat accelerates
6. At 10 m altitude → mode auto-switches to ASCENT + FLIGHT
7. GCS plots altitude in real time, 3D model rises above ground

APOGEE (≈800 m, ~30 s after launch):
8. Judge provides pressure CSV for SIMP simulation OR
   Real flight: click MEC 1 ON → servo releases parachute

DESCENT:
9. Parachute deploys, descent rate ≈10 m/s
10. GCS tracks GPS coordinates, 3D model descends
11. On-ground recovery team follows GPS to landing site

POST-FLIGHT:
12. Export CSV → submit to competition judges
13. Retrieve SD card for camera images
14. Print flight log from GCS console
```

---

## Repository Structure

```
al-idrisi-m1/
├── main.py                        # GCS application entry point
├── requirements.txt               # Python dependencies
├── sample_pressure.csv            # 120-second simulation pressure profile
├── README.md                      # This file
├── C:\Users\El4v\Music\cansat_enclosure.scad   # OpenSCAD enclosure
├── flight/
│   ├── README.md                  # Flight system build guide
│   ├── main_esp32/
│   │   └── main_esp32.ino         # Main flight computer firmware
│   └── esp32_cam/
│       └── esp32_cam.ino          # Camera coprocessor firmware
└── src/
    ├── __init__.py
    ├── main.py                    # (re-exported by root main.py)
    ├── ui_layout.py               # MainWindow, docks, toolbars
    ├── telemetry_engine.py         # Serial/mock thread
    ├── telemetry_packet.py         # 22-field dataclass + CSV parser
    ├── commands.py                 # CommandBuilder + CommandSender
    ├── mock_generator.py           # 4-phase mock flight profile
    ├── simulation_engine.py        # Pressure CSV simulation thread
    ├── data_logger.py              # pandas DataFrame logger + export
    ├── plots.py                    # 5 real-time pyqtgraph plots
    ├── visualizer_3d.py            # OpenGL CanSat + auto-rotation
    ├── ui_tree.py                  # Resources QTreeWidget
    └── ui_console.py               # Console + packet monitor
```

---

## License

Educational / competition use. No warranty expressed or implied.
