# App PE Hemodinámica ICG Z-Logic — versión corregida J48 Olano 2025

App Streamlit para predicción, fenotipo hemodinámico, manejo clínico y generación de informe PDF en preeclampsia usando informes Z-Logic/ICG.

## Correcciones de esta versión

- Corrige `StreamlitDuplicateElementId` asignando claves únicas a todos los formularios repetidos entre pestañas.
- Elimina la carga manual de puntos de corte del ML: los criterios quedan incorporados como base de conocimiento interna.
- Agrega botón explícito **Importar informe completo Z-Logic de 4 hojas e integrar**.
- La importación PDF alimenta directamente datos demográficos, variables hemodinámicas, diagnóstico convencional, diagnóstico ML y PDF médico.

## Funciones

- Importa PDF Z-Logic de informe completo de 4 hojas.
- Extrae automáticamente variables hemodinámicas: IC, IRV, RVS, CA/ICA/ACI, ITC/ITS, CTE, CTS/STR, IH, IAC/IA, CFT, EA, EES/ELV, EA/EES, FC y PA.
- Permite corregir manualmente las variables extraídas.
- Grafica IC e IRV frente a edad gestacional con banda de referencia incorporada.
- Clasifica fenotipo hemodinámico convencional por IC/IRV ajustados a edad gestacional.
- Aplica score operativo global de ML hemodinámico.
- Agrega diagnóstico ML J48 Olano 2025 para discriminar PE temprana vs PE tardía con STR/CTS, IA/IAC, ELV/EES y ACI/CA.
- Muestra la ruta de decisión del árbol en pantalla, PDF, Markdown y Excel.
- Genera PDF médico con logo institucional y firma/sello.
- Exporta Excel y Markdown.
- Procesa lote Excel/CSV.

## Reglas J48 incorporadas

- STR > 43,37% → PE tardía.
- STR ≤ 43,37% e IA ≤ 190,87 → PE tardía.
- STR ≤ 43,37%, IA > 190,87 y ELV > 1,53 → PE temprana.
- STR ≤ 43,37%, IA > 190,87, ELV ≤ 1,53 y STR > 41,21% → PE temprana.
- Si STR ≤ 41,21%, ACI ≤ 1,30 → PE tardía.
- Si STR ≤ 41,21%, ACI 1,30–1,51 → PE temprana.
- Si STR ≤ 41,21%, ACI > 1,51 → PE tardía.

## Uso

1. Abrir la pestaña **PDF Z-Logic**.
2. Cargar el PDF de informe completo de 4 hojas.
3. Presionar **Importar informe completo Z-Logic de 4 hojas e integrar**.
4. Confirmar posición basal, edad gestacional y variables detectadas.
5. Presionar **Analizar y generar informe médico integrado**.
6. Descargar PDF, Excel o Markdown.

## Instalación

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Nota clínica

El árbol J48 publicado se incorporó como subdiagnóstico de PE temprana/tardía. El nodo inicial que separa No PE no queda operacionalizado en el texto extraído del artículo; por seguridad, la app conserva un score global operativo como compuerta de riesgo. Para uso científico-publicable debe incorporarse el árbol Weka completo o un modelo calibrado con la base local, con ROC, calibración, DCA y auditoría de falsos positivos/negativos.
