# Rover de Inspeção de Pavimento — ESP32-WROVER + OV2640 + IA

Projeto final de robótica para controle remoto de um carrinho com **ESP32-WROVER-DEV** e câmera **OV2640**, realizando streaming de vídeo em tempo real para um backend **FastAPI + OpenCV + ONNX/YOLO** que detecta falhas no pavimento (rachaduras, buracos, desníveis).

## Estrutura do Repositório

```text
esp32-rover-pavimento/
├── firmware/    # Código da ESP32-WROVER-DEV (PlatformIO: Wi-Fi + MJPEG + WebSocket + Failsafe)
├── backend/     # Servidor Python FastAPI (captura de stream, inferência de IA e ponte de controle)
├── frontend/    # Interface Web (vídeo anotado, controles WASD/botões, telemetria e captura)
├── ai/          # Dataset coletado pelo carrinho, modelos .onnx e instruções de treino
├── docs/        # Plano de implementação detalhado
└── tests/       # Testes automatizados do backend
```

## Início Rápido (Ambiente Python)

O ambiente virtual fica em `.venv` (gerenciado com `uv`).

### 1. Rodar em Modo Simulação (sem ESP32 conectada)
Ideal para desenvolver e testar a interface, os comandos de controle e o pipeline de visão no computador:

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Depois abra no navegador: **http://localhost:8000**

- Use **W / A / S / D** (ou as setas / botões na tela) para pilotar o rover.
- Pressione **Espaço** para parada de emergência.
- Clique em **Capturar Frame** para salvar imagens em `ai/dataset/raw/`.

### 2. Conectar com a ESP32 real

1. Copie `.env.example` para `.env` e ajuste `ROVER_MOCK_MODE=false` e o IP da ESP32.
2. Suba o backend novamente:
   ```bash
   source .venv/bin/activate
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

### 3. Rodar os testes

```bash
source .venv/bin/activate
pytest
```

## Firmware (ESP32-WROVER-DEV)

O esqueleto inicial está em [firmware/platformio.ini](firmware/platformio.ini) e [firmware/src/main.cpp](firmware/src/main.cpp).
Antes de gravar na placa, confira o mapeamento da sua câmera `DCX OV2640 v2` e da sua Ponte H em [firmware/src/camera_pins.h](firmware/src/camera_pins.h).

## Plano de Implementação

Veja o roteiro completo por fases em [docs/PLANO_IMPLEMENTACAO.md](docs/PLANO_IMPLEMENTACAO.md).
