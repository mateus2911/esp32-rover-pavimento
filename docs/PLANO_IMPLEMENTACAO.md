# Plano de Implementação — Rover de Inspeção de Pavimento (ESP32-WROVER + IA)

## 1. Visão Geral da Arquitetura (Opção 1)

1. **ESP32-WROVER-DEV + OV2640 (No Carrinho):**
   - Captura vídeo em `QVGA (320x240)` ou `VGA (640x480)` e transmite via stream **MJPEG** (`http://<ip>:81/stream`).
   - Recebe comandos diferenciais dos motores (`left`, `right` de `-255` a `255`) via **WebSocket** (`ws://<ip>:82`).
   - Executa **failsafe** automático: se ficar > 500 ms sem comando, zera os motores.
2. **Backend Python (No Notebook — FastAPI + OpenCV + ONNX):**
   - Lê continuamente o frame mais recente da ESP32 (`camera_stream.py`).
   - Executa inferência do modelo de detecção de falhas (`ai_detector.py`).
   - Encaminha comandos do operador para a ESP32 (`esp32_client.py`).
   - Salva frames brutos para dataset quando solicitado (`ai/dataset/raw/`).
3. **Interface Web (`frontend/`):**
   - Exibe vídeo anotado com caixas delimitadoras e FPS.
   - Permite pilotagem via teclado (`W/A/S/D` ou setas), botões virtuais ou controle Gamepad, além de parada de emergência (`Espaço`).

---

## 2. Roteiro por Fases

### Fase 1 — Hardware e Alimentação
- Conferir pinout exato da placa `ESP32-WROVER-DEV` com o módulo `DCX OV2640 v2`.
- Separar a alimentação dos motores (Ponte H) da alimentação lógica (5V da ESP32), mantendo apenas o GND em comum, para evitar reinicializações por *brownout*.
- Selecionar GPIOs livres para a Ponte H evitando `GPIO 16/17` (PSRAM) e `GPIO 34–39` (somente entrada).

### Fase 2 — Firmware ESP32 (`firmware/`)
- Compilar e gravar com PlatformIO (`firmware/platformio.ini`).
- Validar stream MJPEG isolado primeiro; depois testar motores com o carrinho suspenso (rodas fora do chão).
- Confirmar atuação do *failsafe* desligando o cliente WebSocket durante movimento.

### Fase 3 — Backend e Modo Simulação (`backend/`)
- Testar interface e pipeline completo usando `ROVER_MOCK_MODE=true`.
- Integrar fluxo real apontando `ROVER_ESP32_STREAM_URL` e `ROVER_ESP32_WS_URL` para o IP da ESP32.

### Fase 4 — Interface Web (`frontend/`)
- Ajustar velocidade máxima (slider PWM) e ergonomia de controle no campus.
- Adicionar captura rápida de imagens e visualização de log de detecções.

### Fase 5 — Dataset Real e Modelo de IA (`ai/`)
- Gravar imagens reais do pavimento da faculdade (asfalto/bloquete/calçada, com sombras e variações de luz).
- Rotular classes (`rachadura`, `buraco`, `desnivel`), treinar **YOLOv8n / YOLO11n** e exportar para `.onnx` (`ai/models/pavement_yolov8n.onnx`).
- Medir FPS e taxa de falsos positivos no notebook antes da apresentação final.
