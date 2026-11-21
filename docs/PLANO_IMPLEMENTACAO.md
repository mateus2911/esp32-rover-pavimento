# Plano de Implementação e Guia do Grupo — Rover de Inspeção de Pavimento

Este documento explica **como o sistema vai funcionar** de forma simples e divide o projeto em **frentes paralelas e etapas**, para que os membros do grupo possam implementar tudo do zero de maneira organizada.

---

## 1. A Arquitetura Explicada de Forma Simples

O projeto é dividido em **3 partes**, cada uma com um papel bem definido:

1. **O Carrinho (`firmware/` — ESP32-WROVER-DEV + OV2640 + Motores):** é o **corpo e os olhos**.
   - Ele **não** roda inteligência artificial pesada dentro do chip (isso deixaria o vídeo lento a 1–2 FPS).
   - Ele faz apenas duas tarefas rápidas:
     1. Filma o chão com a câmera OV2640 e envia o vídeo pelo Wi-Fi.
     2. Escuta comandos numéricos de velocidade das rodas e aciona a Ponte H.
2. **O Notebook (`backend/` — Python + FastAPI + OpenCV + ONNX):** é o **cérebro**.
   - Recebe o vídeo da câmera pela rede Wi-Fi.
   - Passa cada imagem pelo modelo de IA para identificar **buracos** e **rachaduras**.
   - Recebe os comandos do operador e encaminha para o carrinho.
3. **O Navegador (`frontend/` — HTML/CSS/JS):** é o **controle remoto + monitor**.
   - Exibe o vídeo já anotado pela IA, mostra o status da conexão e envia os comandos do teclado (`W/A/S/D`), botões na tela ou gamepad.

```mermaid
flowchart LR
    subgraph Carrinho["1. CARRINHO (ESP32-WROVER-DEV)"]
        CAM["Câmera OV2640"]
        WIFI["Wi-Fi do Carrinho<br/>(ex.: 192.168.4.1)"]
        MOT["Ponte H + Motores"]
    end

    subgraph Notebook["2. NOTEBOOK (Backend Python)"]
        STREAM["Leitor de Vídeo<br/>(OpenCV)"]
        IA["Detector de Falhas<br/>(ONNX / YOLO)"]
        BRIDGE["Cliente de Controle<br/>(WebSocket)"]
        API["Servidor FastAPI (:8000)"]
    end

    subgraph Tela["3. TELA DO OPERADOR (Navegador)"]
        UI["Interface Web<br/>(Vídeo + WASD + Captura)"]
    end

    CAM -->|"Porta 81 (MJPEG)"| WIFI --> STREAM --> IA --> API -->|"MJPEG anotado"| UI
    UI -->|"WebSocket (/ws/control)"| API --> BRIDGE -->|"Porta 82 (JSON)"| WIFI -->|"PWM + Failsafe"| MOT
```

### Os dois fluxos acontecendo ao mesmo tempo
- **Fluxo de Vídeo (Câmera → IA → Tela):** a ESP32 disponibiliza um stream MJPEG contínuo (ex.: `http://192.168.4.1:81/stream`). O backend em Python lê sempre o frame mais recente (descartando frames antigos para não acumular atraso), roda a IA e envia o vídeo com as detecções para a tela.
- **Fluxo de Controle (Teclado → Carrinho):** o navegador calcula a velocidade de cada lado (`left` e `right`, de `-255` a `+255`) e manda via WebSocket para o backend Python, que repassa para a ESP32.
- **Segurança (Failsafe):** se a ESP32 ficar mais de **500 ms** sem receber comando (ex.: perda de Wi-Fi), o firmware deve desligar os motores automaticamente.

---

## 2. Combinados Técnicos (Contratos Entre os Membros)

Se o grupo seguir estes **3 combinados** desde o começo, o código de cada pessoa vai se encaixar perfeitamente depois:

| Integração | Combinado / Formato sugerido |
| :--- | :--- |
| **Vídeo (ESP32 → Python)** | Stream HTTP MJPEG em `http://<IP_ESP32>:81/stream` (resolução `QVGA 320x240` ou `VGA 640x480`) |
| **Controle (Python → ESP32)** | WebSocket na porta `82` recebendo JSON `{"left": -255..255, "right": -255..255}` |
| **Modelo IA (`ai/` → Python)** | Modelo exportado para `.onnx` em `ai/models/` com classes combinadas (ex.: `0: rachadura`, `1: buraco`) |

---

## 3. Divisão em Frentes (Trabalho em Paralelo)

