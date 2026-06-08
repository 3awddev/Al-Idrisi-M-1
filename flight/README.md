# CanSat Flight System — ESP32 Dual-Processor

## Architecture

```
                      ┌─────────────────────────────────┐
  4×18650 (4S) ──→    │  Pololu 5V 2A Regulator         │
  12–16.8V             │  (4.5–28V input → 5V output)    │
                      └──────────┬──────────────────────┘
                                 │ 5V rail
              ┌──────────────────┼──────────────────┐
              │                  │                  │
        ┌─────▼──────┐    ┌─────▼──────┐     ┌─────▼──────┐
        │  Main ESP32 │    │ ESP32-CAM  │     │   Servo    │
        │ (DevKitC /  │◄──►│ (AI-Thinker)│     │   MG90S    │
        │  NodeMCU)   │UART│  OV2640    │     │  GPIO25    │
        └──┬──┬──┬──┬─┘    └────────────┘     └────────────┘
           │  │  │  │
      ┌────┘  │  │  └──────┐
      │       │  │         │
 ┌────▼──┐ ┌──▼──▼──┐ ┌───▼────┐  ┌───────────┐
 │  GPS  │ │ I2C Bus│ │  LoRa  │  │  microSD  │
 │ NEO-6M│ │GPIO21/22│ │SX1278  │  │  (SPI CS: │
 │UART1  │ │        │ │SPI VSPI│  │   GPIO15) │
 │GPIO13/│ │ BMP280 │ │GPIO5 CS│  └───────────┘
 │14     │ │ MPU6050│ │GPIO4   │
 └───────┘ │ INA219 │ │DIO0    │
           └────────┘ │GPIO2   │
                      │RST     │
                      └────────┘
```

## Bill of Materials

| Component | Qty | Purpose |
|---|---|---|
| ESP32 Dev Board (NodeMCU-32S / ESP32-DevKitC) | 1 | Main flight computer |
| AI-Thinker ESP32-CAM (OV2640) | 1 | Camera coprocessor |
| BMP280 | 1 | Temperature & pressure sensor (I2C) |
| MPU-6050 | 1 | 6-axis IMU (I2C) |
| INA219 | 1 | Voltage & current sensor (I2C) |
| NEO-6M GPS Module | 1 | GPS receiver (UART) |
| LoRa SX1278 433MHz Module | 1 | Telemetry radio (SPI) |
| MG90S Micro Servo | 1 | Canopy release mechanism |
| 4×18650 Lithium-Ion Cells (4S) | 4 | Battery: 14.8V nom, 16.8V full, 12.0V cut-off |
| Pololu 5V 2A Step-Down Regulator | 1 | Powers both ESP32 boards from 4S battery |
| microSD Card (16GB+) | 1 | Flight data & image logging |
| ¼-wave 433 MHz Antenna | 1 | For LoRa module |
| Passive buzzer (optional) | 1 | Audio feedback |

## Wiring

### Main ESP32 Pinout

| Main ESP32 GPIO | Connection | Peripheral |
|---|---|---|
| GPIO21 (SDA) | SDA bus | BMP280 SDA, MPU-6050 SDA, INA219 SDA |
| GPIO22 (SCL) | SCL bus | BMP280 SCL, MPU-6050 SCL, INA219 SCL |
| GPIO23 (MOSI) | VSPI MOSI | SX1278 MOSI, SD MOSI |
| GPIO19 (MISO) | VSPI MISO | SX1278 MISO, SD MISO |
| GPIO18 (SCLK) | VSPI SCLK | SX1278 SCLK, SD SCLK |
| GPIO5 (CS) | SPI CS | SX1278 NSS |
| GPIO15 (CS) | SPI CS | microSD card CS |
| GPIO4 | DIO0 | SX1278 DIO0 (interrupt) |
| GPIO2 | RST | SX1278 Reset |
| GPIO13 (RX1) | UART1 RX | NEO-6M GPS TX (yellow) |
| GPIO14 (TX1) | UART1 TX | NEO-6M GPS RX (green) |
| GPIO16 (RX2) | UART2 RX | ESP32-CAM TX (GPIO1) |
| GPIO17 (TX2) | UART2 TX | ESP32-CAM RX (GPIO3) |
| GPIO25 | PWM | MG90S servo signal (orange) |
| 5V/VIN | Power | Pololu 5V output |
| GND | Ground | Common ground rail |

