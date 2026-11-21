#pragma once

// ============================================================================
// ATENÇÃO: CONFIRA OS PINOS DA SUA PLACA ESP32-WROVER-DEV + DCX OV2640 V2
// antes de gravar! Algumas placas WROVER-CAM (ex.: Freenove / Espressif WROVER)
// variam nos pinos de SIOD/SIOC/XCLK/VSYNC/HREF/PCLK.
// ============================================================================

// Pinout padrão Freenove ESP32-WROVER-DEV CAM (verifique com o esquemático da sua placa)
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  21
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27

#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    19
#define Y4_GPIO_NUM    18
#define Y3_GPIO_NUM     5
#define Y2_GPIO_NUM     4
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22

// ============================================================================
// PINOS DE CONTROLE DA PONTE H (Motores DC)
// NÃO USE:
//   - GPIO 16, 17 (PSRAM na ESP32-WROVER)
//   - GPIO 34, 35, 36, 39 (somente entrada - sem PWM/saída)
//   - Pinos já usados pela câmera acima
// ============================================================================
#define MOTOR_LEFT_IN1   14
#define MOTOR_LEFT_IN2   13
#define MOTOR_LEFT_PWM   32

#define MOTOR_RIGHT_IN1  33
#define MOTOR_RIGHT_IN2  15
#define MOTOR_RIGHT_PWM  12  // Cuidado: GPIO 12 é strapping pin (MTDI). Não puxe para HIGH no boot!
