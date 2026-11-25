#ifndef ROVER_CONFIG_H
#define ROVER_CONFIG_H

// =============================================================================
// 1. CONFIGURAÇÃO DE REDE WI-FI
// =============================================================================
// true  = ESP32 cria rede Wi-Fi própria (SoftAP) no IP 192.168.4.1 (padrão do projeto)
// false = ESP32 conecta em uma rede Wi-Fi / hotspot existente (STA)
#define ROVER_WIFI_USE_AP true

#define WIFI_AP_SSID "RoverPavimento"
#define WIFI_AP_PASS "12345678" // Mínimo 8 caracteres para WPA2
#define WIFI_AP_CHANNEL 1
#define WIFI_AP_MAX_CLIENTS 4

// Usado apenas se ROVER_WIFI_USE_AP == false
#define WIFI_STA_SSID "NOME_DA_SUA_REDE"
#define WIFI_STA_PASS "SENHA_DA_SUA_REDE"

// Portas dos servidores (devem bater com .env / backend/config.py)
#define STREAM_HTTP_PORT 81 // http://192.168.4.1:81/stream
#define CONTROL_WS_PORT 82  // ws://192.168.4.1:82

// =============================================================================
// 2. SEGURANÇA (FAILSAFE) E PWM DOS MOTORES
// =============================================================================
// Desliga os motores automaticamente se ficar mais de 500 ms sem comando
#define FAILSAFE_TIMEOUT_MS 500

// Frequência PWM em Hz (2 kHz funciona bem em L298N, TB6612FNG e DRV8833)
#define MOTOR_PWM_FREQ_HZ 2000
#define MOTOR_PWM_RES_BITS 8 // Resolução de 8 bits (0..255)

// Modo da Ponte H:
// 1 = 6 pinos (ENA + IN1 + IN2 e ENB + IN3 + IN4) -> L298N sem jumpers ou TB6612FNG
// 0 = 4 pinos (PWM direto em IN1/IN2 e IN3/IN4)    -> L298N com jumpers ou DRV8833
#define MOTOR_DRIVER_6PIN 1

// Pinos livres seguros na ESP32-WROVER-DEV + DCX OV2640 v2
// (Evitam pinos da câmera, PSRAM GPIO 16/17, Flash 6..11, UART 1/3, entrada 34..39 e GPIO 12)
#define MOTOR_LEFT_PWM_PIN 32  // ENA (usado se MOTOR_DRIVER_6PIN == 1)
#define MOTOR_LEFT_IN1_PIN 33  // IN1
#define MOTOR_LEFT_IN2_PIN 14  // IN2

#define MOTOR_RIGHT_PWM_PIN 13 // ENB (usado se MOTOR_DRIVER_6PIN == 1)
#define MOTOR_RIGHT_IN3_PIN 15 // IN3
#define MOTOR_RIGHT_IN4_PIN 2  // IN4 (se atrapalhar gravação USB, desconecte durante upload)

// Inverta para true caso algum motor gire ao contrário na montagem do chassi
#define INVERT_LEFT_MOTOR false
#define INVERT_RIGHT_MOTOR false

// =============================================================================
// 3. CÂMERA OV2640
// =============================================================================
// FRAMESIZE_QVGA (320x240) oferece maior FPS e combina com o treino imgsz=320.
// Se quiser fotos em maior resolução para o dataset, altere para FRAMESIZE_VGA (640x480).
#define CAMERA_FRAME_SIZE FRAMESIZE_QVGA
#define CAMERA_JPEG_QUALITY 12 // 0..63 (menor = melhor qualidade, mais dados)

// Ajuste se a câmera for montada invertida no suporte
#define CAMERA_VFLIP false
#define CAMERA_HMIRROR false

#endif // ROVER_CONFIG_H