### ESP32-CAM Pinout

| ESP32-CAM GPIO | Connection | Peripheral |
|---|---|---|
| GPIO1 (TX0) | UART TX | Main ESP32 GPIO16 (RX2) |
| GPIO3 (RX0) | UART RX | Main ESP32 GPIO17 (TX2) |
| GPIO4 | Output | Built-in flash LED |
| 5V | Power | Pololu 5V output |
| GND | Ground | Common ground rail |

### I2C Bus (shared, addresses)

| Device | Address | Notes |
|---|---|---|
| BMP280 | 0x76 | Alt jumper for 0x77 |
| MPU-6050 | 0x68 | AD0 low = 0x68 |
| INA219 | 0x40 | A0/A1 GND = 0x40 |

### Power Distribution

```
4S 18650 (12–16.8V) ──→ Pololu VIN
                           Pololu VOUT (5V) ──→ Main ESP32 5V/VIN
                                              ──→ ESP32-CAM 5V pin
                                              ──→ Servo VCC (5V)
                                              ──→ NEO-6M VCC (3.3V via regulator)
                                              ──→ LoRa VCC (3.3V via regulator)
                                              ──→ BMP280, MPU-6050, INA219 VCC (3.3V)
```

**Note:** All 3.3V sensors/modules share the ESP32's 3.3V rail (the on-board regulator supplies ~150mA, sufficient for these low-power sensors). For LoRa + GPS, use a separate 3.3V regulator (AMS1117-3.3) if total 3.3V draw exceeds 150mA.

### Power Budget

| Component | Current (mA) |
|---|---|
| Main ESP32 (average) | ~80 |
| ESP32-CAM (camera on, no flash) | ~180 |
| LoRa SX1278 (TX) | ~30 |
| NEO-6M GPS | ~45 |
| MG90S servo (idle) | ~10 |
| MG90S servo (stalled) | ~250 |
| BMP280 + MPU-6050 + INA219 | ~5 |
| **Total (typical)** | **~350 mA** |
| **Total (peak, servo+LoRa+camera)** | **~800 mA** |

Pololu 5V 2A rating covers all scenarios.

## Programming

### Software Dependencies

