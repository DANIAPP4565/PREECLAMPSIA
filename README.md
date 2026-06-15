# App Preeclampsia ICG Z-Logic — DOS PDF obligatorios

Versión 2026-06-15.

## Cambio crítico

La pestaña **PDF Z-Logic: DOS INFORMES** obliga a importar dos archivos PDF separados:

1. **PDF COMPLETO Z-Logic**  
   Botón: **1. IMPORTAR INFORME COMPLETO Z-LOGIC**

2. **PDF Z-Logic DE 4 HOJAS**  
   Botón: **2. IMPORTAR INFORME DE 4 HOJAS**

3. Luego se habilita:  
   **3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS**

La app bloquea el análisis si falta cualquiera de los dos PDF.

## Correcciones incluidas

- Se eliminó el flujo de un solo PDF desde el `main()`.
- Se corrigió `StreamlitValueBelowMinError` en edad gestacional: cualquier valor detectado fuera de rango se limita entre 5 y 42 semanas.
- Se agregó parser dirigido para el informe **COMPLETO**, evitando tomar valores de referencia como si fueran del paciente.
- Se agregaron variables complementarias del informe **DE 4 HOJAS**: CFTnr, EA, EES, AC y ortostatismo.
- Se genera tabla de delta y gráfico de desplazamiento **acostado → parado** en cuadrante IC/IRV.

## Prueba con los ejemplos aportados

Con los dos PDF de Riegel Yanina:

- Acostado integrado: IC 5.7, IRV 1095, CA 4.38, IAC 304, CTS 0.36, ITC 6.1, CFT 55.4, CFTnr 129.5, EA 0.59, EES 0.96, AC 0.61.
- Parado: IC 3.2, IRV 2097, CA 2.85, CFTnr 104.5, EA 1.28, EES 1.24, AC 1.02.
- Ortostatismo: IC desciende e IRV aumenta.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
