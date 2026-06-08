/*
  CanSat Main Flight Computer — ESP32
  Sensors:  BMP280, MPU-6050, INA219 (I2C)
  Radio:    SX1278 LoRa (SPI)
  GPS:      NEO-6M (UART1)
  Camera:   ESP32-CAM (UART2)
  Servo:    MG90S (PWM)
  Logging:  microSD (SPI)
*/

#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <LoRa.h>
#include <ESP32Servo.h>

// ── Pin mapping ────────────────────────────────────────────────────────
// I2C:           GPIO21(SDA), GPIO22(SCL)
// VSPI (LoRa):   GPIO23(MOSI), GPIO19(MISO), GPIO18(SCLK), GPIO5(CS)
// VSPI (SD):     share MOSI/MISO/SCLK, GPIO15(SD_CS)
#define LORA_CS   5
#define LORA_RST  2
#define LORA_DIO0 4
#define SD_CS     15
#define SERVO_PIN 25
#define GPS_RX    13  // UART1 RX
#define GPS_TX    14  // UART1 TX
#define CAM_RX    16  // UART2 RX
#define CAM_TX    17  // UART2 TX

// ── Constants ─────────────────────────────────────────────────────────
#define TEAM_ID      1234
#define GPS_BAUD     9600
#define CAM_BAUD     115200
#define LORA_FREQ    433E6
#define TLM_INTERVAL 1000
#define LOG_DIR      "/flight"

static const char TLM_HEADER[] PROGMEM =
    "TEAM_ID,MISSION_TIME,PACKET_COUNT,MODE,STATE,"
    "ALTITUDE,TEMPERATURE,PRESSURE,VOLTAGE,CURRENT,"
    "GYRO_R,GYRO_P,GYRO_Y,ACCEL_R,ACCEL_P,ACCEL_Y,"
    "GPS_TIME,GPS_ALTITUDE,GPS_LATITUDE,GPS_LONGITUDE,"
    "GPS_SATS,CMD_ECHO";

// ── I2C addresses ─────────────────────────────────────────────────────
#define BMP280_ADDR   0x76
#define MPU6050_ADDR  0x68
#define INA219_ADDR   0x40

// ── Flight state ──────────────────────────────────────────────────────
struct FlightState {
    uint32_t mission_time = 0;
    uint32_t packet_count = 0;
    char mode[16] = "NONE";
    char state_str[16] = "LAUNCH_WAIT";
    float altitude = 0.0f;
    float temperature = 20.0f;
    float pressure = 101325.0f;
    float voltage = 16.8f;
    float current = 0.0f;
    float gyro_r = 0.0f, gyro_p = 0.0f, gyro_y = 0.0f;
    float accel_r = 0.0f, accel_p = 0.0f, accel_y = 9.81f;
    char gps_time[16] = "00:00:00";
    float gps_altitude = 0.0f;
    float gps_latitude = 0.0f;
    float gps_longitude = 0.0f;
    int gps_sats = 0;
    char cmd_echo[128] = "";
    bool sim_enabled = false;
    float sim_pressure = 0.0f;
    float cal_bias_alt = 0.0f;
    float cal_bias_accel[3] = {0, 0, 0};
    float cal_bias_gyro[3] = {0, 0, 0};
    bool img_captured = false;
    bool running = true;
};

static FlightState st;
static float base_pressure = 101325.0f;
static Servo servo;
static File csv_file;

// ── Image receive state machine ───────────────────────────────────────
enum ImgState { IMG_IDLE, IMG_HDR1, IMG_HDR2, IMG_LEN, IMG_DATA };
static ImgState img_state = IMG_IDLE;
static uint32_t img_len = 0, img_received = 0;
static int img_len_cnt = 0;
static uint8_t img_buf[60000];
static bool receiving_img = false;

// ── BMP280 driver ────────────────────────────────────────────────────
class BMP280 {
    int16_t dig_T1, dig_T2, dig_T3, dig_P1, dig_P2, dig_P3, dig_P4,
            dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
public:
    bool begin() {
        Wire.beginTransmission(BMP280_ADDR);
        if (Wire.endTransmission() != 0) return false;
        uint8_t id = read_reg(0xD0);
        if (id != 0x58) return false;
        read_calib();
        write_reg(0xF4, 0x27);   // ctrl: normal, oversample x1
        write_reg(0xF5, 0xA0);   // config: filter off
        return true;
    }

