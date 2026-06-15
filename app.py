# -*- coding: utf-8 -*-
"""
APP PREECLAMPSIA - HEMODINAMIA NO INVASIVA Z-LOGIC / ICG
Predicción, fenotipo hemodinámico, apoyo clínico-terapéutico e informe médico PDF.

Autor / Desarrollador: Dr. Olano Ricardo Daniel, Cardiólogo Hipertensólogo.
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
# CONFIGURACIÓN Y CONSTANTES DE REFERENCIA
# =========================================================

DEFAULT_MODEL_CONFIG = {
    "version": "2026-06-14k",
    "thresholds": {
        "PAS": 140.0, "PAD": 90.0, "PAM": 105.0,
        "IC_low": 2.5, "IC_high": 4.2,
        "IRV_low": 1400.0, "IRV_high": 2500.0,
        "RVS_low": 800.0, "RVS_high": 1500.0,
        "CA_low": 1.2, "CA_high": 2.2,
        "CFT_high": 45.0, "CFTnr_high": 35.0,
        "EES_high": 2.2, "AC_low": 0.8
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
    "IH": {"label": "Índice de Aceleración (He气息/IH)", "unit": "/s²"},
    "IAC": {"label": "Índice de Amplificación Central", "unit": "%"},
    "IV": {"label": "Índice de Velocidad", "unit": "/s"},
    "CFT": {"label": "Tiempo de Fluido Correcto", "unit": "ms"},
    "CFTnr": {"label": "CFT No Reactivo / Basal", "unit": "ms"},
    "EA": {"label": "Elastancia Arterial (Ea)", "unit": "mmHg/ml"},
    "EES": {"label": "Elastancia Sistólica Final (Ees)", "unit": "mmHg/ml"},
    "AC": {"label": "Acoplamiento Ventrículo-Arterial (Ea/Ees)", "unit": "ratio"},
    "FC": {"label": "Frecuencia Cardíaca", "unit": "bpm"},
    "PAS": {"label": "Presión Arterial Sistólica", "unit": "mmHg"},
    "PAD": {"label": "Presión Arterial Diastólica", "unit": "mmHg"},
    "PAM": {"label": "Presión Arterial Media", "unit": "mmHg"},
    "DS": {"label": "Descarga Sistólica", "unit": "ml"},
    "IDS": {"label": "Índice de Descarga Sistólica", "unit": "ml/m²"},
    "Z0": {"label": "Impedancia Basal (Z0)", "unit": "ohms"},
    "VM": {"label": "Volumen Minuto", "unit": "L/min"}
}

REFERENCE_POINTS = [
    {"Fenotipo": "Hiperdinámico Puro", "IC": "Elevado (>4.2)", "IRV": "Bajo (<1400)", "RVS": "Baja", "Perfil Clínico": "Asociado a fases tempranas de gestación o preeclampsia precoz compensada."},
    {"Fenotipo": "Resistivo / Vasoespasmo", "IC": "Bajo o Normal (<2.8)", "IRV": "Elevado (>2500)", "RVS": "Alta", "Perfil Clínico": "Típico de preeclampsia tardía, disfunción endotelial severa o daño de órgano blanco."},
    {"Fenotipo": "Desacoplado VA", "IC": "Variable", "IRV": "Variable", "RVS": "Variable", "Perfil Clínico": "Relación Ea/Ees alterada (>1.2), sobrecarga miocárdica inminente."}
]

@dataclass
class ValueObject:
    variable: str
    value: float

# =========================================================
# FUNCIONES AUXILIARES DE LIMPIEZA Y PARSEO
# =========================================================

def clean_num(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        s = str(v).replace(",", ".").strip()
        s = re.sub(r"[^\d\.\-]", "", s)
        return float(s) if s else None
    except:
        return None

def normalize_ratio_if_percent(var_name: str, val: float) -> float:
    if var_name in ["CTE", "CTS"] and val > 1.0:
        return val / 100.0
    return val

def inject_css() -> None:
    st.markdown(
        """
        <style>
        .main { background-color: #f8f9fa; }
        .card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metric-title { font-size: 14px; color: #6c757d; font-weight: bold; }
        .metric-value { font-size: 24px; font-weight: bold; color: #1f2937; }
        .footer-note { font-size: 11px; color: #9ca3af; text-align: center; margin-top: 30px; }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_header() -> None:
    st.title("🫀 Sistema Analítico ICG - Predicción de Preeclampsia")
    st.caption("Mapeo Hemodinámico Avanzado, Modelado No Invasivo y Reportes Automatizados Z-Logic")

def load_model_config() -> Dict[str, Any]:
    return DEFAULT_MODEL_CONFIG

def get_logo_and_signature()
