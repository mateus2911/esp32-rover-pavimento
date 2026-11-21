# Rover de Inspeção de Pavimento — ESP32-WROVER + OV2640 + IA

Repositório base e ambiente configurado para o projeto final de robótica: controle remoto de um carrinho com **ESP32-WROVER-DEV** e câmera **OV2640**, transmitindo vídeo em tempo real para um servidor Python que identifica falhas no pavimento.

## Estrutura de Pastas (Pronta para Implementação)

```text
esp32-rover-pavimento/
├── firmware/    # Código C++/Arduino da ESP32-WROVER-DEV (a implementar)
├── backend/     # Servidor Python FastAPI + OpenCV + ONNX + WebSocket (a implementar)
├── frontend/    # Interface Web de controle e visualização (a implementar)
├── ai/          # Dataset coletado, notebooks/scripts de treino e pesos .onnx
├── docs/        # Plano de implementação, arquitetura e divisão por etapas
└── tests/       # Testes automatizados com pytest (a implementar)
```

## Ambiente Python Configurado

O ambiente virtual já está criado em `.venv` (Python 3.12 via `uv`) com as dependências principais instaladas em [pyproject.toml](pyproject.toml):
- `fastapi` e `uvicorn[standard]` (servidor Web e WebSockets)
- `opencv-python-headless` e `numpy` (leitura/anotação de vídeo)
- `onnxruntime` (inferência leve de modelos YOLO exportados em `.onnx`)
- `websockets` e `pydantic-settings` (comunicação com a ESP32 e config via `.env`)
- `pytest` e `httpx` (testes)

Para ativar o ambiente no terminal:

```bash
source .venv/bin/activate
```

## Plano e Etapas do Grupo

Consulte o guia completo com a arquitetura explicada e a divisão de tarefas em [docs/PLANO_IMPLEMENTACAO.md](docs/PLANO_IMPLEMENTACAO.md).
