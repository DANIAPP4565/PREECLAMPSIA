# -*- coding: utf-8 -*-
"""
APP PREECLAMPSIA - HEMODINAMIA NO INVASIVA Z-LOGIC / ICG
Predicción, fenotipo hemodinámico, apoyo clínico-terapéutico e informe médico PDF.

Autor / Desarrollador: Dr. Olano Ricardo Daniel, Cardiólogo Hipertensólogo.
Mecánica Vascular - Hospital San Martín de La Plata.
"""

from __future__ import annotations

import base64
import io
import json
import math
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# PDF report
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable
)

# =========================================================
# CONFIGURACIÓN Y CONSTANTES DEL MODELO CLÍNICO
# =========================================================

DEFAULT_MODEL_CONFIG = {
    "version": "2026-06-14k",
    "thresholds": {
        "PAS": 140.0,
        "PAD": 90.0,
        "PAM": 105.0,
        "IC_low": 2.5,
        "IC_high": 4.2,
        "IRV_low": 1400.0,
        "IRV_high": 2500.0,
        "RVS_low": 800.0,
        "RVS_high": 1500.0,
        "CA_low": 1.2,
        "CA_high": 2.2,
        "CFT_high": 45.0,
        "CFTnr_high": 35.0,
        "EES_high": 2.2,
        "AC_low": 0.8
    }
}

VARIABLE_INFO = {
    "IC": {"label": "Índice Cardíaco", "unit": "L/min/m²"},
    "IRV": {"label": "Índice de Resistencia Vascular", "unit": "dyn·seg·cm⁻⁵·m²"},
    "RVS": {"label": "Resistencia Vascular Sistémica", "unit": "dyn·seg·cm⁻⁵"},
    "CA": {"label": "Complacencia Arterial", "unit": "ml/mmHg"},
    "ITC": {"label": "Índice de Trabajo Cardíaco", "unit": "g·m/m²"},
    "CTE": {"label": "Coeficiente de Tiempo de Eyección", "unit": "%"},
    "CTS": {"label": "Coeficiente de Tiempo Sistólico", "unit": "%"},
    "IH": {"label": "Índice de Aceleración", "unit": "/s²"},
    "IAC": {"label": "Índice de Amplificación Central", "unit": "%"},
    "IV": {"label": "Índice de Velocidad", "unit": "/s"},
    "CFT": {"label": "Tiempo de Fluido Correcto", "unit": "ms"},
    "CFTnr": {"label": "CFT No Reactivo / Basal", "unit": "ms"},
    "EA": {"label": "Elastancia Arterial (Ea)", "unit": "mmHg/ml"},
    "EES": {"label": "Elastancia Sistólica Final (Ees)", "unit": "mmHg/ml"},
    "AC": {"label": "Acoplamiento Ventrículo-Arterial", "unit": "ratio"},
    "FC": {"label": "Frecuencia Cardíaca", "unit": "bpm"},
    "PAS": {"label": "Presión Arterial Sistólica", "unit": "mmHg"},
    "PAD": {"label": "Presión Arterial Diastólica", "unit": "mmHg"},
    "PAM": {"label": "Presión Arterial Media", "unit": "mmHg"},
    "DS": {"label": "Descarga Sistólica", "unit": "ml"},
    "IDS": {"label": "Índice de Descarga Sistólica", "unit": "ml/m²"},
    "Z0": {"label": "Impedancia Basal (Z0)", "unit": "ohms"},
    "VM": {"label": "Volumen Minuto", "unit": "L/min"}
}

# SOLUCIÓN DEL ERROR DE SINTAXIS: Línea 98 completamente cerrada y saneada
REFERENCE_POINTS = [
    {"Fenotipo": "Hiperdinámico Puro", "IC": "Elevado (>4.2)", "IRV": "Bajo (<1400)", "RVS": "Baja", "Perfil Clínico": "Asociado a fases tempranas de gestación o preeclampsia precoz compensada. Alto volumen minuto."},
    {"Fenotipo": "Resistivo / Vasoespasmo", "IC": "Bajo o Normal (<2.8)", "IRV": "Elevado (>2500)", "RVS": "Alta", "Perfil Clínico": "Típico de preeclampsia tardía, disfunción endotelial severa o daño de órgano blanco."},
    {"Fenotipo": "Desacoplado VA", "IC": "Variable", "IRV": "
