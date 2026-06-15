# App Preeclampsia ICG Z-Logic

Versión 2026-06-15c.

## Corrección del cuadrante hemodinámico IC/IRV

El cuadrante ya no muestra como ejes principales valores z-score difíciles de interpretar.

Ahora muestra ejes clínicos reales:

- Eje X: índice cardíaco medido, IC, en L/min/m².
- Eje Y: índice de resistencia vascular medido, IRV, en dyn·s·cm⁻5·m².

La app sigue calculando internamente el z-score para clasificar IC e IRV según edad gestacional:

`z = (valor medido - media esperada para la edad gestacional) / DE esperada para la edad gestacional`

En el gráfico se muestran líneas punteadas y bandas que representan el rango esperado para la edad gestacional: media ± 1 DE. El punto del paciente se muestra con los valores reales de IC e IRV.

## Ortostatismo

El gráfico de ortostatismo también quedó en unidades reales:

- Punto acostado: IC e IRV acostado.
- Punto parado: IC e IRV en bipedestación.
- Flecha: desplazamiento acostado → parado.

## Flujo obligatorio

La pestaña PDF Z-Logic mantiene dos importadores obligatorios:

1. PDF COMPLETO Z-Logic.
2. PDF Z-Logic DE 4 HOJAS.

Luego se complementan las variables de ambos informes para el análisis.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
