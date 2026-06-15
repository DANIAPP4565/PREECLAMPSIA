# App Preeclampsia ICG Z-Logic

## Versión 2026-06-14L

Corrección obligatoria solicitada:

La app trabaja con **dos PDF separados** del mismo estudio Z-Logic:

1. **PDF COMPLETO Z-Logic**  
   Botón: **1. IMPORTAR INFORME COMPLETO Z-LOGIC**

2. **PDF Z-Logic DE 4 HOJAS**  
   Botón: **2. IMPORTAR INFORME DE 4 HOJAS**

3. Luego se ejecuta:  
   **3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS**

No queda el flujo de un solo PDF. El archivo `app.py` tiene `dual_pdf_flow()` y el `main()` llama a ese flujo. El flujo anterior de un único PDF no se usa.

La integración complementa variables basales del informe COMPLETO con variables adicionales y ortostáticas del informe DE 4 HOJAS, incluyendo acostado/sentado/parado, CFTnr, EA, EES y AC cuando estén disponibles.

## Ejecutar

```bash
pip install -r requirements.txt
streamlit run app.py
```
