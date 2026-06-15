# App Preeclampsia ICG Z-Logic

Versión 2026-06-14j.

## Cambio crítico corregido

La pantalla **PDF Z-Logic** ahora muestra **dos importadores separados** y **dos botones independientes**:

1. **PDF COMPLETO Z-Logic**  
   Botón: **1. IMPORTAR INFORME COMPLETO Z-LOGIC**

2. **PDF Z-Logic DE 4 HOJAS**  
   Botón: **2. IMPORTAR INFORME DE 4 HOJAS**

3. Luego se habilita:  
   **3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS**

## Integración de variables

- El informe **COMPLETO** se usa como fuente primaria para las variables basales: FC, PA, DS, IDS, VM, IC, RVS, IRV, CA, IV, IAC, CTS, ITC, CFT, Z0.
- El informe **DE 4 HOJAS** complementa variables no compartidas: CFTnr, EA, EES, AC, FE, cambios hemodinámicos acostado/sentado/parado y ortostatismo.
- Si hay conflicto entre valores, se muestra auditoría. Para el basal se conserva el valor del informe COMPLETO y se permite corrección manual.

## Ortostatismo

La app genera:

- Tabla acostado vs parado.
- Delta y delta %.
- Interpretación automática.
- Gráfico con flecha **acostado → parado** en cuadrante IC/IRV.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