**Arduino IDE** (or PlatformIO) with ESP32 board support:
- Board URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`

**Arduino Libraries:**
- `LoRa` by Sandeep Mistry (for SX1278)
- `ESP32Servo` by Kevin Harrington
- Built-in: `SPI`, `Wire`, `SD`, `HardwareSerial`

### Main ESP32

1. Open `flight/main_esp32/main_esp32.ino` in Arduino IDE
2. Board: `ESP32 Dev Module` (or your specific dev board)
3. Flash Size: `4MB`
4. Partition Scheme: `Default 4MB with spiffs`
5. Upload Speed: `921600`
6. Select correct COM port
7. **Do not connect ESP32-CAM's UART** during programming (conflicts with serial upload)
8. Click Upload

### ESP32-CAM

1. Open `flight/esp32_cam/esp32_cam.ino` in Arduino IDE
2. Board: `AI-Thinker ESP32-CAM`
3. Flash Size: `4MB`
4. Partition Scheme: `Huge APP (3MB No OTA)`
5. Upload Speed: `115200`
6. **GPIO0 must be LOW during upload** (hold boot button or connect GPIO0 to GND)
7. Click Upload, then press ESP32-CAM RST
8. After flashing, set GPIO0 HIGH and RST

### First-time setup

1. Program ESP32-CAM first (standalone, via its UART-to-USB adapter)
2. Program Main ESP32 (standalone via its USB port)
3. Wire everything together
4. Power on — both ESP32s boot autonomously
5. Open Main ESP32 Serial Monitor (115200 baud) to see boot messages

## Telemetry Protocol

22-field CSV, transmitted via LoRa at 1 Hz:

```
TEAM_ID,MISSION_TIME,PACKET_COUNT,MODE,STATE,
ALTITUDE,TEMPERATURE,PRESSURE,VOLTAGE,CURRENT,
GYRO_R,GYRO_P,GYRO_Y,ACCEL_R,ACCEL_P,ACCEL_Y,
GPS_TIME,GPS_ALTITUDE,GPS_LATITUDE,GPS_LONGITUDE,
GPS_SATS,CMD_ECHO
```

Example:
```
1234,3600,1,FLIGHT,ASCENT,150.25,18.5,101325,16.5,0.2,0.1,-0.2,0.3,0.0,0.0,9.81,12:30:00,152.3,40.4432,-79.9428,10,
```

## Command Protocol

Commands received via LoRa, format:
```
CMD,<TEAM_ID>,<ACTION>[,<PARAM>]
```

| Command | Parameters | Description |
|---|---|---|
| `ST` | `<time_s>` | Start mission, set time, enter FLIGHT/ASCENT |
| `CAL` | *(none)* | Calibrate IMU + altimeter bias |
| `SIM ENABLE` | *(none)* | Enter simulation mode |
| `SIMP` | `<pressure>` | Override pressure sensor (Pa) |
| `MEC` | `<device>,ON/OFF` | Mechanism control (servo 0°/180°) |
| `CX` | `ON` or `OFF` | Camera capture / standby |

## Camera Protocol (Main ESP32 ↔ ESP32-CAM)

**Main** → **CAM**: `CX ON\r\n` or `CX OFF\r\n`

**CAM** → **Main** (CX ON):
```
0xAA 0xBB <uint32_t length (big-endian)> <JPEG bytes> "DONE\r\n"
```

**CAM** → **Main** (CX OFF):
```
"OK\r\n"
```

Images saved to `/flight/img_<timestamp>.jpg` on microSD.

## State Machine

```
LAUNCH_WAIT ──(altitude ≥ 10m)──→ ASCENT ──(MEC ON)──→ RELEASE ──(descent)──→ DESCENT ──(ground)──→ LANDED
```

## GPIO Reference Summary

### Main ESP32

| Pin | Function | Notes |
|---|---|---|
| 21 | I2C SDA | BMP280, MPU6050, INA219 |
| 22 | I2C SCL | |
| 23 | SPI MOSI | LoRa + SD (shared bus) |
| 19 | SPI MISO | |
| 18 | SPI SCLK | |
| 5 | LoRa CS | |
| 15 | SD CS | |
| 4 | LoRa DIO0 | RxDone interrupt |
| 2 | LoRa RST | |
| 13 | GPS RX | UART1 from GPS TX |
| 14 | GPS TX | UART1 to GPS RX |
| 16 | CAM RX | UART2 from ESP32-CAM TX |
| 17 | CAM TX | UART2 to ESP32-CAM RX |
| 25 | Servo PWM | MG90S signal wire |

### ESP32-CAM

| Pin | Function | Notes |
|---|---|---|
| 1 | TX0 | UART to Main ESP32 RX2 |
| 3 | RX0 | UART from Main ESP32 TX2 |
| 4 | Flash LED | Built-in flash, optional |

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| No LoRa TX | SX1278 not initialized | Check SPI wiring, 3.3V, antenna |
| No GPS fix | UART baud mismatch | NEO-6M defaults to 9600 8N1 |
| ESP32-CAM no response | UART crossed | Swap TX/RX between boards |
| SD card fails | CS pin wrong | Check SPI CS assignment |
| Brownout/reset | 5V rail sagging | Check Pololu output, battery voltage >12V |
| Camera no image | PSRAM not enabled | Enable PSRAM in Arduino IDE tools menu |
| Serial upload fails | UART conflict | Disconnect ESP32-CAM TX/RX during upload |
