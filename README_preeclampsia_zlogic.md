# App Preeclampsia ICG Z-Logic

Versión 2026-06-14e.

## Concepto corregido

La app importa **dos informes PDF diferentes** del mismo estudio Z-Logic:

1. **Informe Z-Logic DE 4 HOJAS**
2. **Informe Z-Logic COMPLETO**

Ambos son obligatorios. La integración complementa las variables porque los dos informes no comparten exactamente los mismos datos.

## Flujo de uso

1. Abrir la pestaña **PDF Z-Logic**.
2. Cargar el PDF llamado **DE 4 HOJAS** en el primer campo.
3. Cargar el PDF llamado **COMPLETO** en el segundo campo.
4. Presionar **IMPORTAR E INTEGRAR LOS DOS PDF: DE 4 HOJAS + COMPLETO**.
5. Revisar auditoría, variables basales, variables de pie/parado, cuadrantes IC/IRV y ortostatismo.
6. Generar informe médico PDF.

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```
