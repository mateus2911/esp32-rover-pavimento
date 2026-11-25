#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "config.h"
#include "camera_stream.h"
#include "motor_control.h"

static WebSocketsServer g_webSocket(CONTROL_WS_PORT);
static uint32_t g_lastCommandMs = 0;

static bool parseJsonIntField(const char *json, const char *fieldName, int &outValue) {
  char pattern[32];
  snprintf(pattern, sizeof(pattern), "\"%s\"", fieldName);

  const char *keyPos = strstr(json, pattern);
  if (keyPos == nullptr) {
    return false;
  }

  const char *colonPos = strchr(keyPos + strlen(pattern), ':');
  if (colonPos == nullptr) {
    return false;
  }

  const char *valStart = colonPos + 1;
  while (*valStart == ' ' || *valStart == '\t') {
    ++valStart;
  }

  char *endPtr = nullptr;
  long parsed = strtol(valStart, &endPtr, 10);
  if (endPtr == valStart) {
    return false;
  }

  outValue = static_cast<int>(parsed);
  return true;
}

static void onWebSocketEvent(uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED: {
      IPAddress ip = g_webSocket.remoteIP(num);
      Serial.printf("[WS] Cliente #%u conectado (%s)\n", num, ip.toString().c_str());
      g_lastCommandMs = millis();
      break;
    }

    case WStype_DISCONNECTED: {
      Serial.printf("[WS] Cliente #%u desconectado\n", num);
      if (g_webSocket.connectedClients() == 0) {
        motorStop();
      }
      break;
    }

    case WStype_TEXT: {
      if (payload == nullptr || length == 0) {
        return;
      }

      // Garante string terminada em '\0' com tamanho seguro
      char msg[128];
      size_t copyLen = length < (sizeof(msg) - 1) ? length : (sizeof(msg) - 1);
      memcpy(msg, payload, copyLen);
      msg[copyLen] = '\0';

      int left = 0;
      int right = 0;
      bool hasLeft = parseJsonIntField(msg, "left", left);
      bool hasRight = parseJsonIntField(msg, "right", right);

      if (hasLeft && hasRight) {
        motorSetSpeeds(left, right);
        g_lastCommandMs = millis();
      } else {
        Serial.printf("[WS] JSON inválido ignorado: %s\n", msg);
      }
      break;
    }

    default:
      break;
  }
}

static void setupWifi() {
#if ROVER_WIFI_USE_AP
  WiFi.mode(WIFI_AP);
  IPAddress apIp(192, 168, 4, 1);
  IPAddress subnet(255, 255, 255, 0);
  WiFi.softAPConfig(apIp, apIp, subnet);

  if (!WiFi.softAP(WIFI_AP_SSID, WIFI_AP_PASS, WIFI_AP_CHANNEL, 0, WIFI_AP_MAX_CLIENTS)) {
    Serial.println("[ERRO] Falha ao iniciar rede Wi-Fi SoftAP!");
    return;
  }

  WiFi.setSleep(false);
  Serial.printf("[OK] SoftAP criado! SSID: %s | Senha: %s\n", WIFI_AP_SSID, WIFI_AP_PASS);
  Serial.printf("[OK] IP da ESP32: %s\n", WiFi.softAPIP().toString().c_str());
#else
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASS);
  WiFi.setSleep(false);

  Serial.printf("[INFO] Conectando ao Wi-Fi %s", WIFI_STA_SSID);
  uint32_t startMs = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - startMs) < 20000) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[OK] Conectado! IP da ESP32: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[ERRO] Timeout ao conectar no Wi-Fi STA.");
  }
#endif
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== Rover de Inspeção de Pavimento (ESP32-WROVER-DEV) ===");

  // 1. Garante motores parados desde o primeiro milissegundo
  motorInit();

  // 2. Inicializa câmera OV2640 (usa LEDC_CHANNEL_0 / TIMER_0)
  if (cameraInit()) {
    // 3. Configura Wi-Fi e sobe servidor MJPEG na porta 81
    setupWifi();
    startCameraStreamServer();
  } else {
    Serial.println("[AVISO] Seguindo sem câmera (apenas Wi-Fi + controle de motores).");
    setupWifi();
  }

  // 4. Sobe servidor WebSocket de controle na porta 82
  g_webSocket.begin();
  g_webSocket.onEvent(onWebSocketEvent);
  g_lastCommandMs = millis();

  Serial.printf("[OK] WebSocket de motores ativo na porta %d\n", CONTROL_WS_PORT);
  Serial.printf("[INFO] Stream MJPEG: http://%s:%d/stream\n",
                ROVER_WIFI_USE_AP ? WiFi.softAPIP().toString().c_str() : WiFi.localIP().toString().c_str(),
                STREAM_HTTP_PORT);
}

void loop() {
  g_webSocket.loop();

  // Failsafe obrigatório: desliga os motores se ficar > 500 ms sem receber comandos
  if (motorIsActive() && (millis() - g_lastCommandMs) > FAILSAFE_TIMEOUT_MS) {
    motorStop();
    Serial.println("[FAILSAFE] Sem comandos > 500ms — motores desligados.");
  }
}
