# App Preeclampsia Z-Logic ICG

Versión final corregida: integración doble PDF Z-Logic.

## Cambios principales

- La pestaña **PDF Z-Logic** ahora tiene dos cargadores separados:
  1. **CARGAR INFORME COMPLETO Z-LOGIC**
  2. **CARGAR INFORME Z-LOGIC DE 4 HOJAS**
- El botón principal integra ambos PDF:
  **IMPORTAR E INTEGRAR INFORME COMPLETO + INFORME DE 4 HOJAS**
- Los datos de ambos informes se complementan: si una variable está en uno solo, se incorpora automáticamente.
- Si una variable aparece en ambos con valores diferentes, se muestra una tabla de auditoría de conflictos para corrección manual.
- Se normalizan posiciones equivalentes:
  - Acostada / decúbito supino / basal / cinta
  - Bipedestación / parado / de pie
- Se genera gráfico de ortostatismo ICG: supino vs bipedestación.
- Se interpreta respuesta ortostática esperada: IC desciende e IRV asciende.
- El PDF médico incluye gráfico IC/IRV por edad gestacional, cuadrante IC/IRV y ortostatismo.
- El ML queda interno, sin pedir puntos de corte manuales.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

Subir `app.py`, `requirements.txt` y este README en la raíz del repositorio.
