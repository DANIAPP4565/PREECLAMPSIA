# App Preeclampsia ICG Z-Logic — doble PDF + ortostatismo

Versión 2026-06-14d.

## Cambio principal
La app ahora exige **dos campos separados** de carga:

1. **INFORME COMPLETO Z-LOGIC**
2. **INFORME Z-LOGIC DE 4 HOJAS**

El botón **IMPORTAR E INTEGRAR INFORME COMPLETO + INFORME DE 4 HOJAS** queda bloqueado hasta que ambos PDF estén cargados. Esto evita que se procese sólo el informe de 4 hojas.

## Integración
- Une variables del informe completo y del informe de 4 hojas.
- Complementa faltantes automáticamente.
- Muestra auditoría de fuentes y conflictos.
- Permite corregir manualmente variables importadas antes del informe.

## Gráficos
- IC e IRV contra edad gestacional.
- Cuadrante IC/IRV con punto del paciente.
- Ortostatismo ICG: comparación y flecha **acostada / decúbito supino → bipedestación / parado**.

## ML
Incluye base de conocimiento interna sin pedir puntos de corte manuales:
- Hemodinamia convencional IC/IRV por edad gestacional.
- Score operativo hemodinámico.
- Subclasificador J48 Olano 2025 para PE temprana/tardía con STR/CTS, IAC/IA, EES/ELV y CA/ACI.

## Ejecución
```bash
pip install -r requirements.txt
streamlit run app.py
```
