# Preeclampsia Z-Logic ICG · Integración doble PDF y ortostatismo

Versión 2026-06-14c.

## Cambios incluidos

- Carga de **dos informes Z-Logic del mismo estudio**:
  - Informe **COMPLETO**.
  - Informe **DE 4 HOJAS**.
- Selector múltiple para cargar ambos PDF juntos y, además, dos selectores separados como alternativa.
- Botón único: **IMPORTAR E INTEGRAR INFORME COMPLETO + INFORME DE 4 HOJAS**.
- Integración complementaria de variables entre ambos PDF.
- Auditoría de conflictos cuando una misma variable aparece con valores diferentes.
- Selección explícita de postura basal: **acostada / decúbito supino**.
- Selección explícita de postura ortostática: **bipedestación / parado**.
- Gráfico de **IC e IRV vs edad gestacional** con punto del paciente.
- Gráfico de cuadrantes **z-IC / z-IRV** con punto del paciente.
- Análisis ortostático con:
  - Flecha de desplazamiento **acostada/supino → parado/bipedestación** en plano IC/IRV.
  - Barras comparativas de IC, IRV, CA, IH/IAC y FC.
  - Tabla de delta y delta porcentual.
- Diagnóstico convencional + diagnóstico ML hemodinámico interno.
- Informe PDF médico con gráficos, logo institucional y firma/sello.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Recomendación de uso

1. Abrir la pestaña **PDF Z-Logic doble**.
2. Cargar los dos PDF juntos en el primer selector, o por separado en los dos selectores.
3. Presionar **IMPORTAR E INTEGRAR INFORME COMPLETO + INFORME DE 4 HOJAS**.
4. Verificar las posiciones detectadas y, si hace falta, seleccionar manualmente cuál es acostada/supino y cuál es parado/bipedestación.
5. Confirmar variables en la grilla.
6. Generar informe médico integrado.
