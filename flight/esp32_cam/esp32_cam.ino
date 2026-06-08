/*
  ESP32-CAM Camera Coprocessor
  Communicates with Main ESP32 over UART.
  Protocol:
    RX: "CX ON\r\n"  → capture JPEG → send 0xAA 0xBB + uint32_t len + data + "DONE\r\n"
    RX: "CX OFF\r\n" → camera sleep → "OK\r\n"
*/

#include "esp_camera.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#define CAM_BAUD 115200
#define FLASH_LED 4

// AI-Thinker ESP32-CAM pin config
static const camera_config_t camera_config = {
    .pin_pwdn = -1,
    .pin_reset = -1,
    .pin_xclk = 0,
    .pin_sscb_sda = 26,
    .pin_sscb_scl = 27,
    .pin_d7 = 35,
    .pin_d6 = 34,
    .pin_d5 = 39,
    .pin_d4 = 36,
    .pin_d3 = 21,
    .pin_d2 = 19,
    .pin_d1 = 18,
    .pin_d0 = 5,
    .pin_vsync = 25,
    .pin_href = 23,
    .pin_pclk = 22,
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,
    .pixel_format = PIXFORMAT_JPEG,
    .frame_size = FRAMESIZE_SVGA,
    .jpeg_quality = 12,
    .fb_count = 1,
    .fb_location = CAMERA_FB_IN_PSRAM,
    .grab_mode = CAMERA_GRAB_WHEN_EMPTY,
};

static const char CMD_ON[] = "CX ON\r\n";
static const char CMD_OFF[] = "CX OFF\r\n";
static const char RESP_OK[] = "OK\r\n";
static const char RESP_DONE[] = "DONE\r\n";

static bool camera_active = false;

void send_jpeg() {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        Serial.write(RESP_OK);
        return;
    }

    uint8_t hdr[6] = {0xAA, 0xBB};
    uint32_t len = fb->len;
    hdr[2] = (len >> 24) & 0xFF;
    hdr[3] = (len >> 16) & 0xFF;
    hdr[4] = (len >> 8) & 0xFF;
    hdr[5] = len & 0xFF;

    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    Serial.write(hdr, 6);
    Serial.write(fb->buf, fb->len);
    esp_camera_fb_return(fb);
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 1);

    Serial.write(RESP_DONE);
}

void camera_power(bool on) {
    if (on && !camera_active) {
        esp_camera_init(&camera_config);
        sensor_t *s = esp_camera_sensor_get();
        s->set_framesize(s, FRAMESIZE_SVGA);
        camera_active = true;
    } else if (!on && camera_active) {
        esp_camera_deinit();
        camera_active = false;
    }
}

void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 1);
    pinMode(FLASH_LED, OUTPUT);
    digitalWrite(FLASH_LED, LOW);

    Serial.begin(CAM_BAUD);
    Serial.setTimeout(100);

    pinMode(4, OUTPUT);  // flash
    digitalWrite(4, LOW);
}

void loop() {
    static char buf[32];
    static int idx = 0;

    while (Serial.available()) {
        char c = Serial.read();
        if (idx < (int)sizeof(buf) - 1) buf[idx++] = c;

        if (c == '\n') {
            buf[idx] = '\0';
            idx = 0;

            if (strcmp(buf, CMD_ON) == 0) {
                camera_power(true);
                digitalWrite(FLASH_LED, HIGH);
                delay(200);
                send_jpeg();
                digitalWrite(FLASH_LED, LOW);
            } else if (strcmp(buf, CMD_OFF) == 0) {
                camera_power(false);
                Serial.write(RESP_OK);
            }
        }
    }
}
