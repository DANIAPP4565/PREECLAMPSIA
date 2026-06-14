# App Preeclampsia ICG Z-Logic

Versión corregida con importación explícita de informe completo Z-Logic/ICG de 4 hojas, integración de variables hemodinámicas, gráfico IC/IRV por edad gestacional y gráfico de ortostatismo decúbito supino vs bipedestación.

## Funciones principales

- Botón visible para cargar PDF completo Z-Logic de 4 hojas.
- Botón de importación e integración del PDF.
- Detección de posiciones: acostada/decúbito supino/basal/cinta y bipedestación/parado.
- Extracción automática de IC, IRV, RVS, CA/ICA, ITC/ITS, CTE, CTS/STR, IH, IAC/IA, CFT, EA, EES, EA/EES, FC y PA.
- Selección manual de posición basal y posición ortostática.
- Gráfico de IC e IRV versus edad gestacional.
- Gráfico de respuesta ortostática: IC, IRV, CA e IH/FC en decúbito supino vs bipedestación.
- Diagnóstico convencional hemodinámico.
- Diagnóstico ML interno sin pedir puntos de corte manuales.
- Subclasificador J48 Olano 2025 para PE temprana/tardía.
- PDF médico con logo institucional y firma/sello.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
