# Runbook para LLM — Setup, Gravação do Firmware e Execução em Outro PC

> **Instrução para a LLM / Agente:** Siga as etapas abaixo em ordem para preparar este projeto em um computador novo, compilar e gravar o firmware na **ESP32-WROVER-DEV**, conectar ao carrinho e iniciar o painel de controle/coleta de dataset.
> **Não invente valores, portas ou resultados:** execute os comandos, valide as saídas e pare para pedir ação manual ao usuário apenas nos pontos marcados como **[AÇÃO DO USUÁRIO]**.

---

## Contexto do Repositório

- **Repositório:** `https://github.com/mateus2911/esp32-rover-pavimento.git`
- **Branch de trabalho:** `teste`
- **Hardware:** ESP32-WROVER-DEV + câmera OV2640 (`DCX-OV2640-v2`) + Ponte H (padrão L298N 6 pinos nos GPIOs `32, 33, 14, 13, 15, 2`).
- **Contratos de rede (ESP32 em SoftAP):**
  - Wi-Fi SSID: `RoverPavimento` | Senha: `12345678` | IP: `192.168.4.1`
  - Stream MJPEG: `http://192.168.4.1:81/stream`
  - WebSocket motores: `ws://192.168.4.1:82` (JSON `{"left": -255..255, "right": -255..255}`, *failsafe* de 500 ms)
- **Regra importante sobre `.env` e testes:** mantenha `ROVER_MOCK_MODE=true` no `.env` local para que `pytest` continue passando sem hardware conectado. Para rodar com o carrinho real, use `python -m backend --real` (que sobrescreve `ROVER_MOCK_MODE=false` apenas em tempo de execução).

---

## Etapa 1 — Clonar ou Atualizar na Branch `teste`

Verifique se já está dentro do repositório; caso contrário, clone na branch `teste`:

```bash
git clone -b teste https://github.com/mateus2911/esp32-rover-pavimento.git
cd esp32-rover-pavimento
```

Se já estiver clonado:

```bash
git fetch origin
git checkout teste
git pull origin teste
```

Confirme com `git branch --show-current` que a saída é `teste`.

---

## Etapa 2 — Configurar Ambiente Python e Validar Backend

O projeto exige **Python `>=3.11,<3.14`** (definido em `pyproject.toml`).

1. Verifique as ferramentas disponíveis:
   ```bash
   which uv python3
   python3 --version
   ```
2. Crie o ambiente virtual `.venv` e instale o projeto com dependências de desenvolvimento (`dev` inclui `pytest` e `httpx`):
   - **Com `uv` (preferencial):**
     ```bash
     uv venv .venv --python 3.12
     uv pip install --python .venv/bin/python -e ".[dev]"
     ```
   - **Sem `uv` (fallback com `pip`):**
     ```bash
     python3 -m venv .venv
     .venv/bin/pip install --upgrade pip
     .venv/bin/pip install -e ".[dev]"
     ```
3. Crie o `.env` caso ainda não exista:
   ```bash
   test -f .env || cp .env.example .env
   ```
4. Execute os testes automatizados para validar o backend:
   ```bash
   .venv/bin/pytest -v
   ```
   - **Critério de sucesso:** todos os testes devem passar (`7 passed`). Se falhar, pare e investigue antes de prosseguir.

---

## Etapa 3 — Instalar PlatformIO e Compilar o Firmware

O projeto já possui `firmware/platformio.ini` configurado para `esp-wrover-kit` com `-DBOARD_HAS_PSRAM` e `links2004/WebSockets`.

1. Verifique se `pio` já está no `PATH`; se não estiver, instale via `uv` (ou `pipx` / `pip`):
   ```bash
   which pio || uv tool install platformio
   ```
   *(Se `uv` não existir, use `pipx install platformio` ou `python3 -m pip install --user platformio` e garanta `~/.local/bin` no `PATH`.)*

2. Compile o firmware (na primeira execução o PlatformIO baixa a toolchain `espressif32` e a biblioteca `WebSockets`):
   ```bash
   pio run -d firmware
   ```
   - **Critério de sucesso:** saída final `[SUCCESS]` gerando `firmware/.pio/build/esp-wrover-kit/firmware.bin`.
   - **Não avance para o upload se o build falhar.**

