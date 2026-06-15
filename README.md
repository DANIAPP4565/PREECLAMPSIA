# App Preeclampsia ICG Z-Logic

Versión 2026-06-15d.

## Cambio principal

La app conserva la importación obligatoria de **dos PDF separados**:

1. **PDF COMPLETO Z-Logic**  
   Botón: **1. IMPORTAR INFORME COMPLETO Z-LOGIC**

2. **PDF Z-Logic DE 4 HOJAS**  
   Botón: **2. IMPORTAR INFORME DE 4 HOJAS**

3. Botón final: **3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS**

## Modelos ML incorporados

La salida ML queda separada en dos bloques para no mezclar objetivos:

- **Olano 2023:** riesgo general de preeclampsia con CA/ICA, IC, ITC/ITS, CTE e IH.
- **Olano 2025:** orientación de subtipo de riesgo hacia PE temprana o PE tardía con STR/CTS, IA/IAC, ELV/EES y ACI/CA.

El informe PDF, Markdown, Excel y la pantalla principal muestran ambos resultados en secciones separadas.

## Cuadrante hemodinámico

Los ejes se muestran en unidades clínicas:

- X: IC medido real, L/min/m².
- Y: IRV medido real, dyn·s·cm⁻5·m².

Internamente la app usa z-score por edad gestacional para clasificar bajo/normal/alto.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
