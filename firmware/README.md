# Firmware Arduino — ESP32-WROVER-DEV + OV2640 + Ponte H

Este firmware implementa na ESP32-WROVER-DEV:
1. **Stream de vídeo MJPEG** da câmera OV2640 em `http://192.168.4.1:81/stream` (porta `81`) e foto avulsa em `/capture`.
2. **Servidor WebSocket** na porta `82` (`ws://192.168.4.1:82`) recebendo JSON `{"left": -255..255, "right": -255..255}`.
3. **Controle PWM dos motores** compatível com Arduino-ESP32 **v2.x e v3.x** (suporta Ponte H 6 pinos como **L298N / TB6612FNG** ou 4 pinos como **DRV8833 / L298N com jumpers**).
4. **Failsafe automático de 500 ms**: desliga os motores se perder conexão ou ficar mais de 500 ms sem receber comandos.

---

## 1. Ligação dos Pinos (ESP32-WROVER-DEV + DCX OV2640 v2)

Os pinos abaixo evitam conflitos com a câmera (`4, 5, 18, 19, 21..23, 25..27, 34..36, 39`), PSRAM (`16, 17`), Flash (`6..11`), Serial USB (`1, 3`) e o pino de boot `GPIO 12`:

| Função na Ponte H (ex.: L298N) | GPIO da ESP32 | Observação |
| :--- | :--- | :--- |
| `ENA` (PWM Motor Esquerdo) | `GPIO 32` | Defina `MOTOR_DRIVER_6PIN = 1` em `config.h` |
| `IN1` (Sentido Esquerdo A) | `GPIO 33` | — |
| `IN2` (Sentido Esquerdo B) | `GPIO 14` | — |
| `ENB` (PWM Motor Direito) | `GPIO 13` | Defina `MOTOR_DRIVER_6PIN = 1` em `config.h` |
| `IN3` (Sentido Direito A) | `GPIO 15` | — |
| `IN4` (Sentido Direito B) | `GPIO 2` | Se der erro ao gravar pela USB, desconecte este fio durante o upload |
| `GND` | `GND` | **Obrigatório** unir o GND da bateria dos motores com o GND da ESP32 |

> **Atenção elétrica:** Use baterias/reguladores separados para alimentar os motores (`12V`/`7.4V` na Ponte H) e a ESP32 (`5V` estável via USB/PowerBank), ligando **apenas o GND em comum**. Nunca alimente os motores pelo pino `5V`/`3V3` da ESP32.

---

## 2. Como Gravar pela Arduino IDE

1. Instale o pacote de placas **esp32 by Espressif Systems** (no Gerenciador de Placas).
2. Instale a biblioteca **WebSockets** (por *Markus Sattler* / `links2004`) no Gerenciador de Bibliotecas.
3. Abra o arquivo `firmware/rover_esp32/rover_esp32.ino`.
4. No menu **Ferramentas (Tools)**:
   - **Board:** `ESP32 Wrover Module`
   - **PSRAM:** `Enabled` *(muito importante para a câmera OV2640)*
   - **Partition Scheme:** `Huge APP (3MB No OTA/1MB SPIFFS)` ou `Default 4MB`
   - **Upload Speed:** `115200` (ou `921600` se o cabo USB for bom)
5. Clique em **Carregar (Upload)** e abra o **Monitor Serial** em `115200 baud` para confirmar o boot.

*(Alternativa via PlatformIO: abra a pasta `firmware/` no VS Code com PlatformIO e clique em **Upload**; o arquivo `firmware/platformio.ini` já baixa a biblioteca `WebSockets` automaticamente.)*

---

## 3. Como Testar e Coletar Fotos do Dataset

1. Ligue o carrinho e conecte o notebook na rede Wi-Fi criada pela ESP32:
   - **SSID:** `RoverPavimento`
   - **Senha:** `12345678`
2. Teste rápido do vídeo: abra `http://192.168.4.1:81/stream` no navegador para confirmar a imagem da câmera.
3. Na raiz do repositório, inicie o backend Python em **modo real** (conectado à ESP32):
   ```bash
   source .venv/bin/activate
   python -m backend --real
   ```
4. Abra `http://localhost:8000` no navegador:
   - Dirija com `W / A / S / D` (ou botões na tela) e use `Espaço` para parada de emergência.
   - Use **Tirar Foto (F)** para capturas pontuais ou ative **Captura Contínua (3 img/s)** (`C`) para gravar imagens em `ai/dataset/raw/`.
