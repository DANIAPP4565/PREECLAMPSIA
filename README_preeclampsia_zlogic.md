# App Preeclampsia ICG Z-Logic

Versión 2026-06-14f.

## Cambio crítico

La pantalla PDF Z-Logic ahora muestra dos importadores separados y dos botones independientes:

1. `CARGAR PDF: INFORME Z-LOGIC DE 4 HOJAS` + botón `IMPORTAR INFORME DE 4 HOJAS`.
2. `CARGAR PDF: INFORME COMPLETO Z-LOGIC` + botón `IMPORTAR INFORME COMPLETO Z-LOGIC`.
3. Botón final `IMPORTAR E INTEGRAR LOS DOS PDF: DE 4 HOJAS + COMPLETO`.

La integración complementa variables entre ambos PDF y luego genera diagnóstico, cuadrantes IC/IRV y ortostatismo supino/parado.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