    void read(float *temp, float *pres) {
        uint8_t d[6];
        Wire.beginTransmission(BMP280_ADDR);
        Wire.write(0xF7);
        Wire.endTransmission();
        Wire.requestFrom(BMP280_ADDR, 6);
        for (int i = 0; i < 6; i++) d[i] = Wire.read();

        int32_t raw_p = ((int32_t)d[0] << 12) | ((int32_t)d[1] << 4) | (d[2] >> 4);
        int32_t raw_t = ((int32_t)d[3] << 12) | ((int32_t)d[4] << 4) | (d[5] >> 4);

        int32_t v1 = (((raw_t >> 3) - ((int32_t)dig_T1 << 1)) * (int32_t)dig_T2) >> 11;
        int32_t v2 = (((((raw_t >> 4) - (int32_t)dig_T1) * ((raw_t >> 4) - (int32_t)dig_T1)) >> 12) * (int32_t)dig_T3) >> 14;
        int32_t t_fine = v1 + v2;
        *temp = (t_fine * 5 + 128) >> 8;
        *temp /= 100.0f;

        v1 = t_fine - 128000;
        v2 = v1 * v1 * (int32_t)dig_P6 >> 6;
        v2 += v1 * (int32_t)dig_P5 << 1;
        v2 = (v2 >> 2) + ((int32_t)dig_P4 << 16);
        v1 = (((int32_t)dig_P3 * ((v1 * v1) >> 12)) >> 11) + ((int32_t)dig_P2 * v1 >> 1);
        v1 >>= 15;

        if (v1 == 0) { *pres = 0; return; }
        uint32_t p = (((1048576 - raw_p) - (v2 >> 12))) * 3125;
        if (p < 0x80000000) p = (p << 1) / (uint32_t)v1;
        else p = (p / (uint32_t)v1) * 2;
        v1 = ((int32_t)dig_P9 * ((int32_t)((p >> 3) * (p >> 3)) >> 13)) >> 12;
        v2 = ((int32_t)(p >> 2) * (int32_t)dig_P8) >> 13;
        *pres = (float)(p + ((v1 + v2 + (int32_t)dig_P7) >> 4));
    }

private:
    void read_calib() {
        Wire.beginTransmission(BMP280_ADDR);
        Wire.write(0x88);
        Wire.endTransmission();
        Wire.requestFrom(BMP280_ADDR, 24);
        uint8_t r[24];
        for (int i = 0; i < 24; i++) r[i] = Wire.read();
        dig_T1 = r[0] | (r[1] << 8);
        dig_T2 = (int16_t)(r[2] | (r[3] << 8));
        dig_T3 = (int16_t)(r[4] | (r[5] << 8));
        dig_P1 = r[6] | (r[7] << 8);
        dig_P2 = (int16_t)(r[8] | (r[9] << 8));
        dig_P3 = (int16_t)(r[10] | (r[11] << 8));
        dig_P4 = (int16_t)(r[12] | (r[13] << 8));
        dig_P5 = (int16_t)(r[14] | (r[15] << 8));
        dig_P6 = (int16_t)(r[16] | (r[17] << 8));
        dig_P7 = (int16_t)(r[18] | (r[19] << 8));
        dig_P8 = (int16_t)(r[20] | (r[21] << 8));
        dig_P9 = (int16_t)(r[22] | (r[23] << 8));
    }

    uint8_t read_reg(uint8_t reg) {
        Wire.beginTransmission(BMP280_ADDR);
        Wire.write(reg);
        Wire.endTransmission();
        Wire.requestFrom(BMP280_ADDR, 1);
        return Wire.read();
    }

    void write_reg(uint8_t reg, uint8_t val) {
        Wire.beginTransmission(BMP280_ADDR);
        Wire.write(reg);
        Wire.write(val);
        Wire.endTransmission();
    }
};

// ── MPU-6050 driver ──────────────────────────────────────────────────
class MPU6050 {
public:
    bool begin() {
        Wire.beginTransmission(MPU6050_ADDR);
        if (Wire.endTransmission() != 0) return false;
        write_reg(0x6B, 0x00);
        delay(100);
        write_reg(0x19, 0x07);
        write_reg(0x1A, 0x00);
        write_reg(0x1B, 0x00);
        write_reg(0x1C, 0x00);
        return true;
    }

