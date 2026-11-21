# IA — Coleta de Dados e Treinamento do Modelo

## Fluxo Recomendado

1. **Coleta no Campus:** Dirija o carrinho pelo pavimento da faculdade usando a interface Web e clique em **Capturar Frame** (ou ative gravação automática) para salvar imagens reais em `ai/dataset/raw/`.
2. **Rotulagem:** Suba as imagens para ferramentas como [Roboflow](https://roboflow.com/) ou CVAT e anote as classes:
   - `rachadura`
   - `buraco`
   - `desnivel` (opcional)
3. **Treinamento (Google Colab com GPU gratuita):**
   Treine um modelo leve **YOLOv8n** ou **YOLO11n** com resolução `320` ou `416` (compatível com o stream da OV2640):
   ```python
   from ultralytics import YOLO

   model = YOLO("yolo11n.pt")
   model.train(data="data.yaml", epochs=80, imgsz=320, batch=16)
   model.export(format="onnx", imgsz=320, simplify=True)
   ```
4. **Deploy no Notebook:**
   Copie o arquivo `best.onnx` gerado para `ai/models/pavement_yolov8n.onnx` (ou ajuste `ROVER_MODEL_PATH` no `.env`).
