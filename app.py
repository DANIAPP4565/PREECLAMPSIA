# -*- coding: utf-8 -*-
"""
APP PREECLAMPSIA - HEMODINAMIA NO INVASIVA Z-LOGIC / ICG
Predicción, fenotipo hemodinámico, apoyo clínico-terapéutico e informe médico PDF.

Autor / Desarrollador: Dr. Olano Ricardo Daniel, Cardiólogo Hipertensólogo.

Notas de seguridad clínica:
- Esta herramienta es de apoyo a la decisión clínica. No reemplaza el juicio médico,
  la evaluación obstétrica ni las guías locales vigentes.
- El módulo de Machine Learning Olano 2023 basado en CA/ICA, IC, ITC/ITS, CTE e IH
  estima riesgo general de preeclampsia.
- Se agrega un segundo módulo Olano 2025 para subclasificar el patrón de riesgo como
  preeclampsia temprana o tardía con STR/CTS, IA/IAC, ELV/EES y ACI/CA.
  Para investigación regulatoria/publicación debe validarse contra la base local y
  documentar calibración, ROC, DCA y trazabilidad de falsos positivos/negativos.
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
)

try:
    from reportlab.lib.utils import ImageReader
except Exception:  # pragma: no cover
    ImageReader = None


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="PE Hemodinámica ICG Z-Logic",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "Predicción, manejo clínico y terapéutico de preeclampsia por hemodinamia ICG"
APP_SUBTITLE = "Importación PDF Z-Logic, fenotipo IC/IRV por edad gestacional, reglas convencionales + ML hemodinámico"
AUTHOR = "Dr. Olano Ricardo Daniel - Cardiólogo Hipertensólogo"
APP_VERSION_VISIBLE = "Versión 2026-06-15d · DOS PDF OBLIGATORIOS · ML PE GENERAL OLANO 2023 + SUBTIPO TEMPRANA/TARDÍA OLANO 2025"


DEFAULT_MODEL_CONFIG: Dict[str, Any] = {
    "version": "ZLogic-ICG-PE-v1.4-Olano-2023-General-Olano-2025-Temprana-Tardia",
    "notas": (
        "Modelo ML operativo de riesgo general de preeclampsia basado en las variables "
        "publicadas por Olano et al. 2023: CA/ICA, IC, ITC/ITS, CTE e IH. "
        "Además, se informa en forma separada el submodelo Olano 2025 para orientar "
        "riesgo de PE temprana vs tardía con STR/CTS, IA/IAC, ELV/EES y ACI/CA."
    ),
    "z_ic_bajo": -1.0,
    "z_ic_alto": 1.0,
    "z_irv_alto": 1.0,
    "z_irv_bajo": -1.0,
    "ca_baja": 1.0,
    "ih_bajo": 10.0,
    "cte_alto": 0.42,
    "cts_alto": 0.40,
    "itc_bajo": 3.0,
    "ac_desacoplado": 1.30,
    "prob_bajo": 0.25,
    "prob_alto": 0.60,
    "olano2025_temprana_tardia": {
        "str_alto_tardia": 43.37,
        "ia_baja_tardia": 190.87,
        "elv_alta_temprana": 1.53,
        "str_intermedia_temprana": 41.21,
        "aci_baja_tardia": 1.30,
        "aci_intermedia_temprana": 1.51,
    },
    "pesos_pe_general": {
        "ca_baja": 1.25,
        "ic_anormal": 1.10,
        "itc_bajo": 0.95,
        "cte_alto": 0.90,
        "ih_bajo": 1.00,
        "hta": 0.70,
        "proteinuria_o_disfuncion": 1.00,
        "perfil_hemodinamico_alterado": 0.65,
        "ac_desacoplado": 0.40,
    },
}

# Banda fisiológica editable por defecto. Debe calibrarse con base local.
REFERENCE_POINTS = pd.DataFrame(
    {
        "semana": [10, 12, 16, 20, 24, 28, 32, 36, 40],
        "ic_media": [2.80, 3.00, 3.35, 3.80, 4.15, 4.35, 4.25, 4.00, 3.80],
        "ic_sd": [0.45, 0.45, 0.48, 0.50, 0.52, 0.52, 0.52, 0.50, 0.50],
        "irv_media": [2300, 2150, 1900, 1650, 1450, 1350, 1450, 1600, 1750],
        "irv_sd": [320, 310, 300, 280, 260, 260, 280, 300, 320],
    }
)

VARIABLE_INFO: Dict[str, Dict[str, str]] = {
    "IC": {"label": "Índice cardíaco", "unit": "L/min/m²", "group": "Flujo"},
    "IRV": {"label": "Índice de resistencia vascular", "unit": "dyn·s·cm⁻5·m²", "group": "Poscarga"},
    "RVS": {"label": "Resistencia vascular sistémica", "unit": "dyn·s·cm⁻5", "group": "Poscarga"},
    "CA": {"label": "Índice de complacencia/compliance arterial", "unit": "mL/mmHg/m²", "group": "Complacencia"},
    "ITC": {"label": "Índice de trabajo cardíaco/sistólico", "unit": "kg·m/m²", "group": "Rendimiento"},
    "CTE": {"label": "Cociente de tiempos eyectivos", "unit": "relación", "group": "Tiempos"},
    "CTS": {"label": "Coeficiente tiempos sistólicos", "unit": "relación", "group": "Tiempos"},
    "IH": {"label": "Índice de Heather", "unit": "Ω/s²", "group": "Contractilidad"},
    "IAC": {"label": "Índice de aceleración", "unit": "100/s²", "group": "Contractilidad"},
    "IV": {"label": "Índice de velocidad", "unit": "1000/s", "group": "Contractilidad"},
    "CFT": {"label": "Contenido de fluido torácico", "unit": "kΩ⁻¹", "group": "Volemia"},
    "CFTnr": {"label": "Contenido de fluido torácico normalizado", "unit": "índice", "group": "Volemia"},
    "EES": {"label": "Elastancia ventricular telesistólica", "unit": "mmHg/mL", "group": "Acoplamiento"},
    "FC": {"label": "Frecuencia cardíaca", "unit": "lpm", "group": "General"},
    "PAS": {"label": "Presión sistólica", "unit": "mmHg", "group": "Presión"},
    "PAD": {"label": "Presión diastólica", "unit": "mmHg", "group": "Presión"},
    "PAM": {"label": "Presión arterial media", "unit": "mmHg", "group": "Presión"},
    "DS": {"label": "Descarga sistólica", "unit": "mL", "group": "Flujo"},
    "IDS": {"label": "Índice de descarga sistólica", "unit": "mL/m²", "group": "Flujo"},
    "Z0": {"label": "Impedancia basal", "unit": "Ω", "group": "Técnico"},
    "VM": {"label": "Volumen minuto / gasto cardíaco", "unit": "L/min", "group": "Flujo"},
    "IMC": {"label": "Índice de masa corporal", "unit": "kg/m²", "group": "Antropometría"},
    "PESO": {"label": "Peso", "unit": "kg", "group": "Antropometría"},
    "TALLA": {"label": "Talla", "unit": "cm", "group": "Antropometría"},
}

# Sinónimos por variable. Se evalúan con límites de palabra para evitar que IC se lea dentro de ITC.
VAR_SYNONYMS: Dict[str, List[str]] = {
    "IC": ["indice cardiaco", "índice cardíaco", "cardiac index", "ci", "ic"],
    "IRV": [
        "indice de resistencia vascular",
        "índice de resistencia vascular",
        "indice resistencia vascular",
        "irv",
        "vri",
        "svri",
        "systemic vascular resistance index",
        "vascular resistance index",
    ],
    "RVS": ["resistencia vascular sistemica", "resistencia vascular sistémica", "rvs", "svr", "tvr", "tpvr", "total vascular resistance"],
    "CA": [
        "indice de complacencia arterial",
        "índice de complacencia arterial",
        "indice de compliance arterial",
        "arterial compliance index",
        "complacencia arterial",
        "compliance arterial",
        "ica",
        "aci arterial",
        "ca",
    ],
    "ITC": [
        "indice de trabajo cardiaco",
        "índice de trabajo cardíaco",
        "indice de trabajo sistolico",
        "índice de trabajo sistólico",
        "cardiac work index",
        "systolic work index",
        "cwi",
        "swi",
        "its",
        "itc",
    ],
    "CTE": ["cociente de tiempos eyectivos", "ejective time ratio", "etr", "cte"],
    "CTS": ["coeficiente de tiempos sistolicos", "coeficiente tiempos sistolicos", "systolic time ratio", "systolic time", "str", "pep/lvet", "cts"],
    "IH": ["indice de heather", "índice de heather", "heather index", "ih", "hi"],
    "IAC": ["indice de aceleracion", "índice de aceleración", "cardiac acceleration index", "acceleration index", "iac", "ia", "acceleration"],
    "IV": ["indice de velocidad", "índice de velocidad", "velocity index", "iv"],
    "CFTnr": ["cftnr", "cft nr", "tfc index", "thoracic fluid index", "contenido de fluidos toracicos normalizado"],
    "CFT": ["contenido de fluido toracico", "contenido de fluidos toracicos", "contenido de fluido torácico", "thoracic fluid content", "tfc", "cft"],
    "EES": ["elastancia telesistolica", "elastancia ventricular", "end systolic elastance", "end-systolic ventricular elastance", "left ventricular end systolic elastance", "left ventricular end-systolic elastance", "elv", "ees"],
    "FC": ["frecuencia cardiaca", "frecuencia cardíaca", "heart rate", "hr", "fc"],
    "PAS": ["presion sistolica", "presión sistólica", "systolic blood pressure", "sbp", "pas"],
    "PAD": ["presion diastolica", "presión diastólica", "diastolic blood pressure", "dbp", "pad"],
    "PAM": ["presion arterial media", "presión arterial media", "mean arterial pressure", "map", "pam"],
    "DS": ["descarga sistolica", "descarga sistólica", "stroke volume", "sv", "ds"],
    "IDS": ["indice de descarga sistolica", "índice de descarga sistólica", "stroke index", "si", "ids"],
    "Z0": ["impedancia basal", "basal impedance", "z0"],
    "VM": ["volumen minuto", "gasto cardiaco", "gasto cardíaco", "cardiac output", "co", "vm"],
    "IMC": ["indice de masa corporal", "índice de masa corporal", "body mass index", "bmi", "imc"],
    "PESO": ["peso", "weight"],
    "TALLA": ["talla", "height", "estatura"],
}

PLAUSIBLE_RANGES: Dict[str, Tuple[float, float]] = {
    "IC": (0.8, 8.0),
    "IRV": (500, 6500),
    "RVS": (300, 3500),
    "CA": (0.1, 10.0),
    "ITC": (0.1, 20.0),
    "CTE": (0.05, 100.0),
    "CTS": (0.05, 100.0),
    "IH": (0.1, 80.0),
    "IAC": (0.1, 700.0),
    "IV": (0.1, 200.0),
    "CFT": (5, 120),
    "CFTnr": (1, 200),
    "EES": (0.05, 20.0),
    "FC": (35, 190),
    "PAS": (60, 260),
    "PAD": (30, 160),
    "PAM": (40, 180),
    "DS": (10, 250),
    "IDS": (5, 150),
    "Z0": (5, 100),
    "VM": (0.5, 25),
    "IMC": (12, 70),
    "PESO": (30, 200),
    "TALLA": (120, 210),
}

BLOCKERS: Dict[str, List[str]] = {
    "IC": ["itc", "indice de trabajo", "trabajo cardiaco", "trabajo cardíaco", "cft", "tfc", "iac", "ih", "cts", "cte", "ca", "irv"],
    "CA": ["cardiaco", "cardíaco", "cardiac index", "cardiac output", "iac", "aceleracion", "acceleration"],
    "IAC": ["compliance", "complacencia", "arterial compliance"],
}


# =========================================================
# ESTILO VISUAL
# =========================================================

def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        html, body, .stApp {font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;}
        .stApp {background: linear-gradient(180deg, #f1f7fb 0%, #f8fbfd 100%);}        
        .block-container {padding-top: 1rem; padding-bottom: 3rem; max-width: 1320px;}
        .hero {background: linear-gradient(135deg, #062a47 0%, #0e5f88 65%, #16a085 100%); color: white; border-radius: 22px; padding: 28px 32px; margin-bottom: 20px; box-shadow: 0 12px 34px rgba(8, 42, 71, .18);}        
        .hero h1 {color: white !important; font-size: 1.85rem; margin: 0 0 4px 0;}
        .hero p {color: rgba(255,255,255,.92); margin: 0; font-size: 1rem;}
        .card {background: white; border: 1px solid #dbe7ef; border-radius: 18px; padding: 18px 20px; box-shadow: 0 4px 18px rgba(15,23,42,.06); margin-bottom: 16px;}
        .kpi {background: white; border: 1px solid #dbe7ef; border-radius: 16px; padding: 14px 16px; min-height: 105px; box-shadow: 0 2px 10px rgba(15,23,42,.05);}        
        .kpi .label {font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; color: #64748b; font-weight: 700;}
        .kpi .value {font-size: 1.35rem; color: #0f172a; font-weight: 800; margin-top: 4px;}
        .kpi .sub {font-size: .82rem; color: #64748b; margin-top: 4px;}
        .pill {display:inline-block; padding:4px 10px; border-radius:999px; font-weight:700; font-size:.82rem;}
        .pill-ok {background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0;}
        .pill-warn {background:#fffbeb; color:#92400e; border:1px solid #fde68a;}
        .pill-bad {background:#fef2f2; color:#991b1b; border:1px solid #fecaca;}
        .pill-info {background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe;}
        .muted {color:#64748b;}
        .small {font-size:.85rem;}
        .footer-note {font-size:.78rem; color:#64748b;}
        section[data-testid="stSidebar"] {background:#eef5f8; border-right: 1px solid #dbe7ef;}
        .stButton>button, .stDownloadButton>button {border-radius: 12px !important; font-weight: 700 !important;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# UTILIDADES GENERALES
# =========================================================

def normalize_text(s: Any) -> str:
    s = str(s or "").lower()
    table = str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"})
    s = s.translate(table)
    s = s.replace("\u00ad", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float, np.number)):
        if pd.isna(x):
            return None
        return float(x)
    s = str(x).strip()
    if not s or s.lower() in {"nan", "none", "null", "sd", "no disponible"}:
        return None
    s = s.replace(" ", "")
    # Quita unidades adheridas pero conserva signos y separadores.
    s = re.sub(r"[^0-9,\.\-+]", "", s)
    if not s or s in {"-", "+", ".", ","}:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None




def clamp_value(value: Any, min_value: float, max_value: float, default: float) -> float:
    """Devuelve un valor seguro para widgets de Streamlit.

    Evita StreamlitValueBelowMinError / AboveMaxError cuando el parser del PDF
    detecta un valor no válido, por ejemplo una edad gestacional <5.
    """
    v = clean_num(value)
    if v is None or not math.isfinite(float(v)):
        return float(default)
    return float(max(min_value, min(max_value, float(v))))


def clamp_int_value(value: Any, min_value: int, max_value: int, default: int) -> int:
    v = clamp_value(value, float(min_value), float(max_value), float(default))
    return int(round(v))

def fmt_num(x: Any, dec: int = 2, suffix: str = "") -> str:
    v = clean_num(x)
    if v is None:
        return "No disponible"
    return f"{v:.{dec}f}{suffix}".replace(".", ",")


def extract_numbers(text: Any) -> List[float]:
    nums = re.findall(r"[-+]?\d+(?:[\.,]\d+)?", str(text or ""))
    out: List[float] = []
    for n in nums:
        v = clean_num(n)
        if v is not None:
            out.append(v)
    return out


def plausible(var: str, value: Any) -> bool:
    v = clean_num(value)
    if v is None:
        return False
    lo, hi = PLAUSIBLE_RANGES.get(var, (-math.inf, math.inf))
    return lo <= v <= hi


def synonym_match(line_norm: str, synonym: str) -> bool:
    s = normalize_text(synonym)
    if len(s) <= 4 or s in {"ic", "ci", "ca", "ea", "ac", "iv", "ih", "hi", "fc", "hr", "co", "vm", "sv", "si"}:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(s)}(?![a-z0-9])", line_norm))
    return s in line_norm


def line_has_var(line: str, var: str) -> bool:
    ln = normalize_text(line)
    for blocker in BLOCKERS.get(var, []):
        if synonym_match(ln, blocker):
            # Solo bloquear cuando el blocker aparece como etiqueta fuerte.
            return False
    return any(synonym_match(ln, syn) for syn in VAR_SYNONYMS.get(var, []))


def normalize_ratio_if_percent(var: str, value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if var in {"CTE", "CTS", "AC"} and value > 2:
        return value / 100.0
    return value


def first_non_empty(*values: Any) -> Optional[Any]:
    for v in values:
        if v is not None and str(v).strip() != "":
            return v
    return None


def sanitize_filename(s: str) -> str:
    s = normalize_text(s)
    s = re.sub(r"[^a-z0-9_\-]+", "_", s).strip("_")
    return s[:80] or "informe"


# =========================================================
# EXTRACCIÓN PDF Z-LOGIC
# =========================================================

@dataclass
class ExtractedValue:
    variable: str
    value: float
    source: str
    page: int
    position: str
    confidence: str = "media"


def pdf_to_pages(uploaded_file: Any) -> List[Dict[str, Any]]:
    """Extrae texto y tablas de un PDF Z-Logic de 4 hojas.

    No usa OCR: se prioriza el PDF digital con texto seleccionable. Si el informe está escaneado,
    la app lo informa para que se cargue una versión digital o se preprocese con OCR externo.
    """
    raw = uploaded_file.read()
    pages: List[Dict[str, Any]] = []

    # pdfplumber: mejor para tablas de informes técnicos.
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                table_lines: List[str] = []
                try:
                    tables = page.extract_tables() or []
                    for table in tables:
                        for row in table or []:
                            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
                            if cells:
                                table_lines.append(" | ".join(cells))
                except Exception:
                    pass
                combined = "\n".join([text] + table_lines).strip()
                pages.append({"page": i, "text": combined, "raw_text": text, "tables": table_lines})
    except Exception:
        pages = []

    # pypdf fallback
    if not any(p.get("text") for p in pages):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                pages.append({"page": i, "text": text, "raw_text": text, "tables": []})
        except Exception:
            pages = []

    return pages


def guess_position(page_text: str, page_num: int) -> str:
    n = normalize_text(page_text)
    if any(x in n for x in ["parado", "de pie", "bipedestacion", "standing", "ortostat"]):
        return "De pie / Parado"
    if any(x in n for x in ["cinta", "supino", "decubito", "decubito dorsal", "acostado", "basal"]):
        return "Acostado / Cinta / Basal"
    if "spot" in n:
        return "Spot"
    return f"Página {page_num}"


def parse_demographics(full_text: str) -> Dict[str, Any]:
    txt = str(full_text or "")
    n = normalize_text(txt)
    info: Dict[str, Any] = {}

    patterns = {
        "paciente": [
            r"(?:paciente|apellido y nombre|nombre y apellido|patient)\s*[:\-–—]\s*([^\n\r|]+)",
            r"(?:apellido\s+y\s+nombre)\s+([^\n\r|]+)",
        ],
        "dni": [r"(?:dni|documento|doc\.?|identificacion)\s*[:\-–—]?\s*([0-9\.]{6,14})"],
        "obra_social": [r"(?:obra social|cobertura|financiador|prepaga)\s*[:\-–—]\s*([^\n\r|]+)"],
        "fecha_estudio": [r"(?:fecha(?: del)? estudio|fecha de estudio|fecha informe|study date)\s*[:\-–—]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"],
        "edad": [r"(?:edad|age)\s*[:\-–—]?\s*(\d{1,3})"],
    }
    for key, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, txt, flags=re.IGNORECASE)
            if m:
                val = m.group(1).strip(" |;,-–—")
                info[key] = val
                break

    # Edad gestacional: soporta S24, 24 semanas, EG 24+3.
    eg_candidates: List[float] = []
    for pat in [
        r"(?:edad gestacional|eg|semanas? de gestacion|semana gestacional)\s*[:\-–—]?\s*(\d{1,2})(?:\s*[+\.]\s*(\d))?",
        r"\bemb\s*s\s*(\d{1,2})(?:\s*[+\.]\s*(\d))?\b",
        r"\bs\s*(\d{1,2})(?:\s*[+\.]\s*(\d))?\b",
        r"(\d{1,2})(?:\s*[+\.]\s*(\d))?\s*semanas",
    ]:
        for m in re.finditer(pat, n, flags=re.IGNORECASE):
            w = clean_num(m.group(1))
            d = clean_num(m.group(2)) if len(m.groups()) > 1 and m.group(2) else 0
            if w is not None and 5 <= w <= 42:
                eg_candidates.append(float(w) + float(d or 0) / 7.0)
    if eg_candidates:
        # Se prioriza el candidato más frecuente; si no, el primero válido.
        info["edad_gestacional"] = round(eg_candidates[0], 2)

    # Presión arterial tipo 120/80 en datos clínicos.
    bp_match = re.search(r"(?:presi[oó]n arterial|pa|bp)\s*[:\-–—]?\s*(\d{2,3})\s*/\s*(\d{2,3})", txt, flags=re.IGNORECASE)
    if bp_match:
        info["PAS"] = clean_num(bp_match.group(1))
        info["PAD"] = clean_num(bp_match.group(2))

    return info


def extract_value_from_line(line: str, var: str) -> Optional[float]:
    if not line_has_var(line, var):
        return None
    ln = normalize_text(line)

    # Reglas de seguridad para IC: no permitir ITC/IAC/IH/CTE/CTS/IRV/CA como fuente.
    if var == "IC":
        strong_label = any(synonym_match(ln, s) for s in ["indice cardiaco", "índice cardíaco", "cardiac index", "ic", "ci"])
        if not strong_label:
            return None

    # Si hay presión 120/80, separar PAS/PAD.
    if var in {"PAS", "PAD"}:
        m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", line)
        if m:
            v = clean_num(m.group(1 if var == "PAS" else 2))
            return v if plausible(var, v) else None

    # Tomar números posteriores a la primera etiqueta reconocida.
    cut_positions: List[int] = []
    for syn in VAR_SYNONYMS.get(var, []):
        s = normalize_text(syn)
        idx = ln.find(s)
        if idx >= 0:
            cut_positions.append(idx + len(s))
    cut = min(cut_positions) if cut_positions else 0
    segment = line[cut:]
    nums = [x for x in extract_numbers(segment) if plausible(var, x)]
    if not nums:
        nums = [x for x in extract_numbers(line) if plausible(var, x)]
    if not nums:
        return None

    # En filas de tabla Z-Logic el valor medido suele estar al final de la fila.
    value = nums[-1]
    value = normalize_ratio_if_percent(var, value)
    return value if plausible(var, value) else None


def parse_variables_from_text(text: str, page: int, position: str) -> List[ExtractedValue]:
    values: List[ExtractedValue] = []
    lines = [l.strip() for l in str(text or "").splitlines() if l.strip()]

    # Parse por línea.
    for line in lines:
        for var in VARIABLE_INFO:
            try:
                v = extract_value_from_line(line, var)
            except Exception:
                v = None
            if v is not None:
                values.append(ExtractedValue(var, float(v), line[:160], page, position, confidence="media"))

    # Deducción PAM si hay PAS/PAD.
    vals_by_var = {v.variable: v.value for v in values}
    if "PAM" not in vals_by_var and "PAS" in vals_by_var and "PAD" in vals_by_var:
        pam = (vals_by_var["PAS"] + 2 * vals_by_var["PAD"]) / 3
        values.append(ExtractedValue("PAM", float(pam), "Calculada desde PAS/PAD", page, position, confidence="alta"))

    return values


def parse_zlogic_pdf(uploaded_file: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    pages = pdf_to_pages(uploaded_file)
    full_text = "\n".join(p.get("text", "") for p in pages)
    demo = parse_demographics(full_text)

    extracted: List[ExtractedValue] = []
    for p in pages:
        pos = guess_position(p.get("text", ""), int(p.get("page", 0)))
        extracted.extend(parse_variables_from_text(p.get("text", ""), int(p.get("page", 0)), pos))

    # Agregar demográficos como variables si fueron detectadas.
    for k in ["PAS", "PAD"]:
        if k in demo and clean_num(demo[k]) is not None:
            extracted.append(ExtractedValue(k, float(clean_num(demo[k])), "Datos demográficos/cabecera", 0, "Cabecera", confidence="media"))

    rows = [ev.__dict__ for ev in extracted]
    return rows, demo, full_text


def collapse_by_position(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Agrupa por posición y conserva el último valor plausible por variable.

    La app muestra todo lo extraído, pero para interpretación se necesita un set único por posición.
    """
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        pos = str(row.get("position") or "Sin posición")
        grouped.setdefault(pos, {})
        var = str(row.get("variable"))
        val = clean_num(row.get("value"))
        if var and val is not None:
            grouped[pos][var] = val
    return grouped