### Frente A — Hardware, Elétrica e Chassi
- [ ] **A1.** Montar chassi, motores DC e Ponte H (`L298N`, `TB6612FNG` ou `DRV8833`).
- [ ] **A2.** **Separar a alimentação:** bateria dedicada para os motores e fonte/regulador 5V separado para a ESP32, unindo **apenas o GND**. *(Evita reinicialização por queda de tensão / brownout na partida dos motores).*
- [ ] **A3.** Mapear os pinos da **ESP32-WROVER-DEV + DCX OV2640 v2** e escolher GPIOs livres para a Ponte H (nunca usar `GPIO 16/17` da PSRAM nem `GPIO 34–39` que são somente entrada).
- [ ] **A4.** Construir suporte fixo para a câmera inclinada para o chão (~30° a 45°) à frente do carrinho.

### Frente B — Firmware da ESP32 (`firmware/`)
- [ ] **B1.** Configurar o projeto na IDE escolhida (PlatformIO no VS Code ou Arduino IDE) com suporte a PSRAM (`BOARD_HAS_PSRAM`).
- [ ] **B2.** Implementar inicialização da câmera OV2640 + Wi-Fi (SoftAP criando rede própria ou STA em hotspot) + servidor de stream MJPEG na porta `81`.
- [ ] **B3.** Testar o stream de vídeo isolado no navegador antes de ligar os motores.
- [ ] **B4.** Implementar servidor WebSocket na porta `82`, controle PWM dos motores (`ledcWrite`) e *failsafe* de 500 ms.

### Frente C — Backend Python e Interface Web (`backend/` e `frontend/`)
- [ ] **C1.** Criar servidor **FastAPI** inicial com um **modo simulação** (gerando frames falsos com OpenCV) para testar a interface mesmo sem a ESP32 pronta.
- [ ] **C2.** Implementar captura contínua do stream MJPEG da ESP32 em thread separada (mantendo apenas o último frame).
- [ ] **C3.** Criar rota de streaming anotado (`/video_feed`), WebSocket de controle (`/ws/control`), botão de parada de emergência e endpoint para salvar fotos brutas em `ai/dataset/raw/`.
- [ ] **C4.** Construir a interface Web (`index.html`, `styles.css`, `app.js`) com vídeo ao vivo, controles por teclado (`W/A/S/D`), botões na tela, slider de velocidade e lista de falhas detectadas.

### Frente D — Inteligência Artificial e Dataset (`ai/`)
- [ ] **D1.** Estruturar notebook de treino (ex.: Google Colab com GPU gratuita) usando **YOLOv8n** ou **YOLO11n** e testar exportação para `.onnx` (`imgsz=320`).
- [ ] **D2.** Coletar de 200 a 500 imagens reais do pavimento da faculdade usando o próprio carrinho (incluir fotos sem defeitos, com sombras, folhas e diferentes iluminações).
- [ ] **D3.** Rotular as imagens (ex.: Roboflow ou CVAT) com as classes definidas (`rachadura`, `buraco`, etc.).
- [ ] **D4.** Treinar o modelo definitivo, exportar para `.onnx`, colocar em `ai/models/` e integrar no backend com `onnxruntime`.

---

## 4. Etapas Cronológicas de Execução

1. **Etapa 0 — Setup do Ambiente (Todo o grupo):**
   - Clonar o repositório, ativar o ambiente `.venv` (`source .venv/bin/activate`) e alinhar os combinados da Seção 2.
2. **Etapa 1 — Desenvolvimento Paralelo por Frente:**
   - **A** monta o chassi/elétrica; **B** faz câmera + WebSocket na ESP32; **C** cria backend + dashboard em modo simulação; **D** prepara pipeline de treino e testa um `.onnx` piloto.
3. **Etapa 2 — Primeira Integração Real (Hardware + Software):**
   - Conectar o notebook no Wi-Fi da ESP32 e dirigir o carrinho pelo painel Web vendo a câmera OV2640 ao vivo (ainda sem o modelo final de IA).
4. **Etapa 3 — Coleta em Campo e Treinamento Real:**
   - Andar com o carrinho pelo pavimento da faculdade capturando imagens reais, rotular o dataset e treinar o modelo `.onnx` definitivo.
5. **Etapa 4 — Integração Final e Ensaio da Banca:**
   - Integrar o modelo final no backend, ajustar limiar de confiança para reduzir falsos positivos, medir FPS/latência e fazer testes completos no pavimento escolhido para a apresentação.