    void read(float *ax, float *ay, float *az, float *gx, float *gy, float *gz) {
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(0x3B);
        Wire.endTransmission();
        Wire.requestFrom(MPU6050_ADDR, 14);
        int16_t raw[7];
        for (int i = 0; i < 7; i++) raw[i] = (Wire.read() << 8) | Wire.read();
        *ax = raw[0] / 16384.0f;
        *ay = raw[1] / 16384.0f;
        *az = raw[2] / 16384.0f;
        *gx = raw[4] / 131.0f;
        *gy = raw[5] / 131.0f;
        *gz = raw[6] / 131.0f;
    }

private:
    void write_reg(uint8_t reg, uint8_t val) {
        Wire.beginTransmission(MPU6050_ADDR);
        Wire.write(reg);
        Wire.write(val);
        Wire.endTransmission();
    }
};

// ── INA219 driver ───────────────────────────────────────────────────
class INA219 {
public:
    bool begin() {
        Wire.beginTransmission(INA219_ADDR);
        if (Wire.endTransmission() != 0) return false;
        write_reg(0x00, 0x399F);
        write_reg(0x05, 4096);
        return true;
    }

    void read(float *voltage, float *current) {
        uint16_t raw_bus = read_reg(0x02);
        *voltage = ((raw_bus >> 3) * 4) / 1000.0f;
        int16_t raw_shunt = (int16_t)read_reg(0x01);
        *current = raw_shunt * 0.0001f;
        if (*current < 0) *current = 0;
    }

private:
    uint16_t read_reg(uint8_t reg) {
        Wire.beginTransmission(INA219_ADDR);
        Wire.write(reg);
        Wire.endTransmission();
        Wire.requestFrom(INA219_ADDR, 2);
        return (Wire.read() << 8) | Wire.read();
    }

    void write_reg(uint8_t reg, uint16_t val) {
        Wire.beginTransmission(INA219_ADDR);
        Wire.write(reg);
        Wire.write(val >> 8);
        Wire.write(val & 0xFF);
        Wire.endTransmission();
    }
};

// ── Globals ─────────────────────────────────────────────────────────
static BMP280 bmp;
static MPU6050 mpu;
static INA219 ina;
static bool bmp_ok = false, mpu_ok = false, ina_ok = false;
static HardwareSerial gps_ser(1);
static HardwareSerial cam_ser(2);