---

## Etapa 4 — Gravar o Firmware na ESP32-WROVER-DEV

1. Verifique se há porta serial conectada:
   - **Linux:** `ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true` e `pio device list`
   - **Windows/macOS:** `pio device list`
2. Se nenhuma placa aparecer:
   - **[AÇÃO DO USUÁRIO]:** peça ao usuário para conectar a ESP32-WROVER-DEV ao computador via cabo USB de dados e confirmar quando estiver conectada.
3. No Linux, se houver erro `Permission denied` ao acessar `/dev/ttyUSB0` (ou `/dev/ttyACM0`):
   - Verifique os grupos atuais com `id`.
   - **[AÇÃO DO USUÁRIO]:** informe que é necessário adicionar o usuário ao grupo da porta serial (`sudo usermod -aG dialout $USER` no Ubuntu/Debian, ou `uucp` no Arch) e reiniciar a sessão/terminal. **Não tente contornar permissões.**
4. Faça o upload do firmware:
   ```bash
   pio run -d firmware -t upload
   ```
   - Se o `esptool` falhar ao conectar (`Failed to connect to ESP32: Timed out waiting for packet header`):
     - **[AÇÃO DO USUÁRIO]:** peça para desconectar temporariamente o fio ligado ao `GPIO 2` (`IN4`) ou segurar o botão `BOOT` da ESP32 ao iniciar o upload.
5. *(Opcional, recomendado)* Verifique o boot na serial por alguns segundos para confirmar câmera, SoftAP e portas `81`/`82`:
   ```bash
   pio device monitor -d firmware -b 115200
   ```
   - Saída esperada inclui:
     - `[OK] Câmera OV2640 inicializada.`
     - `[OK] SoftAP criado! SSID: RoverPavimento | Senha: 12345678`
     - `[OK] Servidor MJPEG ativo na porta 81 (/stream)`
     - `[OK] WebSocket de motores ativo na porta 82`

---

## Etapa 5 — Conectar ao Wi-Fi do Carrinho e Testar Operação Real

1. **[AÇÃO DO USUÁRIO]:** peça para o usuário ligar a alimentação do carrinho (bateria dos motores + 5V da ESP32 com GND em comum) e conectar o notebook na rede Wi-Fi:
   - **SSID:** `RoverPavimento`
   - **Senha:** `12345678`
   *(Nota: caso o firmware tenha sido alterado em `firmware/rover_esp32/config.h` para `ROVER_WIFI_USE_AP false`, peça o IP exibido na serial e ajuste `ROVER_ESP32_STREAM_URL` e `ROVER_ESP32_WS_URL` no `.env`.)*

2. Valide conectividade com a ESP32 antes de abrir o servidor:
   ```bash
   curl -sS --max-time 3 http://192.168.4.1:81/
   ```
   - Deve responder: `ESP32 Rover Camera Stream OK. Use /stream or /capture.`

3. Inicie o backend Python em **modo real** (conectado à ESP32):
   ```bash
   .venv/bin/python -m backend --real
   ```

4. Informe ao usuário para abrir **`http://localhost:8000`** no navegador e confira:
   - Topo da tela mostra badge **`ESP32 Conectada`** (ou status da câmera/motores) e **`WS Conectado`**.
   - Vídeo ao vivo aparece na tela.
   - Controles **`W / A / S / D`** acionam os motores; **`Espaço`** para imediatamente.
   - **`F`** (botão **Tirar Foto Agora**) salva uma foto avulsa e **`C`** (chave **Captura Contínua**) grava **3 imagens/s** em `ai/dataset/raw/`.

---

## Checklist Final para a LLM Reportar ao Usuário

Ao concluir, informe objetivamente o resultado observado de cada item:
1. Branch ativa (`teste`) e commit atual (`git log -1 --oneline`).
2. Resultado de `.venv/bin/pytest -v`.
3. Resultado de `pio run -d firmware` e `pio run -d firmware -t upload` (incluindo porta utilizada).
4. Status da conexão com `http://192.168.4.1:81/` e servidor `python -m backend --real` rodando em `http://localhost:8000`.