def variables_to_editor_df(var_dict: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for var, meta in VARIABLE_INFO.items():
        rows.append(
            {
                "Variable": var,
                "Nombre": meta["label"],
                "Grupo": meta["group"],
                "Valor": clean_num(var_dict.get(var)),
                "Unidad": meta["unit"],
            }
        )
    return pd.DataFrame(rows)


def editor_df_to_variables(df: pd.DataFrame) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for _, row in df.iterrows():
        var = str(row.get("Variable"))
        val = clean_num(row.get("Valor"))
        if var and val is not None:
            out[var] = float(val)
    # Deducciones útiles.
    if "PAM" not in out and out.get("PAS") and out.get("PAD"):
        out["PAM"] = (out["PAS"] + 2 * out["PAD"]) / 3
    return out


# =========================================================
# REFERENCIAS POR EDAD GESTACIONAL Y CLASIFICACIÓN
# =========================================================

def reference_at_week(week: Optional[float], reference_df: pd.DataFrame = REFERENCE_POINTS) -> Dict[str, float]:
    if week is None or pd.isna(week):
        week = 24.0
    w = float(np.clip(float(week), reference_df["semana"].min(), reference_df["semana"].max()))
    result = {"semana": w}
    for col in ["ic_media", "ic_sd", "irv_media", "irv_sd"]:
        result[col] = float(np.interp(w, reference_df["semana"], reference_df[col]))
    return result


def z_score(value: Optional[float], mean: float, sd: float) -> Optional[float]:
    v = clean_num(value)
    if v is None or sd == 0:
        return None
    return (v - mean) / sd


def classify_level_z(z: Optional[float], low: float = -1.0, high: float = 1.0) -> str:
    if z is None:
        return "No disponible"
    if z <= low:
        return "Bajo para EG"
    if z >= high:
        return "Aumentado para EG"
    return "Normal para EG"


def classify_hemodynamic(vars: Dict[str, float], eg: Optional[float], cfg: Dict[str, Any]) -> Dict[str, Any]:
    ref = reference_at_week(eg)
    ic = clean_num(vars.get("IC"))
    irv = clean_num(vars.get("IRV"))
    rvs = clean_num(vars.get("RVS"))
    zic = z_score(ic, ref["ic_media"], ref["ic_sd"])
    zirv = z_score(irv, ref["irv_media"], ref["irv_sd"])

    ic_level = classify_level_z(zic, cfg.get("z_ic_bajo", -1.0), cfg.get("z_ic_alto", 1.0))
    irv_level = classify_level_z(zirv, cfg.get("z_irv_bajo", -1.0), cfg.get("z_irv_alto", 1.0))

    ic_low = zic is not None and zic <= cfg.get("z_ic_bajo", -1.0)
    ic_high = zic is not None and zic >= cfg.get("z_ic_alto", 1.0)
    irv_high = zirv is not None and zirv >= cfg.get("z_irv_alto", 1.0)
    irv_low = zirv is not None and zirv <= cfg.get("z_irv_bajo", -1.0)

    profile = "No clasificable"
    phenotype = "Datos insuficientes"
    severity = "indeterminado"

    if ic is not None and irv is not None:
        if ic_low and irv_high:
            profile = "HIPODINAMIA"
            phenotype = "IC bajo con IRV elevada para la EG: patrón vasoconstrictor/placentario"
            severity = "alto"
        elif (not ic_low and not ic_high) and irv_high:
            profile = "IC NORMAL CON IRV INADECUADAMENTE ELEVADA"
            phenotype = "Desacople IC/IRV: flujo conservado con poscarga aumentada para la EG"
            severity = "intermedio-alto"
        elif ic_high and irv_low:
            profile = "HIPERDINAMIA"
            phenotype = "IC alto con IRV baja para la EG: patrón hiperdinámico"
            severity = "intermedio"
        elif ic_high and (not irv_high and not irv_low):
            profile = "IC ELEVADO CON IRV NORMAL"
            phenotype = "Hiperflujo relativo sin caída proporcional de IRV"
            severity = "intermedio"
        elif ic_high and irv_high:
            profile = "PATRÓN MIXTO DE ALTO ESTRÉS HEMODINÁMICO"
            phenotype = "IC alto e IRV elevada: respuesta inadecuada, requiere control estrecho"
            severity = "alto"
        elif (not ic_low and not ic_high) and (not irv_high and not irv_low):
            profile = "NORMODINAMIA"
            phenotype = "IC e IRV dentro de banda esperada para la EG"
            severity = "bajo"
        elif ic_low and (not irv_high):
            profile = "IC BAJO SIN IRV ELEVADA"
            phenotype = "Bajo flujo relativo; correlacionar con volemia, FC, anemia y técnica"
            severity = "intermedio"
        else:
            profile = "ALTERACIÓN HEMODINÁMICA NO CLÁSICA"
            phenotype = "Alteración parcial de IC/IRV respecto a edad gestacional"
            severity = "intermedio"

    # Criterio convencional por resistencia total si se dispone RVS/TPVR no indexada.
    conventional_rvs = None
    if rvs is not None:
        if rvs > 1300:
            conventional_rvs = "Hipodinámica por RVS/TPVR >1300 dyn·s·cm⁻5"
        elif rvs < 800:
            conventional_rvs = "Hiperdinámica por RVS/TPVR <800 dyn·s·cm⁻5"
        else:
            conventional_rvs = "Normodinámica por RVS/TPVR 800-1300 dyn·s·cm⁻5"

    return {
        "profile": profile,
        "phenotype": phenotype,
        "severity": severity,
        "ic_level": ic_level,
        "irv_level": irv_level,
        "z_ic": zic,
        "z_irv": zirv,
        "ref": ref,
        "conventional_rvs": conventional_rvs,
    }


def classify_volemia(cft: Optional[float], sex: str = "Mujer") -> str:
    v = clean_num(cft)
    if v is None:
        return "No disponible"
    # Umbral usado en la línea de trabajo ICG: mujeres >24 hipervolémico.
    if sex.lower().startswith("muj") and v > 24:
        return "CFT elevado: patrón hipervolémico relativo"
    if v < 18:
        return "CFT bajo: posible hipovolemia relativa"
    return "CFT dentro de rango operativo"


def classify_clinical(
    eg: Optional[float],
    pas: Optional[float],
    pad: Optional[float],
    proteinuria: bool,
    severe_symptoms: bool,
    platelets_low: bool,
    creatinine_high: bool,
    liver_high: bool,
    pulmonary_edema: bool,
    seizures: bool,
) -> Dict[str, Any]:
    pas = clean_num(pas)
    pad = clean_num(pad)
    after20 = eg is not None and float(eg) >= 20
    hta = (pas is not None and pas >= 140) or (pad is not None and pad >= 90)
    severe_bp = (pas is not None and pas >= 160) or (pad is not None and pad >= 110)
    organ = proteinuria or severe_symptoms or platelets_low or creatinine_high or liver_high or pulmonary_edema

    if seizures:
        diagnosis = "ECLAMPSIA / emergencia obstétrica"
        level = "crítico"
    elif after20 and hta and (severe_bp or severe_symptoms or platelets_low or creatinine_high or liver_high or pulmonary_edema):
        diagnosis = "Preeclampsia con criterios de severidad probable"
        level = "alto"
    elif after20 and hta and organ:
        diagnosis = "Preeclampsia probable"
        level = "alto"
    elif after20 and hta:
        diagnosis = "Hipertensión gestacional / HTA en embarazo sin criterios completos de PE"
        level = "intermedio"
    elif hta:
        diagnosis = "HTA antes de 20 semanas o HTA crónica posible"
        level = "intermedio"
    else:
        diagnosis = "Sin criterio convencional de HTA/PE con los datos ingresados"
        level = "bajo"

    return {
        "diagnosis": diagnosis,
        "level": level,
        "hta": hta,
        "severe_bp": severe_bp,
        "organ": organ,
        "after20": after20,
    }


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def ratio_to_percent_for_olano2025(value: Any) -> Optional[float]:
    """Normaliza STR/CTS a porcentaje para aplicar los umbrales del árbol Olano 2025.

    Z-Logic puede exportar CTS como 36 o como 0,36. El árbol 2025 usa umbrales
    en escala porcentual, por ejemplo 43,37 y 41,21.
    """
    v = clean_num(value)
    if v is None:
        return None
    return v * 100.0 if v <= 2 else v


def olano2025_temprana_tardia(vars: Dict[str, float], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Submodelo Olano 2025 para orientar riesgo de PE temprana vs tardía.

    Es independiente del modelo Olano 2023 de riesgo general. Usa STR/CTS,
    IA/IAC, ELV/EES y ACI/CA. Devuelve No clasificable si faltan variables.
    """
    jcfg = cfg.get("olano2025_temprana_tardia", {}) or {}
    str_cut_high = float(jcfg.get("str_alto_tardia", 43.37))
    ia_cut = float(jcfg.get("ia_baja_tardia", 190.87))
    elv_cut = float(jcfg.get("elv_alta_temprana", 1.53))
    str_cut_mid = float(jcfg.get("str_intermedia_temprana", 41.21))
    aci_cut_low = float(jcfg.get("aci_baja_tardia", 1.30))
    aci_cut_high = float(jcfg.get("aci_intermedia_temprana", 1.51))

    str_percent = ratio_to_percent_for_olano2025(vars.get("CTS"))
    ia = clean_num(vars.get("IAC"))
    elv = clean_num(vars.get("EES"))
    aci = clean_num(vars.get("CA"))

    missing = []
    if str_percent is None:
        missing.append("STR/CTS")
    if ia is None:
        missing.append("IA/IAC")
    if elv is None:
        missing.append("ELV/EES")
    if aci is None:
        missing.append("ACI/CA")
    if missing:
        return {
            "available": False,
            "category": "NO CLASIFICABLE",
            "classification": "No clasificable por Olano 2025",
            "subtype": "Faltan variables: " + ", ".join(missing),
            "route": "Faltan variables críticas para aplicar el árbol Olano 2025.",
            "variables": {"STR_percent": str_percent, "IA": ia, "ELV": elv, "ACI": aci},
            "model_name": "Olano 2025 - PE temprana vs tardía",
        }

    path = [f"STR/CTS={str_percent:.2f}%"]
    if str_percent > str_cut_high:
        path.append(f"> {str_cut_high:.2f}%")
        cls = "Riesgo orientado a PE tardía"
        subtype = "Predominio PE tardía / materno-metabólica"
        category = "TARDÍA"
    else:
        path.append(f"<= {str_cut_high:.2f}%")
        path.append(f"IA/IAC={ia:.2f}")
        if ia <= ia_cut:
            path.append(f"<= {ia_cut:.2f}")
            cls = "Riesgo orientado a PE tardía"
            subtype = "Predominio PE tardía / materno-metabólica"
            category = "TARDÍA"
        else:
            path.append(f"> {ia_cut:.2f}")
            path.append(f"ELV/EES={elv:.2f}")
            if elv > elv_cut:
                path.append(f"> {elv_cut:.2f}")
                cls = "Riesgo orientado a PE temprana"
                subtype = "Predominio PE temprana / placentaria"
                category = "TEMPRANA"
            else:
                path.append(f"<= {elv_cut:.2f}")
                if str_percent > str_cut_mid:
                    path.append(f"STR/CTS > {str_cut_mid:.2f}%")
                    cls = "Riesgo orientado a PE temprana"
                    subtype = "Predominio PE temprana / placentaria"
                    category = "TEMPRANA"
                else:
                    path.append(f"STR/CTS <= {str_cut_mid:.2f}%")
                    path.append(f"ACI/CA={aci:.2f}")
                    if aci <= aci_cut_low:
                        path.append(f"<= {aci_cut_low:.2f}")
                        cls = "Riesgo orientado a PE tardía"
                        subtype = "Predominio PE tardía / materno-metabólica"
                        category = "TARDÍA"
                    elif aci <= aci_cut_high:
                        path.append(f"> {aci_cut_low:.2f} y <= {aci_cut_high:.2f}")
                        cls = "Riesgo orientado a PE temprana"
                        subtype = "Predominio PE temprana / placentaria"
                        category = "TEMPRANA"
                    else:
                        path.append(f"> {aci_cut_high:.2f}")
                        cls = "Riesgo orientado a PE tardía"
                        subtype = "Predominio PE tardía / materno-metabólica"
                        category = "TARDÍA"

    return {
        "available": True,
        "category": category,
        "classification": cls,
        "subtype": subtype,
        "route": " → ".join(path),
        "variables": {"STR_percent": str_percent, "IA": ia, "ELV": elv, "ACI": aci},
        "model_name": "Olano 2025 - PE temprana vs tardía",
    }


def ml_hemodynamic_risk(vars: Dict[str, float], eg: Optional[float], clinical: Dict[str, Any], hemo: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Riesgo general de preeclampsia por ML hemodinámico Olano 2023.

    El resultado temprano/tardío se informa por separado con el submodelo Olano 2025,
    porque corresponde a otro endpoint y a otro árbol de decisión.
    """
    zic = hemo.get("z_ic")
    ca = clean_num(vars.get("CA"))
    ih = clean_num(vars.get("IH"))
    cte = clean_num(vars.get("CTE"))
    cts = clean_num(vars.get("CTS"))
    itc = clean_num(vars.get("ITC"))

    ic_anormal = zic is not None and (zic <= cfg.get("z_ic_bajo", -1.0) or zic >= cfg.get("z_ic_alto", 1.0))
    perfil_alterado = hemo.get("profile") not in {"NORMODINAMIA", "No clasificable", "Datos insuficientes"}

    flags = {
        "ca_baja": ca is not None and ca < cfg.get("ca_baja", 1.0),
        "ic_anormal": ic_anormal,
        "itc_bajo": itc is not None and itc < cfg.get("itc_bajo", 3.0),
        "cte_alto": (cte is not None and cte > cfg.get("cte_alto", 0.42)) or (cts is not None and cts > cfg.get("cts_alto", 0.40)),
        "ih_bajo": ih is not None and ih < cfg.get("ih_bajo", 10.0),
        "hta": bool(clinical.get("hta")),
        "proteinuria_o_disfuncion": bool(clinical.get("organ")),
        "perfil_hemodinamico_alterado": bool(perfil_alterado),
    }

    score = -2.35
    for flag, weight in cfg.get("pesos_pe_general", {}).items():
        if flags.get(flag):
            score += float(weight)

    p_global = logistic(score)
    if p_global >= cfg.get("prob_alto", 0.60):
        category = "ALTO"
    elif p_global >= cfg.get("prob_bajo", 0.25):
        category = "INTERMEDIO"
    else:
        category = "BAJO"

    drivers = [k for k, v in flags.items() if v]
    scope = "Riesgo general de preeclampsia por Olano 2023. Subtipo temprana/tardía informado aparte por Olano 2025."
    olano2025 = olano2025_temprana_tardia(vars, cfg)
    diagnosis_ml = f"Riesgo general de PE {category}. Olano 2025: {olano2025.get('classification')}"
    return {
        "category": category,
        "subtype": scope,
        "scope": scope,
        "p_global": p_global,
        "drivers": drivers,
        "flags": flags,
        "diagnosis_ml": diagnosis_ml,
        "note": cfg.get("notas", ""),
        "model_name": "Olano 2023 - árbol J48 de riesgo general de PE",
        "variables_modelo": "CA/ICA, IC, ITC/ITS, CTE e IH",
        "olano2025": olano2025,
    }


def therapeutic_recommendations(eg: Optional[float], vars: Dict[str, float], clinical: Dict[str, Any], hemo: Dict[str, Any], ml: Dict[str, Any], low_calcium_intake: bool) -> List[str]:
    recs: List[str] = []
    pas = clean_num(vars.get("PAS"))
    pad = clean_num(vars.get("PAD"))

    if clinical.get("severe_bp") or clinical.get("level") == "crítico":
        recs.append("Derivación/atención obstétrica urgente: PA severa, eclampsia o criterios de severidad requieren manejo hospitalario inmediato.")
    elif clinical.get("hta"):
        recs.append("Confirmar PA con técnica correcta y repetir medición; evaluar proteinuria, plaquetas, creatinina, transaminasas, síntomas neurológicos/visuales y dolor epigástrico.")

    if eg is not None and eg < 34 and ml.get("category") in {"ALTO", "INTERMEDIO"}:
        recs.append("Seguimiento materno-fetal intensificado: PA domiciliaria/MAPA si corresponde, laboratorio seriado, Doppler uterino/umbilical y biomarcadores angiogénicos si están disponibles.")
    if eg is not None and 12 <= eg <= 16 and ml.get("category") in {"ALTO", "INTERMEDIO"}:
        recs.append("Considerar profilaxis con AAS de baja dosis según guías y riesgo obstétrico, idealmente antes de las 16 semanas.")
    elif eg is not None and 16 < eg <= 28 and ml.get("category") == "ALTO":
        recs.append("AAS: revisar indicación según guía local; el mayor beneficio se describe cuando se inicia tempranamente, idealmente antes de 16 semanas.")

    if low_calcium_intake:
        recs.append("Calcio: considerar suplementación si la ingesta dietaria es baja, de acuerdo con guías y tolerancia individual.")

    if clinical.get("hta"):
        recs.append("Tratamiento antihipertensivo en embarazo: seleccionar fármaco seguro según obstetricia/cardiología, comorbilidades, PA y fenotipo hemodinámico.")

    profile = hemo.get("profile", "")
    if "HIPODINAMIA" in profile or "IRV INADECUADAMENTE ELEVADA" in profile:
        recs.append("Fenotipo vasoconstrictor/placentario: evitar interpretar solo la PA; priorizar control de poscarga, perfusión uteroplacentaria y vigilancia de crecimiento fetal.")
    elif "HIPERDINAMIA" in profile or "IC ELEVADO" in profile:
        recs.append("Fenotipo hiperdinámico: correlacionar con IMC, FC, volemia y PA; ajustar estrategia para no agravar taquicardia o hiperflujo.")

    if not recs:
        recs.append("Sin alertas mayores con los datos actuales; mantener control prenatal y repetir ICG si cambia el cuadro clínico o la PA.")
    return recs


# =========================================================
# GRÁFICOS
# =========================================================

def fig_to_png_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()


def plot_ic_irv_vs_eg(vars: Dict[str, float], eg: Optional[float], reference_df: pd.DataFrame = REFERENCE_POINTS) -> Tuple[plt.Figure, bytes]:
    weeks = np.linspace(reference_df["semana"].min(), reference_df["semana"].max(), 200)
    ic_mean = np.interp(weeks, reference_df["semana"], reference_df["ic_media"])
    ic_sd = np.interp(weeks, reference_df["semana"], reference_df["ic_sd"])
    irv_mean = np.interp(weeks, reference_df["semana"], reference_df["irv_media"])
    irv_sd = np.interp(weeks, reference_df["semana"], reference_df["irv_sd"])
    ic = clean_num(vars.get("IC"))
    irv = clean_num(vars.get("IRV"))
    egv = clean_num(eg)

    fig, ax = plt.subplots(1, 2, figsize=(12.8, 4.4))
    ax[0].plot(weeks, ic_mean, linewidth=2.4, label="Media esperada")
    ax[0].fill_between(weeks, ic_mean - ic_sd, ic_mean + ic_sd, alpha=0.18, label="Banda ±1 DE")
    if ic is not None and egv is not None:
        ax[0].scatter([egv], [ic], s=90, zorder=5, label="Paciente")
        ax[0].annotate(f"IC {fmt_num(ic,2)}", (egv, ic), xytext=(8, 8), textcoords="offset points")
    ax[0].set_title("Índice cardíaco vs edad gestacional")
    ax[0].set_xlabel("Edad gestacional (semanas)")
    ax[0].set_ylabel("IC (L/min/m²)")
    ax[0].grid(True, alpha=0.25)
    ax[0].legend(fontsize=8)

    ax[1].plot(weeks, irv_mean, linewidth=2.4, label="Media esperada")
    ax[1].fill_between(weeks, irv_mean - irv_sd, irv_mean + irv_sd, alpha=0.18, label="Banda ±1 DE")
    if irv is not None and egv is not None:
        ax[1].scatter([egv], [irv], s=90, zorder=5, label="Paciente")
        ax[1].annotate(f"IRV {fmt_num(irv,0)}", (egv, irv), xytext=(8, 8), textcoords="offset points")
    ax[1].set_title("IRV vs edad gestacional")
    ax[1].set_xlabel("Edad gestacional (semanas)")
    ax[1].set_ylabel("IRV (dyn·s·cm⁻5·m²)")
    ax[1].grid(True, alpha=0.25)
    ax[1].legend(fontsize=8)
    fig.suptitle("Hemodinamia materna ajustada por edad gestacional", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig, fig_to_png_bytes(fig)


def plot_quadrant(hemo: Dict[str, Any]) -> Tuple[plt.Figure, bytes]:
    zic = hemo.get("z_ic")
    zirv = hemo.get("z_irv")
    fig, ax = plt.subplots(figsize=(6.0, 5.2))
    ax.axhline(0, linewidth=1.2)
    ax.axvline(0, linewidth=1.2)
    ax.axhline(1, linestyle="--", linewidth=0.9)
    ax.axhline(-1, linestyle="--", linewidth=0.9)
    ax.axvline(1, linestyle="--", linewidth=0.9)
    ax.axvline(-1, linestyle="--", linewidth=0.9)
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    ax.set_xlabel("z IC por EG")
    ax.set_ylabel("z IRV por EG")
    ax.set_title("Cuadrante hemodinámico IC/IRV")
    ax.text(-2.7, 2.6, "Hipodinamia\nIC bajo / IRV alta", fontsize=8, va="top")
    ax.text(1.05, -2.6, "Hiperdinamia\nIC alto / IRV baja", fontsize=8, va="bottom")
    ax.text(-0.9, 2.6, "IC normal\nIRV alta", fontsize=8, va="top")
    ax.text(0.2, 0.15, "Normodinamia", fontsize=9, fontweight="bold")
    if zic is not None and zirv is not None:
        ax.scatter([float(zic)], [float(zirv)], s=120, zorder=5)
        ax.annotate("Paciente", (float(zic), float(zirv)), xytext=(8, 8), textcoords="offset points")
    ax.grid(True, alpha=0.20)
    fig.tight_layout()
    return fig, fig_to_png_bytes(fig)


def plot_quadrant_clinical(vars: Dict[str, float], eg: Optional[float], hemo: Dict[str, Any]) -> Tuple[plt.Figure, bytes]:
    """Cuadrante clínico con ejes reales, no z-score.

    Eje X = IC medido (L/min/m²). Eje Y = IRV medido (dyn·s·cm⁻5·m²).
    Las líneas punteadas marcan el rango esperado para la edad gestacional:
    media ± 1 DE. La clasificación interna sigue usando z-score, pero el
    gráfico se muestra en unidades clínicas para que sea interpretable.
    """
    egv = clean_num(eg)
    ref = reference_at_week(egv)
    ic = clean_num(vars.get("IC"))
    irv = clean_num(vars.get("IRV"))
    ic_low = ref["ic_media"] - ref["ic_sd"]
    ic_high = ref["ic_media"] + ref["ic_sd"]
    irv_low = ref["irv_media"] - ref["irv_sd"]
    irv_high = ref["irv_media"] + ref["irv_sd"]

    x_vals = [ic_low, ic_high]
    y_vals = [irv_low, irv_high]
    if ic is not None:
        x_vals.append(ic)
    if irv is not None:
        y_vals.append(irv)
    x_min = max(0.5, min(x_vals) - 0.8)
    x_max = max(x_vals) + 0.8
    y_min = max(400, min(y_vals) - 450)
    y_max = max(y_vals) + 450

    fig, ax = plt.subplots(figsize=(7.0, 5.6))
    ax.axvspan(ic_low, ic_high, alpha=0.12, label="IC esperado para EG")
    ax.axhspan(irv_low, irv_high, alpha=0.12, label="IRV esperado para EG")
    ax.axvline(ic_low, linestyle="--", linewidth=1.0)
    ax.axvline(ic_high, linestyle="--", linewidth=1.0)
    ax.axhline(irv_low, linestyle="--", linewidth=1.0)
    ax.axhline(irv_high, linestyle="--", linewidth=1.0)

    # Punto de referencia central esperado.
    ax.scatter([ref["ic_media"]], [ref["irv_media"]], s=45, marker="x", label="Media esperada EG", zorder=4)

    if ic is not None and irv is not None:
        ax.scatter([ic], [irv], s=130, zorder=5, label="Paciente")
        ax.annotate(f"Paciente\nIC {fmt_num(ic,2)} / IRV {fmt_num(irv,0)}", (ic, irv), xytext=(10, 10), textcoords="offset points")
    else:
        ax.text(0.5, 0.5, "Faltan IC o IRV para ubicar el punto", transform=ax.transAxes, ha="center", va="center")

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xlabel("Índice cardíaco medido, IC (L/min/m²)")
    ax.set_ylabel("Índice de resistencia vascular medido, IRV (dyn·s·cm⁻5·m²)")
    ax.set_title("Cuadrante hemodinámico IC/IRV con ejes clínicos")

    ax.text(x_min + 0.04*(x_max-x_min), y_max - 0.05*(y_max-y_min), "Bajo flujo / alta resistencia\nhipodinamia", fontsize=8, va="top")
    ax.text(x_max - 0.38*(x_max-x_min), y_min + 0.08*(y_max-y_min), "Alto flujo / baja resistencia\nhiperdinamia", fontsize=8, va="bottom")
    ax.text(ic_low, y_min + 0.01*(y_max-y_min), f"IC bajo\n<{fmt_num(ic_low,2)}", fontsize=7, ha="right", va="bottom")
    ax.text(ic_high, y_min + 0.01*(y_max-y_min), f"IC alto\n>{fmt_num(ic_high,2)}", fontsize=7, ha="left", va="bottom")
    ax.text(x_min + 0.01*(x_max-x_min), irv_low, f"IRV bajo <{fmt_num(irv_low,0)}", fontsize=7, va="top")
    ax.text(x_min + 0.01*(x_max-x_min), irv_high, f"IRV alto >{fmt_num(irv_high,0)}", fontsize=7, va="bottom")

    footer = (
        f"EG usada: {fmt_num(ref['semana'],1)} sem. Rango esperado = media ±1DE: "
        f"IC {fmt_num(ic_low,2)}-{fmt_num(ic_high,2)}; IRV {fmt_num(irv_low,0)}-{fmt_num(irv_high,0)}. "
        f"La app calcula internamente z = (valor - media EG) / DE EG."
    )
    ax.text(0.5, -0.20, footer, transform=ax.transAxes, ha="center", va="top", fontsize=7.5, wrap=True)
    ax.grid(True, alpha=0.22)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    return fig, fig_to_png_bytes(fig)


def render_quadrant_explanation(hemo: Dict[str, Any]) -> None:
    ref = hemo.get("ref", {}) or {}
    zic = hemo.get("z_ic")
    zirv = hemo.get("z_irv")
    st.caption(
        "El cuadrante ahora muestra unidades reales: eje X = IC en L/min/m² y eje Y = IRV en dyn·s·cm⁻5·m². "
        "Las bandas punteadas son el rango esperado para la edad gestacional. "
        "Para clasificar bajo/normal/alto, la app calcula z-score interno: z = (valor medido − media esperada para EG) / DE esperada."
    )
    if ref:
        st.caption(
            f"Referencia usada: EG {fmt_num(ref.get('semana'),1)} sem; "
            f"IC media {fmt_num(ref.get('ic_media'),2)} ± {fmt_num(ref.get('ic_sd'),2)}; "
            f"IRV media {fmt_num(ref.get('irv_media'),0)} ± {fmt_num(ref.get('irv_sd'),0)}. "
            f"zIC={fmt_num(zic,2)}; zIRV={fmt_num(zirv,2)}."
        )


# =========================================================
# REPORTE PDF / EXPORTACIONES
# =========================================================

def image_file_from_bytes(image_bytes: Optional[bytes], suffix: str = ".png") -> Optional[str]:
    if not image_bytes:
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(image_bytes)
    tmp.flush()
    tmp.close()
    return tmp.name


def pil_compatible_bytes(upload: Any) -> Optional[bytes]:
    if upload is None:
        return None
    try:
        return upload.read()
    except Exception:
        try:
            return upload.getvalue()
        except Exception:
            return None


def make_pdf_report(
    patient: Dict[str, Any],
    vars: Dict[str, float],
    hemo: Dict[str, Any],
    clinical: Dict[str, Any],
    ml: Dict[str, Any],
    recommendations: List[str],
    fig_ic_irv_bytes: bytes,
    fig_quad_bytes: bytes,
    logo_bytes: Optional[bytes] = None,
    firma_bytes: Optional[bytes] = None,
    medico: str = AUTHOR,
    institucion: str = "",
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.35 * cm,
        leftMargin=1.35 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title="Informe hemodinámico preeclampsia ICG",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#0B3D6E"), fontSize=15, leading=18))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#0B3D6E"), fontSize=11, leading=13, spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=9, leading=11))

    story: List[Any] = []

    logo_path = image_file_from_bytes(logo_bytes) if logo_bytes else None
    if logo_path:
        try:
            story.append(RLImage(logo_path, width=3.0 * cm, height=1.8 * cm, kind="proportional"))
        except Exception:
            pass

    story.append(Paragraph("INFORME MÉDICO - HEMODINAMIA MATERNA ICG Y RIESGO DE PREECLAMPSIA", styles["TitleCenter"]))
    if institucion:
        story.append(Paragraph(str(institucion), styles["Small"]))
    story.append(Spacer(1, 0.12 * cm))

    patient_rows = [
        ["Paciente", patient.get("paciente", "No disponible"), "DNI", patient.get("dni", "SD")],
        ["Fecha", patient.get("fecha_estudio", datetime.now().strftime("%d/%m/%Y")), "Edad gestacional", f"{fmt_num(patient.get('edad_gestacional'), 1)} semanas"],
        ["Médico", medico, "Obra social", patient.get("obra_social", "No disponible")],
    ]
    t = Table(patient_rows, colWidths=[2.2 * cm, 6.8 * cm, 3.0 * cm, 5.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F8FB")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
    ]))
    story.append(t)

    story.append(Paragraph("1. Resultado integrado", styles["Section"]))
    summary_rows = [
        ["Diagnóstico clínico convencional", clinical.get("diagnosis", "No disponible")],
        ["Fenotipo hemodinámico IC/IRV", hemo.get("profile", "No disponible")],
        ["Interpretación", hemo.get("phenotype", "No disponible")],
        ["Modelo ML hemodinámico", f"{ml.get('model_name', 'Olano 2023 - árbol J48 de riesgo general de PE')}"],
        ["Variables del modelo", ml.get('variables_modelo', 'CA/ICA, IC, ITC/ITS, CTE e IH')],
        ["Alcance del ML", ml.get('scope', 'Riesgo general de preeclampsia por Olano 2023; subtipo por Olano 2025.')],
        ["Resultado ML Olano 2023", f"Riesgo general de PE: {ml.get('category')}"],
        ["Probabilidad operativa", f"{ml.get('p_global', 0):.0%}"],
        ["Submodelo Olano 2025", f"{ml.get('olano2025', {}).get('classification', 'No disponible')} - {ml.get('olano2025', {}).get('subtype', '')}"],
        ["Ruta Olano 2025", ml.get('olano2025', {}).get('route', 'No disponible')],
    ]
    t2 = Table(summary_rows, colWidths=[5.1 * cm, 12.0 * cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF3FB")),
        ("BACKGROUND", (1, 0), (1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t2)

    story.append(Paragraph("2. Variables hemodinámicas principales", styles["Section"]))
    key_vars = ["IC", "IRV", "RVS", "CA", "ITC", "CTE", "CTS", "IH", "IAC", "CFT", "EES", "FC", "PAS", "PAD"]
    rows = [["Variable", "Valor", "Unidad", "Interpretación"]]
    for var in key_vars:
        if var in vars and clean_num(vars[var]) is not None:
            interp = ""
            if var == "IC":
                interp = hemo.get("ic_level", "")
            elif var == "IRV":
                interp = hemo.get("irv_level", "")
            elif var == "CFT":
                interp = classify_volemia(vars.get(var))
            rows.append([f"{var} - {VARIABLE_INFO[var]['label']}", fmt_num(vars[var], 2 if var not in {"IRV", "RVS", "FC", "PAS", "PAD"} else 0), VARIABLE_INFO[var]["unit"], interp])
    t3 = Table(rows, colWidths=[6.0 * cm, 2.2 * cm, 3.8 * cm, 5.0 * cm], repeatRows=1)
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3D6E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t3)

    story.append(Paragraph("3. Gráficos", styles["Section"]))
    fig1_path = image_file_from_bytes(fig_ic_irv_bytes)
    fig2_path = image_file_from_bytes(fig_quad_bytes)
    if fig1_path:
        story.append(RLImage(fig1_path, width=17.0 * cm, height=6.0 * cm, kind="proportional"))
    if fig2_path:
        story.append(RLImage(fig2_path, width=9.0 * cm, height=7.2 * cm, kind="proportional"))

    story.append(Paragraph("4. Conducta sugerida / apoyo terapéutico", styles["Section"]))
    for r in recommendations:
        story.append(Paragraph(f"• {r}", styles["Body"]))

    story.append(Paragraph("5. Base de conocimiento incorporada", styles["Section"]))
    kb = (
        "El módulo hemodinámico usa IC/IRV ajustados por edad gestacional y variables de ICG asociadas al modelo de ML "
        "(CA/ICA, IC, ITC/ITS, CTE e IH). La probabilidad mostrada es operativa e incorporada como base de conocimiento; para uso científico debe "
        "reemplazarse por el árbol J48 Olano 2023/modelo calibrado exacto de riesgo general de PE y validado localmente."
    )
    story.append(Paragraph(kb, styles["Small"]))

    firma_path = image_file_from_bytes(firma_bytes) if firma_bytes else None
    story.append(Spacer(1, 0.25 * cm))
    if firma_path:
        try:
            story.append(RLImage(firma_path, width=5.0 * cm, height=2.2 * cm, kind="proportional"))
        except Exception:
            pass
    story.append(Paragraph(f"Firma y sello: {medico}", styles["Small"]))
    story.append(Paragraph("Documento generado automáticamente. Debe interpretarse en contexto clínico-obstétrico.", styles["Small"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def to_excel_bytes(results: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([results.get("patient", {})]).to_excel(writer, index=False, sheet_name="Paciente")
        pd.DataFrame([{"Variable": k, "Valor": v, "Nombre": VARIABLE_INFO.get(k, {}).get("label", "")} for k, v in results.get("vars", {}).items()]).to_excel(writer, index=False, sheet_name="Variables")
        pd.DataFrame([results.get("hemo", {})]).to_excel(writer, index=False, sheet_name="Hemodinamia")
        pd.DataFrame([results.get("clinical", {})]).to_excel(writer, index=False, sheet_name="Clinico")
        pd.DataFrame([results.get("ml", {})]).to_excel(writer, index=False, sheet_name="ML")
        pd.DataFrame({"Recomendaciones": results.get("recommendations", [])}).to_excel(writer, index=False, sheet_name="Conducta")
    buf.seek(0)
    return buf.getvalue()


# =========================================================
# COMPONENTES UI
# =========================================================

def render_kpi(label: str, value: str, sub: str = "", level: str = "info") -> None:
    pill_cls = {"ok": "pill-ok", "warn": "pill-warn", "bad": "pill-bad", "info": "pill-info"}.get(level, "pill-info")
    st.markdown(
        f"""
        <div class="kpi">
            <div class="label">{label}</div>
            <div class="value"><span class="pill {pill_cls}">{value}</span></div>
            <div class="sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_level_to_color(level: str) -> str:
    level = (level or "").lower()
    if "alto" in level or "crítico" in level:
        return "bad"
    if "intermedio" in level:
        return "warn"
    return "ok"


def load_model_config() -> Dict[str, Any]:
    """Carga el modelo interno sin solicitar puntos de corte al usuario.

    Los puntos de corte convencionales, la banda IC/IRV por edad gestacional y
    el modelo Olano 2023 de riesgo general queda incorporado como base de conocimiento de la
    app. Esto evita errores de uso y mantiene reproducibilidad clínica.
    """
    cfg = json.loads(json.dumps(DEFAULT_MODEL_CONFIG))
    st.sidebar.markdown("### Modelo ML incorporado")
    st.sidebar.info(
        "La app usa puntos de corte internos de la base de conocimiento: "
        "IC/IRV por edad gestacional, reglas hemodinámicas convencionales y "
        "modelo Olano 2023 de riesgo general. No requiere cargar JSON ni ingresar umbrales."
    )
    return cfg


def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
            <p class="small" style="margin-top:8px;">{AUTHOR}</p>
            <p class="small" style="margin-top:4px; color:#dbeafe;">{APP_VERSION_VISIBLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def demographic_form(defaults: Dict[str, Any], key_prefix: str = "demo") -> Dict[str, Any]:
    st.markdown("#### Datos clínicos y obstétricos")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        paciente = st.text_input("Paciente", value=str(defaults.get("paciente", "")), key=f"{key_prefix}_paciente")
        dni = st.text_input("DNI / ID", value=str(defaults.get("dni", "SD")), key=f"{key_prefix}_dni")
    with c2:
        fecha_estudio = st.text_input("Fecha del estudio", value=str(defaults.get("fecha_estudio", datetime.now().strftime("%d/%m/%Y"))), key=f"{key_prefix}_fecha_estudio")
        edad = st.number_input("Edad materna", min_value=10, max_value=60, value=clamp_int_value(defaults.get("edad"), 10, 60, 30), step=1, key=f"{key_prefix}_edad")
    with c3:
        eg = st.number_input("Edad gestacional (semanas)", min_value=5.0, max_value=42.0, value=clamp_value(defaults.get("edad_gestacional"), 5.0, 42.0, 24.0), step=0.1, key=f"{key_prefix}_eg")
        obra_social = st.text_input("Obra social", value=str(defaults.get("obra_social", "")), key=f"{key_prefix}_obra_social")
    with c4:
        pas = st.number_input("PAS clínica", min_value=70, max_value=260, value=clamp_int_value(defaults.get("PAS"), 70, 260, 120), step=1, key=f"{key_prefix}_pas")
        pad = st.number_input("PAD clínica", min_value=40, max_value=160, value=clamp_int_value(defaults.get("PAD"), 40, 160, 80), step=1, key=f"{key_prefix}_pad")
    return {
        "paciente": paciente or "No disponible",
        "dni": dni or "SD",
        "fecha_estudio": fecha_estudio,
        "edad": edad,
        "edad_gestacional": eg,
        "obra_social": obra_social,
        "PAS": pas,
        "PAD": pad,
    }


def clinical_flags_form(key_prefix: str = "clinical") -> Dict[str, bool]:
    st.markdown("#### Criterios clínicos convencionales")
    c1, c2, c3 = st.columns(3)
    with c1:
        proteinuria = st.checkbox("Proteinuria / PrCr elevado", value=False, key=f"{key_prefix}_proteinuria")
        severe_symptoms = st.checkbox("Cefalea, visuales o dolor epigástrico", value=False, key=f"{key_prefix}_severe_symptoms")
        seizures = st.checkbox("Convulsiones / eclampsia", value=False, key=f"{key_prefix}_seizures")
    with c2:
        platelets_low = st.checkbox("Plaquetas <100.000", value=False, key=f"{key_prefix}_platelets_low")
        creatinine_high = st.checkbox("Creatinina elevada / daño renal", value=False, key=f"{key_prefix}_creatinine_high")
    with c3:
        liver_high = st.checkbox("Transaminasas elevadas / HELLP", value=False, key=f"{key_prefix}_liver_high")
        pulmonary_edema = st.checkbox("Edema pulmonar", value=False, key=f"{key_prefix}_pulmonary_edema")
        low_calcium_intake = st.checkbox("Baja ingesta de calcio", value=False, key=f"{key_prefix}_low_calcium_intake")
    return {
        "proteinuria": proteinuria,
        "severe_symptoms": severe_symptoms,
        "platelets_low": platelets_low,
        "creatinine_high": creatinine_high,
        "liver_high": liver_high,
        "pulmonary_edema": pulmonary_edema,
        "seizures": seizures,
        "low_calcium_intake": low_calcium_intake,
    }


def get_logo_and_signature() -> Tuple[Optional[bytes], Optional[bytes], str, str]:
    st.sidebar.markdown("### Informe PDF")
    medico = st.sidebar.text_input("Médico / firma textual", value=AUTHOR, key="sidebar_medico_firma_textual")
    institucion = st.sidebar.text_input("Institución", value="", key="sidebar_institucion_pdf")
    logo_upload = st.sidebar.file_uploader("Logo institucional", type=["png", "jpg", "jpeg"], key="logo")
    firma_upload = st.sidebar.file_uploader("Firma con sello", type=["png", "jpg", "jpeg"], key="firma")
    logo_bytes = pil_compatible_bytes(logo_upload) if logo_upload is not None else None
    firma_bytes = pil_compatible_bytes(firma_upload) if firma_upload is not None else None
    return logo_bytes, firma_bytes, medico, institucion


def analyze_patient(patient: Dict[str, Any], vars: Dict[str, float], flags: Dict[str, bool], cfg: Dict[str, Any]) -> Dict[str, Any]:
    # Priorizar PA clínica del formulario si existe.
    vars = dict(vars)
    vars["PAS"] = clean_num(patient.get("PAS")) or vars.get("PAS")
    vars["PAD"] = clean_num(patient.get("PAD")) or vars.get("PAD")
    if "PAM" not in vars and vars.get("PAS") and vars.get("PAD"):
        vars["PAM"] = (float(vars["PAS"]) + 2 * float(vars["PAD"])) / 3

    # Estandariza CTE/CTS cuando el PDF o la carga manual vienen en porcentaje.
    for ratio_var in ("CTE", "CTS"):
        if clean_num(vars.get(ratio_var)) is not None:
            vars[ratio_var] = normalize_ratio_if_percent(ratio_var, vars[ratio_var])

    eg = clean_num(patient.get("edad_gestacional"))
    hemo = classify_hemodynamic(vars, eg, cfg)
    clinical = classify_clinical(
        eg=eg,
        pas=vars.get("PAS"),
        pad=vars.get("PAD"),
        proteinuria=flags.get("proteinuria", False),
        severe_symptoms=flags.get("severe_symptoms", False),
        platelets_low=flags.get("platelets_low", False),
        creatinine_high=flags.get("creatinine_high", False),
        liver_high=flags.get("liver_high", False),
        pulmonary_edema=flags.get("pulmonary_edema", False),
        seizures=flags.get("seizures", False),
    )
    ml = ml_hemodynamic_risk(vars, eg, clinical, hemo, cfg)
    recs = therapeutic_recommendations(eg, vars, clinical, hemo, ml, flags.get("low_calcium_intake", False))
    return {"patient": patient, "vars": vars, "hemo": hemo, "clinical": clinical, "ml": ml, "recommendations": recs}


def render_results(results: Dict[str, Any], logo_bytes: Optional[bytes], firma_bytes: Optional[bytes], medico: str, institucion: str) -> None:
    patient = results["patient"]
    vars = results["vars"]
    hemo = results["hemo"]
    clinical = results["clinical"]
    ml = results["ml"]
    recs = results["recommendations"]

    st.markdown("### Resultado automatizado")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_kpi("Clínico", clinical["diagnosis"], f"Nivel: {clinical['level']}", risk_level_to_color(clinical["level"]))
    with k2:
        render_kpi("Fenotipo hemodinámico", hemo["profile"], hemo["phenotype"], risk_level_to_color(hemo["severity"]))
    with k3:
        render_kpi("ML Olano 2023", f"Riesgo {ml['category']}", "Riesgo general de PE", risk_level_to_color(ml["category"]))
    with k4:
        render_kpi("Probabilidad operativa", f"{ml['p_global']:.0%}", "Riesgo general de PE", risk_level_to_color(ml["category"]))
    with k5:
        ol25 = ml.get("olano2025", {})
        render_kpi("Olano 2025", ol25.get("category", "No clas."), ol25.get("classification", "Subtipo temprana/tardía"), risk_level_to_color("intermedio" if ol25.get("available") else "bajo"))
    st.info("La app informa dos salidas separadas: Olano 2023 estima riesgo general de preeclampsia; Olano 2025 orienta el subtipo de riesgo como PE temprana o PE tardía cuando STR/CTS, IA/IAC, ELV/EES y ACI/CA están disponibles.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("IC", fmt_num(vars.get("IC"), 2), hemo.get("ic_level", ""))
    with c2:
        st.metric("IRV", fmt_num(vars.get("IRV"), 0), hemo.get("irv_level", ""))
    with c3:
        st.metric("CA / ICA", fmt_num(vars.get("CA"), 2), "Complacencia arterial")

    fig_ic_irv, fig_ic_irv_bytes = plot_ic_irv_vs_eg(vars, patient.get("edad_gestacional"))
    fig_quad, fig_quad_bytes = plot_quadrant_clinical(vars, patient.get("edad_gestacional"), hemo)
    st.pyplot(fig_ic_irv, clear_figure=False)
    st.pyplot(fig_quad, clear_figure=False)
    render_quadrant_explanation(hemo)

    with st.expander("Detalle de variables y drivers del modelo", expanded=True):
        left, right = st.columns([1.2, 1])
        with left:
            dvar = pd.DataFrame([
                {
                    "Variable": k,
                    "Nombre": VARIABLE_INFO.get(k, {}).get("label", ""),
                    "Valor": v,
                    "Unidad": VARIABLE_INFO.get(k, {}).get("unit", ""),
                }
                for k, v in sorted(vars.items())
            ])
            st.dataframe(dvar, use_container_width=True, hide_index=True)
        with right:
            st.write("**Drivers activos del ML hemodinámico:**")
            if ml["drivers"]:
                for d in ml["drivers"]:
                    st.write(f"- {d}")
            else:
                st.write("Sin drivers mayores detectados.")
            st.caption(ml.get("note", ""))
            st.write("**Alcance del ML:**")
            st.write("- Olano 2023: riesgo general de preeclampsia.")
            st.write("- Olano 2025: subtipo de riesgo temprana/tardía.")
            ol25 = ml.get("olano2025", {})
            st.write("**Submodelo Olano 2025:**")
            st.write(f"- {ol25.get('classification', 'No disponible')}: {ol25.get('subtype', '')}")
            st.write(f"- Ruta: {ol25.get('route', 'No disponible')}")

    with st.expander("Conducta sugerida / apoyo terapéutico", expanded=True):
        for r in recs:
            st.write(f"- {r}")

    pdf_bytes = make_pdf_report(
        patient=patient,
        vars=vars,
        hemo=hemo,
        clinical=clinical,
        ml=ml,
        recommendations=recs,
        fig_ic_irv_bytes=fig_ic_irv_bytes,
        fig_quad_bytes=fig_quad_bytes,
        logo_bytes=logo_bytes,
        firma_bytes=firma_bytes,
        medico=medico,
        institucion=institucion,
    )
    xlsx_bytes = to_excel_bytes(results)
    md = build_markdown_report(results)

    base_name = sanitize_filename(f"PE_ICG_{patient.get('paciente', 'paciente')}_{datetime.now().strftime('%Y%m%d_%H%M')}")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Descargar PDF médico", pdf_bytes, file_name=f"{base_name}.pdf", mime="application/pdf")
    with c2:
        st.download_button("Descargar Excel", xlsx_bytes, file_name=f"{base_name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c3:
        st.download_button("Descargar Markdown", md.encode("utf-8"), file_name=f"{base_name}.md", mime="text/markdown")


def build_markdown_report(results: Dict[str, Any]) -> str:
    p = results["patient"]
    v = results["vars"]
    h = results["hemo"]
    c = results["clinical"]
    m = results["ml"]
    lines = [
        "# Informe hemodinámico ICG - Preeclampsia",
        "",
        f"**Paciente:** {p.get('paciente','No disponible')}",
        f"**Edad gestacional:** {fmt_num(p.get('edad_gestacional'),1)} semanas",
        f"**Diagnóstico clínico:** {c.get('diagnosis')}",
        f"**Fenotipo hemodinámico:** {h.get('profile')} - {h.get('phenotype')}",
        f"**ML hemodinámico Olano 2023:** Riesgo general de PE {m.get('category')} ({m.get('p_global',0):.0%})",
        f"**ML Olano 2025:** {m.get('olano2025', {}).get('classification', 'No disponible')} - {m.get('olano2025', {}).get('subtype', '')}",
        f"**Ruta Olano 2025:** {m.get('olano2025', {}).get('route', 'No disponible')}",
        "",
        "## Variables principales",
        f"- IC: {fmt_num(v.get('IC'),2)} L/min/m² ({h.get('ic_level')})",
        f"- IRV: {fmt_num(v.get('IRV'),0)} dyn·s·cm⁻5·m² ({h.get('irv_level')})",
        f"- CA/ICA: {fmt_num(v.get('CA'),2)}",
        f"- IH: {fmt_num(v.get('IH'),2)}",
        f"- CTE: {fmt_num(v.get('CTE'),2)}",
        "",
        "## Recomendaciones",
    ]
    lines.extend([f"- {r}" for r in results.get("recommendations", [])])
    lines.append("\n---\nGenerado por app ICG PE - Dr. Olano Ricardo Daniel.")
    return "\n".join(lines)


# =========================================================
# FLUJOS PRINCIPALES
# =========================================================

def single_pdf_flow(cfg: Dict[str, Any], logo_bytes: Optional[bytes], firma_bytes: Optional[bytes], medico: str, institucion: str) -> None:
    st.markdown("## 1) Importar informe completo Z-Logic de 4 hojas")
    st.info(
        "Cargue el PDF digital del informe completo Z-Logic/ICG de 4 hojas. "
        "Luego presione el botón de importación para integrar automáticamente datos demográficos, "
        "variables hemodinámicas, diagnóstico convencional, ML y PDF médico."
    )
    upload = st.file_uploader(
        "Botón de carga: PDF Z-Logic/ICG - informe completo de 4 hojas",
        type=["pdf"],
        accept_multiple_files=False,
        key="zlogic_pdf_upload",
    )

    current_token = None
    if upload is not None:
        current_token = f"{getattr(upload, 'name', 'pdf')}_{getattr(upload, 'size', 0)}"
        if st.session_state.get("zlogic_pdf_token") != current_token:
            for k in ["zlogic_pdf_rows", "zlogic_pdf_demo", "zlogic_pdf_text", "zlogic_pdf_grouped"]:
                st.session_state.pop(k, None)
            st.session_state["zlogic_pdf_token"] = current_token

    import_clicked = st.button(
        "Importar informe completo Z-Logic de 4 hojas e integrar",
        type="primary",
        disabled=upload is None,
        key="btn_import_zlogic_pdf",
    )

    if import_clicked and upload is not None:
        with st.spinner("Leyendo las 4 hojas del PDF Z-Logic e importando variables hemodinámicas..."):
            try:
                upload.seek(0)
            except Exception:
                pass
            extracted_rows, demo, full_text = parse_zlogic_pdf(upload)
            grouped = collapse_by_position(extracted_rows)
            st.session_state["zlogic_pdf_rows"] = extracted_rows
            st.session_state["zlogic_pdf_demo"] = demo
            st.session_state["zlogic_pdf_text"] = full_text
            st.session_state["zlogic_pdf_grouped"] = grouped

        if not full_text.strip():
            st.error(
                "No se detectó texto seleccionable en el PDF. Probablemente sea un PDF escaneado. "
                "Cargar versión digital del Z-Logic o aplicar OCR externo antes de importarlo."
            )
        else:
            st.success(
                f"Informe integrado. Variables detectadas: {len(extracted_rows)}. "
                f"Posiciones/páginas detectadas: {', '.join(grouped.keys()) if grouped else 'sin variables'}."
            )

    extracted_rows: List[Dict[str, Any]] = st.session_state.get("zlogic_pdf_rows", [])
    demo: Dict[str, Any] = st.session_state.get("zlogic_pdf_demo", {})
    full_text: str = st.session_state.get("zlogic_pdf_text", "")
    grouped: Dict[str, Dict[str, Any]] = st.session_state.get("zlogic_pdf_grouped", {})

    if upload is not None and not grouped and not full_text and not import_clicked:
        st.warning("PDF cargado. Presione **Importar informe completo Z-Logic de 4 hojas e integrar** para extraer las variables.")

    if full_text or extracted_rows:
        with st.expander("Auditoría de importación del PDF", expanded=False):
            st.text_area("Texto extraído del PDF", value=full_text[:12000], height=220, key="pdf_text_audit")
            if extracted_rows:
                st.dataframe(pd.DataFrame(extracted_rows), use_container_width=True, hide_index=True)

    st.markdown("## 2) Confirmar posición basal y corregir variables")
    if grouped:
        position_options = list(grouped.keys())
        default_index = 0
        for idx, pos in enumerate(position_options):
            if "basal" in normalize_text(pos) or "cinta" in normalize_text(pos) or "acostado" in normalize_text(pos) or "supino" in normalize_text(pos):
                default_index = idx
                break
        selected_position = st.selectbox(
            "Posición a usar como hemodinamia basal para embarazo",
            position_options,
            index=default_index,
            key="pdf_selected_position",
        )
        base_vars = grouped.get(selected_position, {})
        st.caption(f"Posición seleccionada: {selected_position}. Los datos pueden corregirse antes de generar el informe.")
    else:
        selected_position = "Manual"
        base_vars = {}
        st.caption("Sin variables importadas todavía. Puede completar el formulario o cargar/importar un PDF Z-Logic.")

    # Usar PAS/PAD extraídas como defaults clínicos.
    if "PAS" in base_vars:
        demo.setdefault("PAS", base_vars.get("PAS"))
    if "PAD" in base_vars:
        demo.setdefault("PAD", base_vars.get("PAD"))

    patient = demographic_form(demo, key_prefix="pdf_demo")
    flags = clinical_flags_form(key_prefix="pdf_flags")

    editor_df = variables_to_editor_df(base_vars)
    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="%.3f"),
            "Variable": st.column_config.TextColumn("Variable"),
            "Nombre": st.column_config.TextColumn("Nombre"),
            "Grupo": st.column_config.TextColumn("Grupo"),
            "Unidad": st.column_config.TextColumn("Unidad"),
        },
        key="pdf_vars_editor",
        disabled=["Variable", "Nombre", "Grupo", "Unidad"],
    )
    vars = editor_df_to_variables(edited_df)

    # Insertar IMC calculado si no existe y peso/talla están presentes.
    if "IMC" not in vars and vars.get("PESO") and vars.get("TALLA"):
        talla_m = vars["TALLA"] / 100.0 if vars["TALLA"] > 3 else vars["TALLA"]
        if talla_m > 0:
            vars["IMC"] = vars["PESO"] / (talla_m ** 2)

    if st.button("Analizar y generar informe médico integrado", type="primary", key="btn_analyze_pdf"):
        results = analyze_patient(patient, vars, flags, cfg)
        render_results(results, logo_bytes, firma_bytes, medico, institucion)


def pick_acostado_group(grouped: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if not grouped:
        return {}
    for key, vals in grouped.items():
        nk = normalize_text(key)
        if any(x in nk for x in ["acostado", "supino", "basal", "cinta"]):
            return dict(vals)
    # Si no está rotulado, usar el grupo con más variables útiles.
    best_key = max(grouped.keys(), key=lambda k: len(grouped.get(k, {})))
    return dict(grouped.get(best_key, {}))


def complement_vars(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, float]:
    """Completa variables faltantes sin pisar lo ya importado del informe principal."""
    out: Dict[str, float] = {}
    for src in [primary, secondary]:
        for k, v in (src or {}).items():
            cv = clean_num(v)
            if cv is not None and k not in out:
                out[k] = float(cv)
    if "PAM" not in out and out.get("PAS") and out.get("PAD"):
        out["PAM"] = (out["PAS"] + 2 * out["PAD"]) / 3
    if "IMC" not in out and out.get("PESO") and out.get("TALLA"):
        talla_m = out["TALLA"] / 100.0 if out["TALLA"] > 3 else out["TALLA"]
        if talla_m > 0:
            out["IMC"] = out["PESO"] / (talla_m ** 2)
    return out




def extract_zlogic_named_vars(text: str) -> Dict[str, float]:
    """Parser dirigido para informes Z-Logic donde la etiqueta y el valor están en la misma línea.

    Corrige el problema de tomar valores de referencia o valores de dz/dt como si fueran IC.
    Se usa especialmente para el PDF llamado COMPLETO y para el basal del PDF de 4 hojas.
    """
    out: Dict[str, float] = {}
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    specs: List[Tuple[str, str]] = [
        ("FC", r"\bFC\s+Frecuencia\s+Card[ií]aca\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("DS", r"\bDS\s+Descarga\s+Sist[oó]lica\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("IDS", r"\bIDS\s+Indice\s+de\s+Descarga\s+Sist[oó]lica\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("VM", r"\bVM\s+Volumen\s+Minuto\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("IC", r"\bIC\s+Indice\s+Card[ií]aco\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("RVS", r"\bRVS\s+Resistencia\s+Vascular\s+Sist[eé]mica\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("IRV", r"\bIRV\s+Indice\s+de\s+Resistencia\s+Vascular\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("CA", r"\bCA\s+Complacencia\s+Arterial\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("IV", r"\bIV\s+Indice\s+de\s+Velocidad\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("IAC", r"\bIAC\s+Indice\s+de\s+Aceleraci[oó]n\s+Card[ií]aca\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("CTS", r"\bCTS\s+Cociente\s+de\s+Tiempo\s+Sist[oó]lico.*?([-+]?\d+(?:[\.,]\d+)?)\s*%?"),
        ("ITC", r"\bITC\s+Indice\s+de\s+Trabajo\s+Card[ií]aco\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("CFT", r"\bCFT\s+Contenido\s+de\s+Fluidos\s+Tor[aá]cicos\s+([-+]?\d+(?:[\.,]\d+)?)"),
        ("Z0", r"\bZ0\s+([-+]?\d+(?:[\.,]\d+)?)"),
    ]
    for line in lines:
        for var, pat in specs:
            m = re.search(pat, line, flags=re.IGNORECASE)
            if m:
                val = clean_num(m.group(1))
                if val is not None:
                    if var == "CTS":
                        val = normalize_ratio_if_percent("CTS", val) or val
                    if plausible(var, val):
                        out[var] = float(val)
        bp = re.search(r"\bPA\s+Sist[oó]lica/Diast[oó]lica.*?(\d{2,3})\s*/\s*(\d{2,3})\s*\((\d{2,3})\)", line, flags=re.IGNORECASE)
        if bp:
            out["PAS"] = float(bp.group(1)); out["PAD"] = float(bp.group(2)); out["PAM"] = float(bp.group(3))
    # Datos antropométricos globales
    for key, pat in [
        ("PESO", r"Peso\s+([-+]?\d+(?:[\.,]\d+)?)\s*kg"),
        ("TALLA", r"Altura\s+([-+]?\d+(?:[\.,]\d+)?)\s*cm"),
        ("IMC", r"(?:BMI|IMC)\s+([-+]?\d+(?:[\.,]\d+)?)"),
    ]:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            val = clean_num(m.group(1))
            if val is not None and plausible(key, val):
                out[key] = float(val)
    if "IMC" not in out and out.get("PESO") and out.get("TALLA"):
        talla_m = out["TALLA"] / 100.0 if out["TALLA"] > 3 else out["TALLA"]
        if talla_m > 0:
            out["IMC"] = out["PESO"] / (talla_m ** 2)
    return out

def merge_demo(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(primary or {})
    for k, v in (secondary or {}).items():
        if k not in out or out.get(k) in [None, "", "SD", "No disponible"]:
            out[k] = v
    # Edad gestacional segura. En los PDF de ejemplo aparece "EMB S11" y debe quedar 11,
    # pero si el parser toma un valor fuera de rango no puede romper Streamlit.
    out["edad_gestacional"] = clamp_value(out.get("edad_gestacional"), 5.0, 42.0, 24.0)
    return out


def parse_bp_triplet(line: str) -> Optional[Tuple[List[float], List[float], List[float]]]:
    matches = re.findall(r"(\d{2,3})\s*/\s*(\d{2,3})\s*\((\d{2,3})\)", line)
    if len(matches) >= 3:
        pas = [float(m[0]) for m in matches[:3]]
        pad = [float(m[1]) for m in matches[:3]]
        pam = [float(m[2]) for m in matches[:3]]
        return pas, pad, pam
    return None


def extract_ortho_from_text(text: str) -> Dict[str, Dict[str, float]]:
    """Extrae columnas Acostado/Sentado/Parado del informe Z-Logic de 4 hojas.

    El informe de 4 hojas trae líneas del tipo:
    'Indice Cardíaco 5.7 3.6 3.2 ---' y variables adicionales en página 4.
    Esta función evita depender de la detección de posición por página y crea
    tres diccionarios separados: Acostado, Sentado y Parado.
    """
    ortho: Dict[str, Dict[str, float]] = {"Acostado": {}, "Sentado": {}, "Parado": {}}
    patterns: List[Tuple[str, str]] = [
        ("IC", r"indice\s+card[ií]aco"),
        ("IDS", r"indice\s+de\s+descarga\s+sist[oó]lica"),
        ("FC", r"frecuencia\s+card[ií]aca"),
        ("IRV", r"indice\s+de\s+res\.?\s*vascular|indice\s+de\s+resistencia\s+vascular"),
        ("CA", r"complacencia\s+arterial(?!\s+sist[eé]mica)"),
        ("Z0", r"z0\s*\(impedancia\s+basal\)|\bz0\b"),
        ("DS", r"descarga\s+sist[oó]lica"),
        ("VM", r"volumen\s+minuto"),
        ("RVS", r"resistencia\s+vascular\s+sist[eé]mica"),
        ("PP", r"presi[oó]n\s+de\s+pulso"),
        ("CFT", r"contenido\s+de\s+fluidos\s+tor[aá]cicos"),
        ("CFTnr", r"cft\s*n\.?r\.?|cft\s+nr"),
        ("EES", r"ees\s*\(capan\)|ees\s*\(weissler\)|\bees\b"),
        ("FE_CAPAN", r"fe\s*\(capan\)"),
    ]
    pending_var: Optional[str] = None
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        nline = normalize_text(line)
        if not line:
            continue
        if pending_var is not None:
            nums_pending = extract_numbers(line)
            if len(nums_pending) >= 1:
                # Solo se usa la primera columna (CINTA/Acostado). La situación "Parado" se ignora.
                val = nums_pending[0]
                if plausible(pending_var if pending_var in PLAUSIBLE_RANGES else "IC", val):
                    ortho["Acostado"][pending_var] = float(val)
                pending_var = None
                continue
            pending_var = None
        bp = parse_bp_triplet(line)
        if bp:
            pas, pad, pam = bp
            for pos, i in zip(["Acostado", "Sentado", "Parado"], range(3)):
                ortho[pos]["PAS"] = pas[i]
                ortho[pos]["PAD"] = pad[i]
                ortho[pos]["PAM"] = pam[i]
            continue
        for var, pat in patterns:
            if re.search(pat, nline, flags=re.IGNORECASE):
                nums = extract_numbers(line)
                # Ignorar referencias al final si aparecen; tomar los 3 primeros valores de la fila.
                if len(nums) >= 3:
                    vals = nums[:3]
                    # En filas como EES (Capan) puede aparecer el nombre sin números extraños.
                    for pos, val in zip(["Acostado", "Sentado", "Parado"], vals):
                        if plausible(var if var in PLAUSIBLE_RANGES else "IC", val):
                            if var == "CTS":
                                val = normalize_ratio_if_percent("CTS", val) or val
                            # Evitar que las tablas internas del PDF sobrescriban el primer valor correcto
                            # extraído desde el texto visible. Para EES/AC se permite sobrescribir
                            # porque Capan aparece después de Weissler y es el valor usado clínicamente.
                            if var not in ortho[pos] or var in {"EES", "FE_CAPAN"}:
                                ortho[pos][var] = float(val)
                elif var in {"CFTnr", "EES", "FE_CAPAN"}:
                    pending_var = var
                break
    # Solo se conserva la columna basal (Acostado/CINTA). La situación "Parado" no se utiliza.
    return {"Acostado": ortho.get("Acostado", {})}


def reset_integrated_dual_state() -> None:
    for k in ["dual_integrated_ready", "dual_integrated_demo", "dual_base_vars", "dual_standing_vars", "dual_ortho_table", "dual_conflicts"]:
        st.session_state.pop(k, None)


def dual_pdf_flow(cfg: Dict[str, Any], logo_bytes: Optional[bytes], firma_bytes: Optional[bytes], medico: str, institucion: str) -> None:
    st.markdown("## Importación obligatoria de DOS PDF Z-Logic")
    st.error("Esta pantalla NO acepta un único informe. Deben cargarse dos PDF separados: 1) COMPLETO y 2) DE 4 HOJAS.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 1) PDF COMPLETO Z-Logic")
        upload_completo = st.file_uploader(
            "CARGAR PDF COMPLETO Z-Logic",
            type=["pdf"],
            accept_multiple_files=False,
            key="uploader_pdf_completo_zlogic_obligatorio_v15",
        )
        token_c = None
        if upload_completo is not None:
            token_c = f"{getattr(upload_completo, 'name', '')}_{getattr(upload_completo, 'size', 0)}"
            if st.session_state.get("token_pdf_completo") != token_c:
                for k in ["rows_pdf_completo", "demo_pdf_completo", "text_pdf_completo", "grouped_pdf_completo"]:
                    st.session_state.pop(k, None)
                reset_integrated_dual_state()
                st.session_state["token_pdf_completo"] = token_c
        if st.button("1. IMPORTAR INFORME COMPLETO Z-LOGIC", type="primary", disabled=upload_completo is None, key="btn_importar_pdf_completo_real_v15"):
            with st.spinner("Importando informe COMPLETO Z-Logic..."):
                try:
                    upload_completo.seek(0)
                except Exception:
                    pass
                rows, demo, text = parse_zlogic_pdf(upload_completo)
                grouped = collapse_by_position(rows)
                st.session_state["rows_pdf_completo"] = rows
                st.session_state["demo_pdf_completo"] = demo
                st.session_state["text_pdf_completo"] = text
                st.session_state["grouped_pdf_completo"] = grouped
                reset_integrated_dual_state()
            st.success(f"Informe COMPLETO importado: {len(rows)} variables/lecturas detectadas.")
    with c2:
        st.markdown("### 2) PDF Z-Logic DE 4 HOJAS")
        upload_4h = st.file_uploader(
            "CARGAR PDF Z-Logic DE 4 HOJAS",
            type=["pdf"],
            accept_multiple_files=False,
            key="uploader_pdf_4hojas_zlogic_obligatorio_v15",
        )
        token_4 = None
        if upload_4h is not None:
            token_4 = f"{getattr(upload_4h, 'name', '')}_{getattr(upload_4h, 'size', 0)}"
            if st.session_state.get("token_pdf_4hojas") != token_4:
                for k in ["rows_pdf_4hojas", "demo_pdf_4hojas", "text_pdf_4hojas", "grouped_pdf_4hojas", "ortho_pdf_4hojas"]:
                    st.session_state.pop(k, None)
                reset_integrated_dual_state()
                st.session_state["token_pdf_4hojas"] = token_4
        if st.button("2. IMPORTAR INFORME DE 4 HOJAS", type="primary", disabled=upload_4h is None, key="btn_importar_pdf_4hojas_real_v15"):
            with st.spinner("Importando informe Z-Logic DE 4 HOJAS..."):
                try:
                    upload_4h.seek(0)
                except Exception:
                    pass
                rows, demo, text = parse_zlogic_pdf(upload_4h)
                grouped = collapse_by_position(rows)
                ortho = extract_ortho_from_text(text)
                st.session_state["rows_pdf_4hojas"] = rows
                st.session_state["demo_pdf_4hojas"] = demo
                st.session_state["text_pdf_4hojas"] = text
                st.session_state["grouped_pdf_4hojas"] = grouped
                st.session_state["ortho_pdf_4hojas"] = ortho
                reset_integrated_dual_state()
            st.success(f"Informe DE 4 HOJAS importado: {len(rows)} variables/lecturas + ortostatismo detectado.")

    completo_ok = "rows_pdf_completo" in st.session_state
    cuatro_ok = "rows_pdf_4hojas" in st.session_state
    st.markdown("### 3) Complementar variables de ambos informes")
    if not completo_ok or not cuatro_ok:
        faltan = []
        if not completo_ok:
            faltan.append("COMPLETO")
        if not cuatro_ok:
            faltan.append("DE 4 HOJAS")
        st.warning("Falta importar: " + " y ".join(faltan) + ". El análisis queda bloqueado hasta importar ambos PDF.")

    if st.button(
        "3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS",
        type="primary",
        disabled=not (completo_ok and cuatro_ok),
        key="btn_complementar_analizar_dos_pdf_real_v15",
    ):
        grouped_c = st.session_state.get("grouped_pdf_completo", {})
        grouped_4 = st.session_state.get("grouped_pdf_4hojas", {})
        ortho_4 = st.session_state.get("ortho_pdf_4hojas", {}) or {"Acostado": {}, "Parado": {}}
        # El informe COMPLETO aporta la tabla basal principal; el de 4 hojas complementa
        # variables adicionales y ortostatismo. Se usa un parser dirigido para evitar
        # que se importen valores de referencia como si fueran datos del paciente.
        complete_direct = extract_zlogic_named_vars(st.session_state.get("text_pdf_completo", ""))
        four_direct = extract_zlogic_named_vars(st.session_state.get("text_pdf_4hojas", ""))
        complete_base = complement_vars(complete_direct, pick_acostado_group(grouped_c))
        four_base = complement_vars(four_direct, complement_vars(ortho_4.get("Acostado", {}), pick_acostado_group(grouped_4)))
        base_vars = complement_vars(complete_base, four_base)
        standing_vars = {}
        demo = merge_demo(st.session_state.get("demo_pdf_completo", {}), st.session_state.get("demo_pdf_4hojas", {}))
        if "PAS" in base_vars:
            demo.setdefault("PAS", base_vars.get("PAS"))
        if "PAD" in base_vars:
            demo.setdefault("PAD", base_vars.get("PAD"))
        conflicts = []
        for k in sorted(set(complete_base).intersection(set(four_base))):
            a = clean_num(complete_base.get(k)); b = clean_num(four_base.get(k))
            if a is not None and b is not None and abs(a - b) > max(0.05, abs(a) * 0.03):
                conflicts.append({"Variable": k, "Completo": a, "4 hojas": b, "Usado": base_vars.get(k)})
        st.session_state["dual_integrated_demo"] = demo
        st.session_state["dual_base_vars"] = base_vars
        st.session_state["dual_standing_vars"] = standing_vars
        st.session_state["dual_conflicts"] = conflicts
        st.session_state["dual_integrated_ready"] = True
        st.success("Integración realizada: informe COMPLETO + informe DE 4 HOJAS complementados.")

    with st.expander("Auditoría de importación de ambos PDF", expanded=False):
        cc1, cc2 = st.columns(2)
        with cc1:
            st.write("**COMPLETO**")
            if completo_ok:
                st.dataframe(pd.DataFrame(st.session_state.get("rows_pdf_completo", [])), use_container_width=True, hide_index=True)
            else:
                st.caption("No importado.")
        with cc2:
            st.write("**DE 4 HOJAS**")
            if cuatro_ok:
                st.dataframe(pd.DataFrame(st.session_state.get("rows_pdf_4hojas", [])), use_container_width=True, hide_index=True)
            else:
                st.caption("No importado.")

    if not st.session_state.get("dual_integrated_ready"):
        return

    demo = st.session_state.get("dual_integrated_demo", {})
    base_vars = st.session_state.get("dual_base_vars", {})
    standing_vars = st.session_state.get("dual_standing_vars", {})
    conflicts = st.session_state.get("dual_conflicts", [])

    st.markdown("## Variables integradas y análisis")
    if conflicts:
        st.warning("Hay diferencias entre ambos informes. Se usa el valor del informe COMPLETO cuando existe y el de 4 hojas para completar faltantes.")
        st.dataframe(pd.DataFrame(conflicts), use_container_width=True, hide_index=True)

    patient = demographic_form(demo, key_prefix="dual_demo_final")
    flags = clinical_flags_form(key_prefix="dual_flags_final")

    st.markdown("#### Acostado / decúbito supino integrado")
    edited_base = st.data_editor(
        variables_to_editor_df(base_vars),
        use_container_width=True,
        hide_index=True,
        disabled=["Variable", "Nombre", "Grupo", "Unidad"],
        column_config={"Valor": st.column_config.NumberColumn("Valor", format="%.3f")},
        key="editor_base_integrado_dos_pdf_v15",
    )
    base_vars = editor_df_to_variables(edited_base)

    if st.button("ANALIZAR Y GENERAR INFORME MÉDICO INTEGRADO DE LOS DOS PDF", type="primary", key="btn_analizar_dos_pdf_integrado_v15"):
        results = analyze_patient(patient, base_vars, flags, cfg)
        render_results(results, logo_bytes, firma_bytes, medico, institucion)

def manual_flow(cfg: Dict[str, Any], logo_bytes: Optional[bytes], firma_bytes: Optional[bytes], medico: str, institucion: str) -> None:
    st.markdown("## Carga manual / validación rápida")
    patient = demographic_form({}, key_prefix="manual_demo")
    flags = clinical_flags_form(key_prefix="manual_flags")
    st.markdown("#### Variables hemodinámicas ICG")
    c1, c2, c3, c4 = st.columns(4)
    vars: Dict[str, float] = {}
    with c1:
        vars["IC"] = st.number_input("IC", min_value=0.0, max_value=8.0, value=3.6, step=0.1, key="manual_var_ic")
        vars["IRV"] = st.number_input("IRV", min_value=0.0, max_value=6500.0, value=1600.0, step=50.0, key="manual_var_irv")
        vars["RVS"] = st.number_input("RVS/TPVR", min_value=0.0, max_value=3500.0, value=0.0, step=50.0, key="manual_var_rvs")
    with c2:
        vars["CA"] = st.number_input("CA/ICA/ACI", min_value=0.0, max_value=10.0, value=1.4, step=0.1, key="manual_var_ca")
        vars["ITC"] = st.number_input("ITC/ITS", min_value=0.0, max_value=20.0, value=3.5, step=0.1, key="manual_var_itc")
        vars["IH"] = st.number_input("IH", min_value=0.0, max_value=80.0, value=12.0, step=0.5, key="manual_var_ih")
        vars["IAC"] = st.number_input("IAC/IA", min_value=0.0, max_value=700.0, value=290.0, step=5.0, key="manual_var_iac")
    with c3:
        vars["CTE"] = st.number_input("CTE", min_value=0.0, max_value=100.0, value=0.36, step=0.01, key="manual_var_cte")
        vars["CTS"] = st.number_input("CTS/STR (relación o %)", min_value=0.0, max_value=100.0, value=0.34, step=0.01, key="manual_var_cts")
        vars["CFT"] = st.number_input("CFT", min_value=0.0, max_value=120.0, value=24.0, step=1.0, key="manual_var_cft")
    with c4:
        vars["EES"] = st.number_input("EES", min_value=0.0, max_value=20.0, value=1.4, step=0.1, key="manual_var_ees")
        vars["FC"] = st.number_input("FC", min_value=35.0, max_value=190.0, value=80.0, step=1.0, key="manual_var_fc")

    # Quitar ceros vacíos opcionales.
    vars = {k: v for k, v in vars.items() if clean_num(v) is not None and not (k == "RVS" and v == 0)}

    if st.button("Analizar manual", type="primary", key="btn_analyze_manual"):
        results = analyze_patient(patient, vars, flags, cfg)
        render_results(results, logo_bytes, firma_bytes, medico, institucion)


def batch_flow(cfg: Dict[str, Any]) -> None:
    st.markdown("## Procesamiento masivo desde Excel/CSV")
    st.info("El archivo debe contener, idealmente, columnas: paciente, edad_gestacional, PAS, PAD, IC, IRV, CA, ITC, CTE, IH, AC, IMC.")
    up = st.file_uploader("Cargar Excel/CSV", type=["xlsx", "xls", "csv"], key="batch")
    if up is None:
        return
    try:
        if up.name.lower().endswith(".csv"):
            df = pd.read_csv(up)
        else:
            df = pd.read_excel(up)
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        return

    st.dataframe(df.head(20), use_container_width=True)

    # Mapeo flexible de columnas.
    norm_cols = {normalize_text(c): c for c in df.columns}

    def col(*names: str) -> Optional[str]:
        for n in names:
            nn = normalize_text(n)
            if nn in norm_cols:
                return norm_cols[nn]
        for nn, orig in norm_cols.items():
            if any(normalize_text(n) in nn for n in names):
                return orig
        return None

    if st.button("Procesar lote", type="primary", key="btn_process_batch"):
        results_rows = []
        for _, row in df.iterrows():
            patient = {
                "paciente": row.get(col("paciente", "nombre") or "", ""),
                "dni": row.get(col("dni", "documento") or "", "SD"),
                "edad_gestacional": clean_num(row.get(col("edad_gestacional", "eg", "semana") or "")) or 24,
                "PAS": clean_num(row.get(col("pas", "sbp") or "")) or 120,
                "PAD": clean_num(row.get(col("pad", "dbp") or "")) or 80,
                "fecha_estudio": datetime.now().strftime("%d/%m/%Y"),
                "obra_social": "",
            }
            vars: Dict[str, float] = {}
            for var in VARIABLE_INFO:
                c = col(var, VARIABLE_INFO[var]["label"])
                if c and clean_num(row.get(c)) is not None:
                    vars[var] = float(clean_num(row.get(c)))
            flags = {"proteinuria": False, "severe_symptoms": False, "platelets_low": False, "creatinine_high": False, "liver_high": False, "pulmonary_edema": False, "seizures": False, "low_calcium_intake": False}
            res = analyze_patient(patient, vars, flags, cfg)
            results_rows.append({
                "paciente": patient.get("paciente"),
                "edad_gestacional": patient.get("edad_gestacional"),
                "IC": vars.get("IC"),
                "IRV": vars.get("IRV"),
                "fenotipo": res["hemo"]["profile"],
                "riesgo_ml_general_olano2023": res["ml"]["category"],
                "p_global": res["ml"]["p_global"],
                "olano2025_categoria": res["ml"].get("olano2025", {}).get("category"),
                "olano2025_clasificacion": res["ml"].get("olano2025", {}).get("classification"),
                "olano2025_subtipo": res["ml"].get("olano2025", {}).get("subtype"),
                "olano2025_ruta": res["ml"].get("olano2025", {}).get("route"),
                "alcance_ml": res["ml"].get("scope"),
                "modelo_ml": res["ml"].get("model_name"),
                "diagnostico_clinico": res["clinical"]["diagnosis"],
            })
        out = pd.DataFrame(results_rows)
        st.dataframe(out, use_container_width=True, hide_index=True)
        buf = io.BytesIO()
        out.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("Descargar resultados del lote", buf.getvalue(), "resultados_lote_pe_icg.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def knowledge_base_tab() -> None:
    st.markdown("## Base de conocimiento de la app")
    st.markdown(
        """
        **Módulo convencional hemodinámico**
        
        - Compara IC e IRV contra una banda esperada por edad gestacional.
        - Clasifica: hipodinamia, normodinamia, hiperdinamia, IC normal con IRV inadecuadamente elevada, IC elevado con IRV normal.
        - Si se dispone RVS/TPVR no indexada, agrega criterio convencional de perfiles por resistencia total.
        
        **Módulo ML hemodinámico operativo: Olano 2023**
        
        - Usa las variables centrales del modelo local: CA/ICA, IC, ITC/ITS, CTE e IH.
        - Entrega riesgo general de preeclampsia: bajo, intermedio o alto.
        - No debe usarse para subtipo temprano/tardío, porque su endpoint es PE general.
        
        **Módulo ML hemodinámico operativo: Olano 2025**
        
        - Usa STR/CTS, IA/IAC, ELV/EES y ACI/CA.
        - Entrega orientación de subtipo de riesgo: PE temprana/placentaria o PE tardía/materno-metabólica.
        - Se muestra como resultado separado y complementario del riesgo general.
        
        **Importante:** la app informa ambos modelos por separado para no mezclar endpoints: Olano 2023 = riesgo general de PE; Olano 2025 = orientación temprana/tardía.
        """
    )
    st.download_button("Descargar base de conocimiento interna", json.dumps(DEFAULT_MODEL_CONFIG, indent=2, ensure_ascii=False).encode("utf-8"), "base_conocimiento_ml_pe_icg.json", mime="application/json")
    st.dataframe(REFERENCE_POINTS, use_container_width=True, hide_index=True)


# =========================================================
# MAIN
# =========================================================

def main() -> None:
    inject_css()
    render_header()
    cfg = load_model_config()
    logo_bytes, firma_bytes, medico, institucion = get_logo_and_signature()

    tabs = st.tabs(["PDF Z-Logic: DOS INFORMES", "Carga manual", "Lote Excel/CSV", "Base de conocimiento"])
    with tabs[0]:
        dual_pdf_flow(cfg, logo_bytes, firma_bytes, medico, institucion)
    with tabs[1]:
        manual_flow(cfg, logo_bytes, firma_bytes, medico, institucion)
    with tabs[2]:
        batch_flow(cfg)
    with tabs[3]:
        knowledge_base_tab()

    st.markdown(
        """
        <div class="footer-note">
        Esta app es un sistema de apoyo clínico para investigación, docencia y práctica supervisada. No reemplaza la evaluación médica, obstétrica ni las guías locales vigentes.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