// ── NMEA parser ─────────────────────────────────────────────────────
void parse_nmea(const char *sentence) {
    if (sentence[0] != '$') return;
    if (!(strstr(sentence, "$GPGGA") || strstr(sentence, "$GNGGA"))) return;

    char buf[96];
    strncpy(buf, sentence, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';

    char *parts[15];
    int n = 0;
    char *p = strtok(buf, ",");
    while (p && n < 15) { parts[n++] = p; p = strtok(NULL, ","); }
    if (n < 15) return;

    if (strlen(parts[1]) >= 6) {
        char t[16];
        snprintf(t, sizeof(t), "%.2s:%.2s:%.2s", parts[1], parts[1] + 2, parts[1] + 4);
        strcpy(st.gps_time, t);
    }

    if (strlen(parts[2]) && strlen(parts[3])) {
        float lat = atof(parts[2]);
        int deg = (int)(lat / 100);
        float lat_dec = deg + (lat - deg * 100) / 60.0f;
        if (parts[3][0] == 'S') lat_dec *= -1;
        st.gps_latitude = lat_dec;
    }

    if (strlen(parts[4]) && strlen(parts[5])) {
        float lon = atof(parts[4]);
        int deg = (int)(lon / 100);
        float lon_dec = deg + (lon - deg * 100) / 60.0f;
        if (parts[5][0] == 'W') lon_dec *= -1;
        st.gps_longitude = lon_dec;
    }

    if (strlen(parts[7])) st.gps_sats = atoi(parts[7]);
    if (strlen(parts[9])) st.gps_altitude = atof(parts[9]);
}

// ── Altitude from pressure ──────────────────────────────────────────
static float altitude_from_pressure(float press, float base) {
    return 44330.0f * (1.0f - pow(press / base, 1.0f / 5.255f));
}

// ── Format telemetry CSV ────────────────────────────────────────────
static void format_telemetry(char *out, size_t len) {
    snprintf(out, len,
        "%d,%u,%u,%s,%s,%.2f,%.2f,%.2f,%.3f,%.3f,"
        "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,"
        "%s,%.2f,%.6f,%.6f,%d,%s",
        TEAM_ID, st.mission_time, st.packet_count,
        st.mode, st.state_str,
        st.altitude, st.temperature, st.pressure,
        st.voltage, st.current,
        st.gyro_r, st.gyro_p, st.gyro_y,
        st.accel_r, st.accel_p, st.accel_y,
        st.gps_time, st.gps_altitude,
        st.gps_latitude, st.gps_longitude,
        st.gps_sats, st.cmd_echo);
}

// ── Execute command ─────────────────────────────────────────────────
void execute_command(const char *cmd) {
    if (strncmp(cmd, "CMD", 3) != 0) return;

    char buf[128];
    strncpy(buf, cmd, sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';

    char *parts[8];
    int n = 0;
    char *p = strtok(buf, ",");
    while (p && n < 8) { parts[n++] = p; p = strtok(NULL, ","); }
    if (n < 3) return;

    int tid = atoi(parts[1]);
    if (tid != TEAM_ID) return;

    strcpy(st.cmd_echo, cmd);

    const char *action = parts[2];

    if (strcmp(action, "ST") == 0 && n >= 4) {
        st.mission_time = atol(parts[3]);
        strcpy(st.mode, "FLIGHT");
        strcpy(st.state_str, "ASCENT");
    } else if (strcmp(action, "CAL") == 0) {
        st.cal_bias_accel[0] = st.accel_r;
        st.cal_bias_accel[1] = st.accel_p;
        st.cal_bias_accel[2] = st.accel_y;
        st.cal_bias_gyro[0] = st.gyro_r;
        st.cal_bias_gyro[1] = st.gyro_p;
        st.cal_bias_gyro[2] = st.gyro_y;
        st.cal_bias_alt = st.altitude;
    } else if (strcmp(action, "SIM") == 0 && n >= 4) {
        if (strcmp(parts[3], "ENABLE") == 0) {
            st.sim_enabled = true;
            strcpy(st.mode, "SIMULATION");
        }
    } else if (strcmp(action, "SIMP") == 0 && n >= 4) {
        st.sim_pressure = atof(parts[3]);
    } else if (strcmp(action, "MEC") == 0 && n >= 5) {
        if (strcmp(parts[4], "ON") == 0) {
            servo.write(180);
            strcpy(st.state_str, "RELEASE");
        } else {
            servo.write(0);
        }
    } else if (strcmp(action, "CX") == 0) {
        const char *cx_state = (n >= 4) ? parts[3] : "ON";
        cam_ser.print("CX ");
        cam_ser.print(cx_state);
        cam_ser.println();
        if (strcmp(cx_state, "ON") == 0) {
            st.img_captured = false;
            receiving_img = true;
            img_state = IMG_HDR1;
            img_len = 0;
            img_received = 0;
        } else {
            receiving_img = false;
            img_state = IMG_IDLE;
        }
    }

    st.mission_time = millis() / 1000;
}

// ── Process incoming image bytes from ESP32-CAM ─────────────────────
void process_cam_uart() {
    if (!receiving_img) return;

    while (cam_ser.available() && img_state != IMG_DONE) {
        uint8_t b = cam_ser.read();

        switch (img_state) {
            case IMG_HDR1:
                if (b == 0xAA) img_state = IMG_HDR2;
                break;
            case IMG_HDR2:
                if (b == 0xBB) { img_state = IMG_LEN; img_len = 0; img_len_cnt = 0; }
                else img_state = IMG_HDR1;
                break;
            case IMG_LEN:
                img_len = (img_len << 8) | b;
                if (++img_len_cnt >= 4) img_state = IMG_DATA;
                break;
            case IMG_DATA:
                if (img_received < sizeof(img_buf)) img_buf[img_received++] = b;
                if (img_received >= img_len) {
                    // Save image to SD
                    char fname[64];
                    snprintf(fname, sizeof(fname), "%s/img_%lu.jpg", LOG_DIR, millis() / 1000);
                    File img_file = SD.open(fname, FILE_WRITE);
                    if (img_file) {
                        img_file.write(img_buf, img_len);
                        img_file.close();
                    }
                    st.img_captured = true;
                    receiving_img = false;
                    img_state = IMG_IDLE;
                    img_received = 0;
                }
                break;
        }
    }
}

// ── Setup ───────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(1000);

    // ── I2C ──
    Wire.begin(21, 22);
    Wire.setClock(100000);

    // ── Sensors ──
    bmp_ok = bmp.begin();
    if (bmp_ok) Serial.println("BMP280 OK");
    else Serial.println("BMP280 FAIL");

    mpu_ok = mpu.begin();
    if (mpu_ok) Serial.println("MPU6050 OK");
    else Serial.println("MPU6050 FAIL");

    ina_ok = ina.begin();
    if (ina_ok) Serial.println("INA219 OK");
    else Serial.println("INA219 FAIL");

    // ── GPS UART ──
    gps_ser.begin(GPS_BAUD, SERIAL_8N1, GPS_RX, GPS_TX);

    // ── ESP32-CAM UART ──
    cam_ser.begin(CAM_BAUD, SERIAL_8N1, CAM_RX, CAM_TX);

    // ── LoRa ──
    LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
    if (!LoRa.begin(LORA_FREQ)) {
        Serial.println("LoRa init failed!");
    } else {
        LoRa.setSpreadingFactor(7);
        LoRa.setSignalBandwidth(125E3);
        LoRa.setCodingRate4(5);
        LoRa.setTxPower(17);
        Serial.println("LoRa OK");
    }

    // ── Servo ──
    servo.attach(SERVO_PIN);
    servo.write(0);

    // ── SD card ──
    if (!SD.begin(SD_CS)) {
        Serial.println("SD init failed!");
    } else {
        SD.mkdir(LOG_DIR);
        char fname[64];
        snprintf(fname, sizeof(fname), "%s/flight_%lu.csv", LOG_DIR, millis() / 1000);
        csv_file = SD.open(fname, FILE_WRITE);
        if (csv_file) {
            csv_file.println(FPSTR(TLM_HEADER));
            csv_file.flush();
            Serial.print("Logging to "); Serial.println(fname);
        }
    }

    Serial.println("CanSat ESP32 ready");
}

// ── Main loop ───────────────────────────────────────────────────────
static uint32_t last_tlm = 0;
static char gps_buf[256];
static int gps_idx = 0;

void loop() {
    uint32_t now = millis();

    // ── Read GPS ──
    while (gps_ser.available()) {
        char c = gps_ser.read();
        if (gps_idx < (int)sizeof(gps_buf) - 1) gps_buf[gps_idx++] = c;
        if (c == '\n') {
            gps_buf[gps_idx] = '\0';
            gps_idx = 0;
            parse_nmea(gps_buf);
        }
    }

    // ── Read sensors + send telemetry at 1 Hz ──
    if (now - last_tlm >= TLM_INTERVAL) {
        last_tlm = now;
        st.mission_time = now / 1000;

        // BMP280
        if (bmp_ok) {
            float t, p;
            bmp.read(&t, &p);
            st.temperature = t;
            if (st.sim_enabled && st.sim_pressure > 0) p = st.sim_pressure;
            st.pressure = p;
            float alt = altitude_from_pressure(p, base_pressure);
            alt -= st.cal_bias_alt;
            st.altitude = (alt > 0) ? alt : 0;
        }

        // MPU-6050
        if (mpu_ok) {
            float ax, ay, az, gx, gy, gz;
            mpu.read(&ax, &ay, &az, &gx, &gy, &gz);
            st.accel_r = ax - st.cal_bias_accel[0];
            st.accel_p = ay - st.cal_bias_accel[1];
            st.accel_y = az - st.cal_bias_accel[2];
            st.gyro_r = gx - st.cal_bias_gyro[0];
            st.gyro_p = gy - st.cal_bias_gyro[1];
            st.gyro_y = gz - st.cal_bias_gyro[2];
        }

        // INA219
        if (ina_ok) {
            float v, c;
            ina.read(&v, &c);
            st.voltage = v;
            st.current = c;
        }

        // State machine
        st.packet_count++;
        if (st.altitude >= 10.0f && strcmp(st.state_str, "LAUNCH_WAIT") == 0) {
            strcpy(st.state_str, "ASCENT");
            strcpy(st.mode, "FLIGHT");
            base_pressure = st.pressure;
        }

        // Format and send
        char csv_line[256];
        format_telemetry(csv_line, sizeof(csv_line));

        // LoRa
        LoRa.beginPacket();
        LoRa.print(csv_line);
        LoRa.endPacket(false);

        // SD
        if (csv_file) {
            csv_file.println(csv_line);
            csv_file.flush();
        }

        // Serial debug
        Serial.println(csv_line);
    }

    // ── Receive image from ESP32-CAM ──
    process_cam_uart();

    // ── Check for LoRa commands ──
    int packet_size = LoRa.parsePacket();
    if (packet_size > 0) {
        char cmd[128];
        int i = 0;
        while (LoRa.available() && i < (int)sizeof(cmd) - 1) {
            cmd[i++] = (char)LoRa.read();
        }
        cmd[i] = '\0';
        execute_command(cmd);
    }
}
