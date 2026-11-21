#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "esp_http_server.h"
#include "camera_pins.h"

// ============================================================================
// Configuração Wi-Fi
// true = ESP32 cria sua própria rede Wi-Fi (192.168.4.1) - ótimo para campo
// false = ESP32 conecta em um roteador/hotspot existente
// ============================================================================
const bool USE_SOFT_AP = true;
const char *WIFI_SSID = "RoverPavimento";
const char *WIFI_PASS = "rover1234";

// Failsafe: se passar mais de 500 ms sem comando, para os motores
const unsigned long FAILSAFE_TIMEOUT_MS = 500;
unsigned long lastCmdMs = 0;

// Canais PWM (ESP32 LEDC)
const int PWM_FREQ = 1000;
const int PWM_RES = 8; // 0..255
const int PWM_CH_LEFT = 4;
const int PWM_CH_RIGHT = 5;

WebSocketsServer webSocket(82);
httpd_handle_t streamHttpd = nullptr;

void setMotor(int in1, int in2, int pwmChannel, int speed) {
    int constrainedSpeed = constrain(speed, -255, 255);
    if (constrainedSpeed > 0) {
        digitalWrite(in1, HIGH);
        digitalWrite(in2, LOW);
        ledcWrite(pwmChannel, constrainedSpeed);
    } else if (constrainedSpeed < 0) {
        digitalWrite(in1, LOW);
        digitalWrite(in2, HIGH);
        ledcWrite(pwmChannel, -constrainedSpeed);
    } else {
        digitalWrite(in1, LOW);
        digitalWrite(in2, LOW);
        ledcWrite(pwmChannel, 0);
    }
}

void stopMotors() {
    setMotor(MOTOR_LEFT_IN1, MOTOR_LEFT_IN2, PWM_CH_LEFT, 0);
    setMotor(MOTOR_RIGHT_IN1, MOTOR_RIGHT_IN2, PWM_CH_RIGHT, 0);
}

void setupMotors() {
    pinMode(MOTOR_LEFT_IN1, OUTPUT);
    pinMode(MOTOR_LEFT_IN2, OUTPUT);
    pinMode(MOTOR_RIGHT_IN1, OUTPUT);
    pinMode(MOTOR_RIGHT_IN2, OUTPUT);

    ledcSetup(PWM_CH_LEFT, PWM_FREQ, PWM_RES);
    ledcAttachPin(MOTOR_LEFT_PWM, PWM_CH_LEFT);

    ledcSetup(PWM_CH_RIGHT, PWM_FREQ, PWM_RES);
    ledcAttachPin(MOTOR_RIGHT_PWM, PWM_CH_RIGHT);

    stopMotors();
}

bool setupCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    if (psramFound()) {
        config.frame_size = FRAMESIZE_VGA; // 640x480
        config.jpeg_quality = 12;
        config.fb_count = 2;
        config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
        config.frame_size = FRAMESIZE_QVGA; // 320x240
        config.jpeg_quality = 15;
        config.fb_count = 1;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Falha ao inicializar câmera: 0x%x\n", err);
        return false;
    }
    return true;
}

#define PART_BOUNDARY "123456789000000000000987654321"
static const char *_STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *_STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char *_STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t streamHandler(httpd_req_t *req) {
    camera_fb_t *fb = nullptr;
    esp_err_t res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    char partBuf[64];
    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("Erro ao capturar frame da OV2640");
            res = ESP_FAIL;
        } else {
            size_t hlen = snprintf(partBuf, sizeof(partBuf), _STREAM_PART, fb->len);
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
            if (res == ESP_OK) {
                res = httpd_resp_send_chunk(req, partBuf, hlen);
            }
            if (res == ESP_OK) {
                res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
            }
            esp_camera_fb_return(fb);
        }
        if (res != ESP_OK) {
            break;
        }
    }
    return res;
}

void startStreamServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 81;

    httpd_uri_t streamUri = {
        .uri = "/stream",
        .method = HTTP_GET,
        .handler = streamHandler,
        .user_ctx = nullptr
    };

    if (httpd_start(&streamHttpd, &config) == ESP_OK) {
        httpd_register_uri_handler(streamHttpd, &streamUri);
        Serial.println("Servidor MJPEG iniciado na porta 81 (/stream)");
    }
}

void onWebSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
    if (type == WStype_DISCONNECTED) {
        stopMotors();
        return;
    }
    if (type != WStype_TEXT) {
        return;
    }

    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, payload, length);
    if (err) {
        return;
    }

    int left = doc["left"] | 0;
    int right = doc["right"] | 0;
    setMotor(MOTOR_LEFT_IN1, MOTOR_LEFT_IN2, PWM_CH_LEFT, left);
    setMotor(MOTOR_RIGHT_IN1, MOTOR_RIGHT_IN2, PWM_CH_RIGHT, right);
    lastCmdMs = millis();
}

void setupWiFi() {
    if (USE_SOFT_AP) {
        WiFi.softAP(WIFI_SSID, WIFI_PASS);
        Serial.print("SoftAP ativo. IP: ");
        Serial.println(WiFi.softAPIP());
    } else {
        WiFi.begin(WIFI_SSID, WIFI_PASS);
        Serial.print("Conectando ao Wi-Fi");
        while (WiFi.status() != WL_CONNECTED) {
            delay(500);
            Serial.print(".");
        }
        Serial.print("\nConectado. IP: ");
        Serial.println(WiFi.localIP());
    }
}

void setup() {
    Serial.begin(115200);
    setupMotors();
    setupWiFi();

    if (setupCamera()) {
        startStreamServer();
    }

    webSocket.begin();
    webSocket.onEvent(onWebSocketEvent);
    Serial.println("WebSocket de controle iniciado na porta 82");
}

void loop() {
    webSocket.loop();

    if (millis() - lastCmdMs > FAILSAFE_TIMEOUT_MS) {
        stopMotors();
    }
}
