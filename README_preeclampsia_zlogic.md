# App Preeclampsia ICG Z-Logic

Versión 2026-06-14i.

## Funcionalidad obligatoria respetada

La pantalla **PDF Z-Logic** trabaja con **dos informes separados** del mismo estudio:

1. **PDF COMPLETO Z-Logic**  
   Botón independiente: `1. IMPORTAR INFORME COMPLETO Z-LOGIC`

2. **PDF Z-Logic DE 4 HOJAS**  
   Botón independiente: `2. IMPORTAR INFORME DE 4 HOJAS`

3. Luego se presiona:  
   `3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS`

No se reemplaza un PDF por el otro. La app complementa variables entre ambos informes para que el análisis use la mayor cantidad posible de datos.

## Integración esperada con los ejemplos

- El informe completo aporta la tabla basal: IC, IRV, RVS, CA, IV, IAC, CTS, ITC, CFT, FC, PA, etc.
- El informe de 4 hojas aporta cambios por posición y variables adicionales: sentado/parado, CFTnr, EA, EES, AC, FE, ISRVS, delta Z0, etc.
- El informe médico genera gráfico IC/IRV por edad gestacional, cuadrante con punto del paciente y desplazamiento ortostático acostado → parado cuando existan IC e IRV en ambas posiciones.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
