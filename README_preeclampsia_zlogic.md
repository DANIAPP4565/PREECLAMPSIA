# App Preeclampsia ICG Z-Logic

Versión 2026-06-14h.

## Cambio crítico confirmado

La pestaña **PDF Z-Logic** ahora trabaja con **dos informes PDF distintos del mismo estudio**:

1. **CARGAR PDF 1: INFORME Z-LOGIC DE 4 HOJAS**  
   Botón independiente: **IMPORTAR INFORME DE 4 HOJAS**

2. **CARGAR PDF 2: INFORME COMPLETO Z-LOGIC**  
   Botón independiente: **IMPORTAR INFORME COMPLETO Z-LOGIC**

3. Botón final de fusión:  
   **IMPORTAR E INTEGRAR LOS DOS PDF: DE 4 HOJAS + COMPLETO**

## Qué integra

- Datos basales en **Acostado / decúbito supino**.
- Datos de **Sentado** si están disponibles.
- Datos de **Parado / bipedestación**.
- Variables principales: FC, PA, DS, IDS, VM, IC, RVS, IRV, CA, ICA, IV, IAC, CTS, ITC, CFT.
- Variables adicionales del informe de 4 hojas: CFTnr, FE Weissler, FE Capan, RPVFSE/Suga, IC/PAS, ISRVS, EA, EES, AC y delta Z0.
- Auditoría de conflictos entre ambos PDF.
- Gráfico de punto del paciente en cuadrantes IC/IRV.
- Gráfico de desplazamiento ortostático **acostado → parado**.
- Informe PDF médico con gráficos, ML y conducta sugerida.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
