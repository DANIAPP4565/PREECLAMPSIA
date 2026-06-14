
# -*- coding: utf-8 -*-
"""
PREECLAMPSIA SMART-ICG
App Streamlit para predicción, estratificación de riesgo, fenotipo hemodinámico,
manejo clínico y orientación terapéutica de preeclampsia.

Autor/Desarrollador:
Dr. Olano Ricardo Daniel, Cardiólogo Hipertensólogo

Uso:
streamlit run app_preeclampsia.py

Aviso:
Esta herramienta es de apoyo a la decisión clínica. No reemplaza el criterio
del equipo obstétrico, cardiológico ni los protocolos institucionales.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

APP_TITLE = "Preeclampsia Smart-ICG"
APP_SUBTITLE = "Predicción, fenotipo hemodinámico, manejo clínico y orientación terapéutica"
AUTHOR = "Dr. Olano Ricardo Daniel · Cardiólogo Hipertensólogo"
VERSION = "v1.0 · 2026"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# ESTILOS
# =========================================================

def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --navy: #0B2545;
            --blue: #134E7C;
            --teal: #0E9384;
            --mint: #E7F7F4;
            --bg: #F4F8FB;
            --card: #FFFFFF;
            --line: #D7E2EA;
            --text: #172033;
            --muted: #5E6B7A;
            --red: #B42318;
            --orange: #B54708;
            --green: #067647;
        }
        .stApp {
            background: linear-gradient(180deg, #EEF6FB 0%, #F8FBFD 100%);
        }
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1320px;
        }
        h1, h2, h3 {
            color: var(--navy) !important;
            letter-spacing: -0.02em;
        }
        .hero {
            background: linear-gradient(135deg, #0B2545 0%, #134E7C 55%, #0E9384 100%);
            color: white;
            border-radius: 24px;
            padding: 26px 30px;
            margin-bottom: 20px;
            box-shadow: 0 14px 40px rgba(11,37,69,.16);
        }
        .hero h1 {
            color: white !important;
            margin: 0 0 6px 0;
            font-size: 2.0rem;
        }
        .hero p {
            color: rgba(255,255,255,.92);
            margin: 0;
            font-size: 1.02rem;
        }
        .soft-card {
            background: white;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: 0 8px 26px rgba(31,55,85,.06);
            margin-bottom: 14px;
        }
        .result-card {
            border-radius: 18px;
            padding: 18px 20px;
            border: 1px solid var(--line);
            background: white;
            box-shadow: 0 6px 20px rgba(31,55,85,.06);
        }
        .risk-low {
            border-left: 9px solid var(--green);
        }
        .risk-mid {
            border-left: 9px solid var(--orange);
        }
        .risk-high {
            border-left: 9px solid var(--red);
        }
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: .82rem;
            font-weight: 800;
            margin-right: 6px;
        }
        .badge-green { background:#ECFDF3; color:#067647; border:1px solid #ABEFC6; }
        .badge-orange { background:#FFF7ED; color:#B54708; border:1px solid #FEDF89; }
        .badge-red { background:#FEF3F2; color:#B42318; border:1px solid #FECDCA; }
        .badge-blue { background:#EFF8FF; color:#175CD3; border:1px solid #B2DDFF; }
        .small-muted { color: var(--muted); font-size: .86rem; }
        .stButton > button, .stDownloadButton > button {
            border-radius: 12px !important;
            background: #134E7C !important;
            color: white !important;
            border: 1px solid #0B2545 !important;
            font-weight: 700 !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            background: #0B2545 !important;
        }
        div[data-testid="stMetricValue"] {
            color: var(--navy);
        }
        [data-testid="stSidebar"] {
            background: #EAF2F8;
            border-right: 1px solid var(--line);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


# =========================================================
# MODELO DE DATOS
# =========================================================

@dataclass
class PatientInput:
    # Identificación
    paciente: str
    documento: str
    fecha: str
    edad: float
    edad_gestacional: float
    embarazo_multiple: bool
    nulipara: bool
    intervalo_embarazo_mayor_10: bool
    antecedente_pe: bool
    antecedente_fgr: bool
    antecedente_familiar_pe: bool

    # Riesgo clínico basal
    hta_cronica: bool
    enfermedad_renal: bool
    diabetes_previa: bool
    diabetes_gestacional: bool
    autoinmune_saf_lupus: bool
    trombofilia: bool
    reproduccion_asistida: bool
    apnea_sueno: bool
    bmi: float
    baja_ingesta_calcio: bool

    # Estado actual
    pas: float
    pad: float
    proteinuria_mg24: float
    relacion_prot_creat: float
    tira_proteinas_2plus: bool
    plaquetas: float
    creatinina: float
    ast_alt_mayor_2x: bool
    dolor_epigastrio: bool
    cefalea_visual: bool
    edema_pulmonar: bool
    convulsion: bool
    fgr_sospecha: bool
    doppler_uterino_anormal: bool
    plgf_bajo_o_sflt_alto: bool

    # Hemodinamia ICG basal
    ic: float
    irv: float
    ca_ica: float
    ih: float
    iv: float
    iac: float
    cts: float
    cte: float
    its_itc: float
    cft: float
    ea: float
    ees: float
    ac: float
    fc: float

    # Ortostatismo
    ic_de_pie: float
    irv_de_pie: float
    ca_de_pie: float
    ih_de_pie: float


# =========================================================
# UTILIDADES
# =========================================================

def to_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        if isinstance(x, str):
            s = x.strip().replace(",", ".")
            if s == "":
                return default
            return float(s)
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def safe_int(x: Any) -> Optional[int]:
    v = to_float(x, None)
    if v is None:
        return None
    try:
        return int(round(v))
    except Exception:
        return None


def fmt(x: Any, dec: int = 1, suffix: str = "") -> str:
    v = to_float(x, None)
    if v is None:
        return "No disponible"
    return f"{v:.{dec}f}{suffix}".replace(".", ",")


def mmhg_mean(sbp: float, dbp: float) -> Optional[float]:
    if sbp <= 0 or dbp <= 0:
        return None
    return dbp + (sbp - dbp) / 3.0


def anonymize_id(name: str, doc: str, date: str) -> str:
    seed = f"{name}|{doc}|{date}|preeclampsia_smart_icg".encode("utf-8")
    return "PE-" + hashlib.sha256(seed).hexdigest()[:10].upper()


def now_str() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def normalize_col(c: str) -> str:
    s = str(c).strip().lower()
    repl = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    for ch in [" ", "-", ".", "/", "\\", "(", ")", "%"]:
        s = s.replace(ch, "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


# =========================================================
# RANGOS HEMODINÁMICOS POR EDAD GESTACIONAL
# =========================================================

def gestational_ranges(eg: float) -> Dict[str, Tuple[float, float]]:
    """
    Rangos operativos y configurables para apoyo clínico.
    No son puntos de corte diagnósticos universales. Su objetivo es categorizar
    el patrón relativo IC/IRV durante la gestación.
    """
    if eg < 14:
        return {
            "ic": (2.7, 4.2),
            "irv": (1100, 2400),
            "ca": (1.2, 3.5),
            "ih": (10, 35),
        }
    if eg < 28:
        return {
            "ic": (3.1, 4.8),
            "irv": (800, 2100),
            "ca": (1.3, 3.8),
            "ih": (10, 38),
        }
    return {
        "ic": (3.0, 4.7),
        "irv": (850, 2200),
        "ca": (1.2, 3.6),
        "ih": (9, 36),
    }


def classify_value(value: float, low: float, high: float, missing_label: str = "No disponible") -> str:
    if value is None or value <= 0:
        return missing_label
    if value < low:
        return "BAJO"
    if value > high:
        return "AUMENTADO"
    return "NORMAL"


def hemodynamic_classification(p: PatientInput) -> Dict[str, Any]:
    ranges = gestational_ranges(p.edad_gestacional)
    ic_class = classify_value(p.ic, *ranges["ic"])
    irv_class = classify_value(p.irv, *ranges["irv"])
    ca_class = classify_value(p.ca_ica, *ranges["ca"])
    ih_class = classify_value(p.ih, *ranges["ih"])

    phenotype = "No clasificable"
    probable_type = "No determinable"

    if ic_class == "NORMAL" and irv_class == "NORMAL":
        phenotype = "NORMODINAMIA"
        probable_type = "Bajo desacople IC/IRV"
    elif ic_class == "BAJO" and irv_class == "AUMENTADO":
        phenotype = "HIPODINAMIA VASOCONSTRICTORA"
        probable_type = "Fenotipo placentario: mayor probabilidad de PE temprana/FGR si el contexto obstétrico acompaña"
    elif ic_class == "AUMENTADO" and irv_class in ["NORMAL", "BAJO"]:
        phenotype = "HIPERDINAMIA"
        probable_type = "Fenotipo materno/metabólico: mayor probabilidad de PE tardía si no hay FGR"
    elif ic_class == "NORMAL" and irv_class == "AUMENTADO":
        phenotype = "IC NORMAL CON IRV INADECUADAMENTE ELEVADAS"
        probable_type = "Desacople hemodinámico de riesgo: poscarga alta para edad gestacional"
    elif ic_class == "AUMENTADO" and irv_class == "NORMAL":
        phenotype = "IC ELEVADO CON IRV NORMALES"
        probable_type = "Adaptación hiperdinámica con resistencia no reducida"
    elif ic_class == "BAJO":
        phenotype = "HIPODINAMIA"
        probable_type = "Flujo materno bajo relativo"
    elif irv_class == "AUMENTADO":
        phenotype = "VASOCONSTRICCIÓN MATERNA"
        probable_type = "PAM/poscarga elevada, requiere integración con Doppler/laboratorio"

    # Volemia operativa por CFT
    cft_status = "No disponible"
    if p.cft > 0:
        if p.cft < 25:
            cft_status = "CFT bajo: posible hipovolemia/vasoconstricción relativa"
        elif p.cft > 50:
            cft_status = "CFT alto: posible hipervolemia/congestión"
        else:
            cft_status = "CFT en rango operativo"

    # Acoplamiento ventrículo-arterial
    ac_status = "No disponible"
    if p.ac > 0:
        if p.ac < 1:
            ac_status = "Óptimo (<1)"
        elif p.ac <= 1.3:
            ac_status = "Subóptimo (1–1,3)"
        else:
            ac_status = "Desacoplamiento (>1,3)"

    # Ortostatismo
    delta_ic = None
    delta_irv = None
    delta_ca = None
    delta_ih = None
    ortho_flags: List[str] = []
    if p.ic > 0 and p.ic_de_pie > 0:
        delta_ic = p.ic_de_pie - p.ic
        if delta_ic >= 0:
            ortho_flags.append("IC no desciende con bipedestación")
    if p.irv > 0 and p.irv_de_pie > 0:
        delta_irv = p.irv_de_pie - p.irv
        if delta_irv <= 0:
            ortho_flags.append("IRV no aumenta con bipedestación")
    if p.ca_ica > 0 and p.ca_de_pie > 0:
        delta_ca = p.ca_de_pie - p.ca_ica
    if p.ih > 0 and p.ih_de_pie > 0:
        delta_ih = p.ih_de_pie - p.ih
        if delta_ih < -5:
            ortho_flags.append("Descenso relevante de IH con ortostatismo")

    if not ortho_flags and (delta_ic is not None or delta_irv is not None):
        ortho_flags.append("Respuesta ortostática compatible con adaptación esperada: IC ↓ e IRV ↑")

    return {
        "ic_class": ic_class,
        "irv_class": irv_class,
        "ca_class": ca_class,
        "ih_class": ih_class,
        "phenotype": phenotype,
        "probable_type": probable_type,
        "cft_status": cft_status,
        "ac_status": ac_status,
        "ranges": ranges,
        "delta_ic": delta_ic,
        "delta_irv": delta_irv,
        "delta_ca": delta_ca,
        "delta_ih": delta_ih,
        "ortho_flags": ortho_flags,
    }


# =========================================================
# DIAGNÓSTICO CLÍNICO DE HDP/PE
# =========================================================

def diagnose_current_state(p: PatientInput) -> Dict[str, Any]:
    eg = p.edad_gestacional
    severe_bp = (p.pas >= 160) or (p.pad >= 110)
    htn = (p.pas >= 140) or (p.pad >= 90)
    proteinuria = (
        (p.proteinuria_mg24 >= 300 if p.proteinuria_mg24 > 0 else False)
        or (p.relacion_prot_creat >= 0.3 if p.relacion_prot_creat > 0 else False)
        or p.tira_proteinas_2plus
    )
    severe_features = []
    if severe_bp:
        severe_features.append("PA en rango severo ≥160/110 mmHg")
    if 0 < p.plaquetas < 100000:
        severe_features.append("Plaquetas <100.000/µL")
    if p.creatinina >= 1.1:
        severe_features.append("Creatinina ≥1,1 mg/dL")
    if p.ast_alt_mayor_2x:
        severe_features.append("AST/ALT >2× límite superior")
    if p.dolor_epigastrio:
        severe_features.append("Dolor epigástrico/hipocondrio derecho persistente")
    if p.cefalea_visual:
        severe_features.append("Cefalea persistente o síntomas visuales")
    if p.edema_pulmonar:
        severe_features.append("Edema pulmonar")
    if p.convulsion:
        severe_features.append("Convulsión/eclampsia")

    diagnosis = "Sin criterios actuales de HTA del embarazo"
    urgency = "Control programado"
    if eg >= 20 and htn and proteinuria:
        diagnosis = "Preeclampsia probable"
        urgency = "Evaluación obstétrica prioritaria"
    elif eg >= 20 and htn and severe_features:
        diagnosis = "Preeclampsia con criterios de severidad"
        urgency = "Urgencia obstétrica"
    elif eg >= 20 and htn:
        diagnosis = "Hipertensión gestacional / sospecha de PE sin proteinuria documentada"
        urgency = "Completar laboratorio, proteinuria y evaluación fetal"
    elif eg < 20 and htn:
        diagnosis = "HTA crónica o HTA previa al embarazo probable"
        urgency = "Evaluación cardio-obstétrica"

    if p.convulsion:
        diagnosis = "Eclampsia hasta demostrar lo contrario"
        urgency = "Emergencia obstétrica"

    if severe_features and "Preeclampsia" in diagnosis:
        diagnosis = "Preeclampsia con criterios de severidad"

    return {
        "htn": htn,
        "severe_bp": severe_bp,
        "proteinuria": proteinuria,
        "severe_features": severe_features,
        "diagnosis": diagnosis,
        "urgency": urgency,
    }


# =========================================================
# RIESGO CLÍNICO Y HEMODINÁMICO
# =========================================================

def clinical_risk(p: PatientInput) -> Dict[str, Any]:
    high_factors = []
    moderate_factors = []

    if p.antecedente_pe:
        high_factors.append("Antecedente de PE")
    if p.hta_cronica:
        high_factors.append("HTA crónica")
    if p.enfermedad_renal:
        high_factors.append("Enfermedad renal crónica")
    if p.diabetes_previa:
        high_factors.append("Diabetes tipo 1/2 pregestacional")
    if p.autoinmune_saf_lupus:
        high_factors.append("Lupus/SAF u otra enfermedad autoinmune")
    if p.embarazo_multiple:
        high_factors.append("Embarazo múltiple")

    if p.nulipara:
        moderate_factors.append("Nuliparidad")
    if p.edad >= 40:
        moderate_factors.append("Edad ≥40 años")
    if p.intervalo_embarazo_mayor_10:
        moderate_factors.append("Intervalo intergenésico >10 años")
    if p.bmi >= 35:
        moderate_factors.append("IMC ≥35 kg/m²")
    elif p.bmi >= 30:
        moderate_factors.append("Obesidad IMC ≥30 kg/m²")
    if p.antecedente_familiar_pe:
        moderate_factors.append("Antecedente familiar de PE")
    if p.diabetes_gestacional:
        moderate_factors.append("Diabetes gestacional")
    if p.trombofilia:
        moderate_factors.append("Trombofilia")
    if p.reproduccion_asistida:
        moderate_factors.append("Reproducción asistida")
    if p.apnea_sueno:
        moderate_factors.append("Apnea del sueño")
    if p.antecedente_fgr:
        moderate_factors.append("Antecedente de FGR/RCIU")

    aspirin_candidate = bool(high_factors) or len(moderate_factors) >= 2

    points = 0
    points += len(high_factors) * 2.5
    points += len(moderate_factors) * 1.0
    if aspirin_candidate:
        points += 1.0

    return {
        "high_factors": high_factors,
        "moderate_factors": moderate_factors,
        "aspirin_candidate": aspirin_candidate,
        "points": points,
    }


def hemodynamic_risk_points(p: PatientInput, h: Dict[str, Any]) -> Tuple[float, List[str]]:
    points = 0.0
    reasons: List[str] = []

    if h["ic_class"] == "BAJO" and h["irv_class"] == "AUMENTADO":
        points += 4.0
        reasons.append("IC bajo + IRV aumentado: patrón hipodinámico vasoconstrictor")
    elif h["ic_class"] == "NORMAL" and h["irv_class"] == "AUMENTADO":
        points += 3.0
        reasons.append("IC normal con IRV inadecuadamente elevadas para la edad gestacional")
    elif h["ic_class"] == "AUMENTADO" and h["irv_class"] in ["BAJO", "NORMAL"]:
        points += 2.0
        reasons.append("Fenotipo hiperdinámico: considerar PE tardía/metabólica si contexto clínico acompaña")
    elif h["ic_class"] == "BAJO":
        points += 2.0
        reasons.append("IC bajo para edad gestacional")

    if h["ca_class"] == "BAJO":
        points += 1.5
        reasons.append("ICA/CA bajo: menor complacencia arterial")
    if h["ih_class"] == "BAJO":
        points += 1.0
        reasons.append("IH bajo: contractilidad disminuida relativa")

    if p.ac > 1.3:
        points += 1.0
        reasons.append("EA/EES >1,3: desacoplamiento ventrículo-arterial")
    elif 1.0 <= p.ac <= 1.3:
        points += 0.5
        reasons.append("EA/EES 1–1,3: acoplamiento subóptimo")

    if p.cte > 0.38:
        points += 0.75
        reasons.append("CTE elevado: alteración de tiempos eyectivos")
    if p.cts > 0.42:
        points += 0.75
        reasons.append("CTS/PEP-LVET elevado: rendimiento sistólico subóptimo")
    if p.cft > 50:
        points += 0.5
        reasons.append("CFT elevado: posible congestión/hipervolemia")
    elif 0 < p.cft < 25:
        points += 0.5
        reasons.append("CFT bajo: posible hipovolemia o vasoconstricción relativa")

    # Ortostatismo
    if h["delta_ic"] is not None and h["delta_ic"] >= 0:
        points += 1.0
        reasons.append("Ortostatismo: IC no desciende con bipedestación")
    if h["delta_irv"] is not None and h["delta_irv"] <= 0:
        points += 1.0
        reasons.append("Ortostatismo: IRV no aumenta con bipedestación")
    if h["delta_ih"] is not None and h["delta_ih"] < -5:
        points += 0.5
        reasons.append("Ortostatismo: descenso relevante de IH")

    return points, reasons


def integrated_prediction(p: PatientInput) -> Dict[str, Any]:
    clinical = clinical_risk(p)
    hemo = hemodynamic_classification(p)
    dx = diagnose_current_state(p)
    hemo_points, hemo_reasons = hemodynamic_risk_points(p, hemo)

    points = clinical["points"] + hemo_points
    flags: List[str] = []

    if dx["htn"]:
        points += 2.0
        flags.append("HTA actual")
    if dx["proteinuria"]:
        points += 2.0
        flags.append("Proteinuria positiva")
    if dx["severe_bp"]:
        points += 4.0
        flags.append("PA severa")
    if dx["severe_features"]:
        points += 4.0
        flags.append("Criterios de severidad")
    if p.fgr_sospecha:
        points += 2.0
        flags.append("FGR/RCIU sospechado")
    if p.doppler_uterino_anormal:
        points += 1.5
        flags.append("Doppler uterino anormal")
    if p.plgf_bajo_o_sflt_alto:
        points += 1.5
        flags.append("PlGF bajo o sFlt-1/PlGF elevado")

    # Normalización 0-100
    risk_percent = max(0, min(100, round(points * 7.0, 1)))

    if dx["severe_bp"] or dx["severe_features"] or p.convulsion:
        category = "MUY ALTO / URGENTE"
        color = "red"
    elif risk_percent >= 70:
        category = "ALTO"
        color = "red"
    elif risk_percent >= 40:
        category = "INTERMEDIO"
        color = "orange"
    else:
        category = "BAJO / NO ELEVADO"
        color = "green"

    # Estimación de fenotipo temprano/tardío
    early_score = 0
    late_score = 0
    if hemo["ic_class"] in ["BAJO", "NORMAL"] and hemo["irv_class"] == "AUMENTADO":
        early_score += 3
    if hbool(p.fgr_sospecha) or hbool(p.doppler_uterino_anormal) or hbool(p.plgf_bajo_o_sflt_alto):
        early_score += 2
    if hemo["ca_class"] == "BAJO":
        early_score += 1
    if hemo["ic_class"] == "AUMENTADO":
        late_score += 2
    if p.bmi >= 30 or p.diabetes_gestacional or p.diabetes_previa:
        late_score += 2
    if hemo["irv_class"] in ["BAJO", "NORMAL"] and hemo["ic_class"] == "AUMENTADO":
        late_score += 1

    if early_score > late_score + 1:
        pe_type = "Mayor señal hacia PE temprana/placentaria"
    elif late_score > early_score + 1:
        pe_type = "Mayor señal hacia PE tardía/materno-metabólica"
    else:
        pe_type = "Fenotipo mixto o no definido: requiere integración obstétrica"

    return {
        "clinical": clinical,
        "hemo": hemo,
        "dx": dx,
        "hemo_points": hemo_points,
        "hemo_reasons": hemo_reasons,
        "flags": flags,
        "points": points,
        "risk_percent": risk_percent,
        "category": category,
        "color": color,
        "pe_type": pe_type,
    }


def hbool(x: Any) -> bool:
    return bool(x)


# =========================================================
# MANEJO Y TERAPÉUTICA
# =========================================================

def management_plan(p: PatientInput, pred: Dict[str, Any], aspirin_dose: str, bp_target: str) -> Dict[str, List[str]]:
    dx = pred["dx"]
    clinical = pred["clinical"]
    hemo = pred["hemo"]

    prevention: List[str] = []
    evaluation: List[str] = []
    treatment: List[str] = []
    hemo_guided: List[str] = []
    delivery: List[str] = []
    followup: List[str] = []

    # Prevención
    if clinical["aspirin_candidate"] and p.edad_gestacional <= 28:
        prevention.append(
            f"Candidata a AAS preventivo: considerar {aspirin_dose} nocturno desde 12 semanas "
            "hasta el parto, idealmente iniciado antes de 16 semanas, si no hay contraindicación."
        )
    elif clinical["aspirin_candidate"] and p.edad_gestacional > 28:
        prevention.append(
            "Cumple criterios de alto riesgo para AAS, pero la mayor utilidad preventiva es al iniciarlo temprano; "
            "revisar conducta con obstetricia según edad gestacional y exposición previa."
        )
    else:
        prevention.append("AAS preventivo: no surge indicación automática por los factores ingresados; reevaluar si aparecen nuevos factores.")

    if p.baja_ingesta_calcio:
        prevention.append("Calcio: por baja ingesta dietaria, considerar suplementación con calcio elemental 1,5–2,0 g/día en dosis divididas, según tolerancia y protocolo.")
    else:
        prevention.append("Calcio: reforzar evaluación de ingesta dietaria; suplementar si la ingesta es baja o si lo indica protocolo local.")

    # Evaluación diagnóstica
    if dx["htn"] or pred["category"] in ["INTERMEDIO", "ALTO", "MUY ALTO / URGENTE"]:
        evaluation.extend([
            "Confirmar PA con técnica validada; si PA severa, repetir en 15 minutos.",
            "Laboratorio de PE: hemograma con plaquetas, creatinina, AST/ALT, LDH, ácido úrico según protocolo, proteinuria cuantitativa o relación proteína/creatinina.",
            "Evaluación fetal: ecografía de crecimiento, líquido amniótico, Doppler uterino/umbilical según edad gestacional, vitalidad fetal si corresponde.",
            "Integrar síntomas maternos: cefalea, fosfenos/alteración visual, dolor epigástrico, disnea, edema pulmonar, reducción de diuresis."
        ])
    else:
        evaluation.append("Seguimiento prenatal con control periódico de PA, proteinuria si síntomas o HTA, y reevaluación hemodinámica si cambia el estado clínico.")

    # Tratamiento antihipertensivo
    if dx["severe_bp"] or p.convulsion or dx["severe_features"]:
        treatment.extend([
            "PA severa o severidad: manejo como urgencia obstétrica en ámbito con capacidad materno-fetal.",
            "Antihipertensivo de acción rápida según protocolo institucional: labetalol IV, hidralazina IV o nifedipina oral de liberación inmediata; objetivo inicial: salir de rango ≥160/110.",
            "Sulfato de magnesio si eclampsia o PE con criterios de severidad, especialmente si el parto es inminente o hay síntomas neurológicos.",
            "Evitar IECA, ARA-II, inhibidores directos de renina y antagonistas mineralocorticoides durante embarazo salvo indicación extraordinaria especializada."
        ])
    elif dx["htn"]:
        treatment.extend([
            f"HTA no severa: considerar tratamiento farmacológico y titulación para objetivo aproximado {bp_target}, individualizando por perfusión fetal y tolerancia.",
            "Primera línea habitual: labetalol. Si no es adecuado, nifedipina; si ambas no son adecuadas, metildopa.",
            "Evitar caídas bruscas de PA si hay sospecha de insuficiencia placentaria, Doppler patológico o IC bajo."
        ])
    else:
        treatment.append("Sin HTA actual: no iniciar antihipertensivo por la app; usar la estratificación para vigilancia y prevención.")

    # Hemodinámica guiada
    if hemo["phenotype"] == "HIPODINAMIA VASOCONSTRICTORA":
        hemo_guided.extend([
            "Fenotipo de alto interés: bajo flujo + alta poscarga. Priorizar vigilancia estrecha de FGR/PE temprana.",
            "Si requiere antihipertensivo, evitar beta-bloqueo excesivo que reduzca más el IC; considerar estrategia con perfil vasodilatador bajo supervisión obstétrica.",
            "Revisar volemia, CFT, síntomas ortostáticos y perfusión fetal antes de intensificar."
        ])
    elif hemo["phenotype"] == "IC NORMAL CON IRV INADECUADAMENTE ELEVADAS":
        hemo_guided.extend([
            "Desacople IC/IRV: la resistencia está elevada para la edad gestacional aunque el flujo parezca conservado.",
            "Repetir ICG/MAPA/Doppler si aparecen síntomas, aumento de PA o alteración fetal."
        ])
    elif hemo["phenotype"] == "HIPERDINAMIA":
        hemo_guided.extend([
            "Fenotipo hiperdinámico: integrar IMC, diabetes, FC y volumen; suele orientar más a fenotipo materno/tardío si no hay FGR.",
            "Si hay taquicardia o alto gasto con HTA, labetalol puede tener lógica hemodinámica si no hay contraindicaciones; evitar sobredosificar vasodilatadores si IRV ya está bajo."
        ])
    elif hemo["phenotype"] == "NORMODINAMIA":
        hemo_guided.append("Normodinamia: el riesgo dependerá más de clínica, laboratorio, Doppler y evolución que del patrón ICG actual.")
    else:
        hemo_guided.append("Fenotipo no concluyente: completar variables ICG y repetir en condiciones estandarizadas.")

    if "CFT alto" in hemo["cft_status"]:
        hemo_guided.append("CFT alto: evitar sobrecarga hídrica; evaluar signos de congestión/edema pulmonar. Diurético solo con indicación especializada.")
    if "CFT bajo" in hemo["cft_status"]:
        hemo_guided.append("CFT bajo: evitar restricción hídrica excesiva y revisar depleción de volumen antes de intensificar antihipertensivos.")

    # Timing de finalización
    if dx["severe_features"] or dx["severe_bp"] or p.convulsion:
        if p.edad_gestacional >= 34:
            delivery.append("Con criterios de severidad y EG ≥34 semanas: discutir finalización según protocolo y estado materno-fetal.")
        else:
            delivery.append("Con criterios de severidad y EG <34 semanas: internación; manejo expectante solo si estable y en centro adecuado, con corticoides para maduración fetal si corresponde.")
    elif dx["diagnosis"].startswith("Preeclampsia") and p.edad_gestacional >= 37:
        delivery.append("PE sin severidad con EG ≥37 semanas: discutir finalización según protocolo obstétrico.")
    else:
        delivery.append("No definir finalización solo por esta app; usar evolución clínica, laboratorio, Doppler, crecimiento fetal y edad gestacional.")

    # Seguimiento
    if pred["color"] == "red":
        followup.append("Seguimiento inmediato/urgente. Revalorar PA y síntomas hoy.")
    elif pred["color"] == "orange":
        followup.append("Seguimiento estrecho: PA domiciliaria o institucional, laboratorio y control fetal según riesgo; repetir ICG si cambia tratamiento o clínica.")
    else:
        followup.append("Seguimiento prenatal habitual reforzado según factores de riesgo; repetir evaluación si aparece HTA, proteinuria o síntomas.")

    followup.append("Postparto: controlar PA y riesgo cardiovascular materno; antecedente de PE/HDP aumenta riesgo cardiovascular futuro.")

    return {
        "Prevención": prevention,
        "Evaluación diagnóstica": evaluation,
        "Tratamiento antihipertensivo": treatment,
        "Manejo guiado por hemodinamia": hemo_guided,
        "Finalización/derivación": delivery,
        "Seguimiento": followup,
    }


# =========================================================
# INFORME
# =========================================================

def build_markdown_report(p: PatientInput, pred: Dict[str, Any], plan: Dict[str, List[str]]) -> str:
    h = pred["hemo"]
    dx = pred["dx"]
    clinical = pred["clinical"]

    lines = []
    lines.append(f"# {APP_TITLE} — Informe integrado")
    lines.append(f"**Código anonimizado:** {anonymize_id(p.paciente, p.documento, p.fecha)}")
    lines.append(f"**Fecha de emisión:** {now_str()}")
    lines.append("")
    lines.append("## 1. Datos clínicos")
    lines.append(f"- Paciente: {p.paciente or 'No disponible'}")
    lines.append(f"- Edad: {fmt(p.edad,0)} años · Edad gestacional: {fmt(p.edad_gestacional,1)} semanas")
    lines.append(f"- PA: {fmt(p.pas,0)}/{fmt(p.pad,0)} mmHg · PAM: {fmt(mmhg_mean(p.pas,p.pad),0)} mmHg")
    lines.append(f"- Diagnóstico clínico actual: **{dx['diagnosis']}**")
    lines.append(f"- Urgencia sugerida: **{dx['urgency']}**")
    if dx["severe_features"]:
        lines.append("- Criterios de severidad: " + "; ".join(dx["severe_features"]))
    lines.append("")
    lines.append("## 2. Riesgo integrado")
    lines.append(f"- Categoría: **{pred['category']}**")
    lines.append(f"- Puntaje operativo: **{fmt(pred['risk_percent'],1)}%**")
    lines.append(f"- Tendencia fenotípica: **{pred['pe_type']}**")
    if clinical["high_factors"]:
        lines.append("- Factores mayores: " + "; ".join(clinical["high_factors"]))
    if clinical["moderate_factors"]:
        lines.append("- Factores moderados: " + "; ".join(clinical["moderate_factors"]))
    if pred["flags"]:
        lines.append("- Alertas clínicas: " + "; ".join(pred["flags"]))
    lines.append("")
    lines.append("## 3. Hemodinamia materna")
    lines.append(f"- IC: {fmt(p.ic,2)} L/min/m² → **{h['ic_class']}**")
    lines.append(f"- IRV: {fmt(p.irv,0)} dyn·s·cm⁻⁵·m² → **{h['irv_class']}**")
    lines.append(f"- ICA/CA: {fmt(p.ca_ica,2)} → **{h['ca_class']}**")
    lines.append(f"- IH: {fmt(p.ih,1)} → **{h['ih_class']}**")
    lines.append(f"- Fenotipo: **{h['phenotype']}**")
    lines.append(f"- Lectura clínica: {h['probable_type']}")
    lines.append(f"- CFT: {fmt(p.cft,1)} → {h['cft_status']}")
    lines.append(f"- EA/EES: {fmt(p.ac,2)} → {h['ac_status']}")
    if h["ortho_flags"]:
        lines.append("- Ortostatismo: " + "; ".join(h["ortho_flags"]))
    if pred["hemo_reasons"]:
        lines.append("- Señales hemodinámicas de riesgo: " + "; ".join(pred["hemo_reasons"]))
    lines.append("")
    lines.append("## 4. Conducta sugerida")
    for section, items in plan.items():
        lines.append(f"### {section}")
        for item in items:
            lines.append(f"- {item}")
    lines.append("")
    lines.append("## 5. Limitaciones")
    lines.append("- Herramienta de apoyo clínico; no reemplaza diagnóstico médico ni protocolos obstétricos.")
    lines.append("- El score es operativo/configurable y debe validarse externamente antes de uso como predictor autónomo.")
    lines.append("- Integrar siempre con laboratorio, Doppler, crecimiento fetal, síntomas y evolución.")
    lines.append("")
    lines.append(f"**Autor/Desarrollador:** {AUTHOR}")
    return "\n".join(lines)


def make_pdf(report_md: str) -> bytes:
    """
    Genera PDF simple. Si reportlab no está disponible, lanza excepción controlada.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="MyHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0B2545"), fontSize=13, leading=16))
    styles["Title"].textColor = colors.HexColor("#0B2545")
    story = []

    for raw in report_md.splitlines():
        line = raw.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Title"]))
            story.append(Spacer(1, 8))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["MyHeading"]))
        elif line.startswith("### "):
            story.append(Paragraph("<b>" + line[4:] + "</b>", styles["Normal"]))
        elif line.startswith("- "):
            txt = line[2:].replace("**", "<b>", 1)
            # Convert paired markdown bold conservatively
            while "**" in txt:
                txt = txt.replace("**", "</b>", 1) if "<b>" in txt and "</b>" not in txt else txt.replace("**", "<b>", 1)
            txt = txt.replace("·", "&middot;").replace("⁻", "-")
            story.append(Paragraph("• " + txt, styles["Small"]))
        else:
            txt = line.replace("**", "<b>", 1)
            while "**" in txt:
                txt = txt.replace("**", "</b>", 1) if "<b>" in txt and "</b>" not in txt else txt.replace("**", "<b>", 1)
            story.append(Paragraph(txt, styles["Small"]))

    doc.build(story)
    return buffer.getvalue()


def make_excel(p: PatientInput, pred: Dict[str, Any], plan: Dict[str, List[str]]) -> bytes:
    out = io.BytesIO()
    data = asdict(p)
    data.update({
        "codigo_anonimizado": anonymize_id(p.paciente, p.documento, p.fecha),
        "diagnostico_actual": pred["dx"]["diagnosis"],
        "urgencia": pred["dx"]["urgency"],
        "categoria_riesgo": pred["category"],
        "riesgo_operativo_pct": pred["risk_percent"],
        "fenotipo_hemodinamico": pred["hemo"]["phenotype"],
        "tipo_pe_probable": pred["pe_type"],
        "ic_clase": pred["hemo"]["ic_class"],
        "irv_clase": pred["hemo"]["irv_class"],
        "ca_clase": pred["hemo"]["ca_class"],
        "ih_clase": pred["hemo"]["ih_class"],
        "criterios_severidad": "; ".join(pred["dx"]["severe_features"]),
        "factores_mayores": "; ".join(pred["clinical"]["high_factors"]),
        "factores_moderados": "; ".join(pred["clinical"]["moderate_factors"]),
        "alertas": "; ".join(pred["flags"]),
        "senales_hemodinamicas": "; ".join(pred["hemo_reasons"]),
        "conducta": json.dumps(plan, ensure_ascii=False),
    })
    df = pd.DataFrame([data])
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="evaluacion")
        pd.DataFrame([
            {"seccion": k, "recomendacion": item}
            for k, items in plan.items()
            for item in items
        ]).to_excel(writer, index=False, sheet_name="plan")
    return out.getvalue()


# =========================================================
# GRÁFICOS
# =========================================================

def plot_hemo_quadrant(p: PatientInput, h: Dict[str, Any]) -> plt.Figure:
    ranges = h["ranges"]
    ic_low, ic_high = ranges["ic"]
    irv_low, irv_high = ranges["irv"]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.axvspan(0, ic_low, alpha=0.10)
    ax.axvspan(ic_low, ic_high, alpha=0.06)
    ax.axvspan(ic_high, max(ic_high*1.5, p.ic+1), alpha=0.10)
    ax.axhspan(0, irv_low, alpha=0.10)
    ax.axhspan(irv_low, irv_high, alpha=0.06)
    ax.axhspan(irv_high, max(irv_high*1.6, p.irv+600), alpha=0.10)

    ax.axvline(ic_low, linestyle="--", linewidth=1)
    ax.axvline(ic_high, linestyle="--", linewidth=1)
    ax.axhline(irv_low, linestyle="--", linewidth=1)
    ax.axhline(irv_high, linestyle="--", linewidth=1)

    if p.ic > 0 and p.irv > 0:
        ax.scatter([p.ic], [p.irv], s=120)
        ax.text(p.ic, p.irv, "  Paciente", va="center", fontsize=10)

    if p.ic_de_pie > 0 and p.irv_de_pie > 0:
        ax.scatter([p.ic_de_pie], [p.irv_de_pie], s=80, marker="x")
        ax.annotate(
            "",
            xy=(p.ic_de_pie, p.irv_de_pie),
            xytext=(p.ic, p.irv),
            arrowprops=dict(arrowstyle="->", lw=1.5),
        )
        ax.text(p.ic_de_pie, p.irv_de_pie, "  De pie", va="center", fontsize=10)

    ax.set_xlabel("Índice cardíaco, IC (L/min/m²)")
    ax.set_ylabel("Índice de resistencia vascular, IRV (dyn·s·cm⁻⁵·m²)")
    ax.set_title("Hemodinamia materna por edad gestacional")
    ax.grid(True, alpha=0.25)
    ax.set_xlim(max(0, min(ic_low - 1, p.ic - 1 if p.ic > 0 else 1)), max(ic_high + 1.5, p.ic + 1 if p.ic > 0 else 6))
    ax.set_ylim(max(0, min(irv_low - 500, p.irv - 800 if p.irv > 0 else 500)), max(irv_high + 1000, p.irv + 800 if p.irv > 0 else 3500))
    fig.tight_layout()
    return fig


def plot_risk_gauge(risk: float) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7, 1.3))
    ax.barh([0], [100], height=0.45, alpha=0.15)
    ax.barh([0], [risk], height=0.45, alpha=0.80)
    ax.axvline(40, linestyle="--", linewidth=1)
    ax.axvline(70, linestyle="--", linewidth=1)
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xlabel("Riesgo operativo integrado (%)")
    ax.set_title(f"Riesgo: {risk:.1f}%")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    return fig


# =========================================================
# BATCH
# =========================================================

EXPECTED_COLUMNS = {
    "paciente": ["paciente", "nombre", "apellido"],
    "documento": ["documento", "dni", "id"],
    "edad": ["edad"],
    "edad_gestacional": ["edad_gestacional", "eg", "semanas"],
    "pas": ["pas", "sistolica", "sbp"],
    "pad": ["pad", "diastolica", "dbp"],
    "bmi": ["bmi", "imc"],
    "ic": ["ic", "ci"],
    "irv": ["irv", "svri", "vri"],
    "ca_ica": ["ca", "ica", "compliance"],
    "ih": ["ih", "heather"],
    "cts": ["cts"],
    "cte": ["cte"],
    "cft": ["cft", "tfc"],
    "ac": ["ac", "ea_ees", "ea/ees"],
    "fc": ["fc", "hr"],
}


def get_col(df: pd.DataFrame, target: str) -> Optional[str]:
    cols_norm = {normalize_col(c): c for c in df.columns}
    for alias in EXPECTED_COLUMNS.get(target, []):
        alias_n = normalize_col(alias)
        for cn, original in cols_norm.items():
            if alias_n == cn or alias_n in cn:
                return original
    return None


def row_to_patient(row: pd.Series, df: pd.DataFrame) -> PatientInput:
    def val(name: str, default: Any = "") -> Any:
        c = get_col(df, name)
        if c is None:
            return default
        return row.get(c, default)

    return PatientInput(
        paciente=str(val("paciente", "")),
        documento=str(val("documento", "")),
        fecha=datetime.now().strftime("%d/%m/%Y"),
        edad=to_float(val("edad", 0), 0) or 0,
        edad_gestacional=to_float(val("edad_gestacional", 0), 0) or 0,
        embarazo_multiple=False,
        nulipara=False,
        intervalo_embarazo_mayor_10=False,
        antecedente_pe=False,
        antecedente_fgr=False,
        antecedente_familiar_pe=False,
        hta_cronica=False,
        enfermedad_renal=False,
        diabetes_previa=False,
        diabetes_gestacional=False,
        autoinmune_saf_lupus=False,
        trombofilia=False,
        reproduccion_asistida=False,
        apnea_sueno=False,
        bmi=to_float(val("bmi", 0), 0) or 0,
        baja_ingesta_calcio=False,
        pas=to_float(val("pas", 0), 0) or 0,
        pad=to_float(val("pad", 0), 0) or 0,
        proteinuria_mg24=0,
        relacion_prot_creat=0,
        tira_proteinas_2plus=False,
        plaquetas=0,
        creatinina=0,
        ast_alt_mayor_2x=False,
        dolor_epigastrio=False,
        cefalea_visual=False,
        edema_pulmonar=False,
        convulsion=False,
        fgr_sospecha=False,
        doppler_uterino_anormal=False,
        plgf_bajo_o_sflt_alto=False,
        ic=to_float(val("ic", 0), 0) or 0,
        irv=to_float(val("irv", 0), 0) or 0,
        ca_ica=to_float(val("ca_ica", 0), 0) or 0,
        ih=to_float(val("ih", 0), 0) or 0,
        iv=0,
        iac=0,
        cts=to_float(val("cts", 0), 0) or 0,
        cte=to_float(val("cte", 0), 0) or 0,
        its_itc=0,
        cft=to_float(val("cft", 0), 0) or 0,
        ea=0,
        ees=0,
        ac=to_float(val("ac", 0), 0) or 0,
        fc=to_float(val("fc", 0), 0) or 0,
        ic_de_pie=0,
        irv_de_pie=0,
        ca_de_pie=0,
        ih_de_pie=0,
    )


def process_batch(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        p = row_to_patient(row, df)
        pred = integrated_prediction(p)
        rows.append({
            "codigo_anonimizado": anonymize_id(p.paciente, p.documento, p.fecha),
            "paciente": p.paciente,
            "edad_gestacional": p.edad_gestacional,
            "PA": f"{p.pas:.0f}/{p.pad:.0f}",
            "diagnostico": pred["dx"]["diagnosis"],
            "riesgo_categoria": pred["category"],
            "riesgo_pct": pred["risk_percent"],
            "fenotipo": pred["hemo"]["phenotype"],
            "tipo_probable": pred["pe_type"],
            "IC_clase": pred["hemo"]["ic_class"],
            "IRV_clase": pred["hemo"]["irv_class"],
            "alertas": "; ".join(pred["flags"]),
            "senales_hemodinamicas": "; ".join(pred["hemo_reasons"]),
        })
    return pd.DataFrame(rows)


# =========================================================
# UI
# =========================================================

def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>🫀 {APP_TITLE}</h1>
            <p>{APP_SUBTITLE}<br><span style="opacity:.85">{AUTHOR} · {VERSION}</span></p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def input_form() -> PatientInput:
    with st.sidebar:
        st.header("⚙️ Configuración")
        aspirin_dose = st.selectbox(
            "Dosis de AAS preventiva a mostrar",
            ["150 mg/día", "100 mg/día", "81 mg/día", "75–150 mg/día"],
            index=0,
            help="La app muestra la opción elegida como texto de apoyo; ajustar al protocolo local.",
        )
        bp_target = st.selectbox(
            "Objetivo tensional orientativo",
            ["≈135/85 mmHg", "<140/90 mmHg", "individualizado"],
            index=0,
        )
        st.session_state["aspirin_dose"] = aspirin_dose
        st.session_state["bp_target"] = bp_target
        st.caption("Los puntos de corte hemodinámicos son operativos y deben ajustarse a la base local.")

    tabs = st.tabs(["1. Datos clínicos", "2. Laboratorio / severidad", "3. ICG / hemodinamia", "4. Ortostatismo"])

    with tabs[0]:
        st.subheader("Datos de la paciente y factores de riesgo")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            paciente = st.text_input("Paciente", value="")
            documento = st.text_input("Documento/DNI", value="")
        with c2:
            fecha = st.date_input("Fecha de evaluación", value=datetime.now()).strftime("%d/%m/%Y")
            edad = st.number_input("Edad (años)", min_value=10.0, max_value=60.0, value=32.0, step=1.0)
        with c3:
            edad_gestacional = st.number_input("Edad gestacional (semanas)", min_value=4.0, max_value=42.0, value=20.0, step=0.5)
            bmi = st.number_input("IMC (kg/m²)", min_value=10.0, max_value=70.0, value=28.0, step=0.5)
        with c4:
            pas = st.number_input("PAS (mmHg)", min_value=70.0, max_value=260.0, value=120.0, step=1.0)
            pad = st.number_input("PAD (mmHg)", min_value=40.0, max_value=160.0, value=75.0, step=1.0)

        st.markdown("**Factores mayores y moderados**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            antecedente_pe = st.checkbox("Antecedente de PE")
            hta_cronica = st.checkbox("HTA crónica")
            enfermedad_renal = st.checkbox("Enfermedad renal crónica")
        with c2:
            diabetes_previa = st.checkbox("Diabetes pregestacional")
            diabetes_gestacional = st.checkbox("Diabetes gestacional")
            autoinmune_saf_lupus = st.checkbox("Lupus/SAF/autoinmune")
        with c3:
            embarazo_multiple = st.checkbox("Embarazo múltiple")
            nulipara = st.checkbox("Nuliparidad")
            antecedente_fgr = st.checkbox("Antecedente FGR/RCIU")
        with c4:
            antecedente_familiar_pe = st.checkbox("Familiar con PE")
            intervalo_embarazo_mayor_10 = st.checkbox("Intervalo >10 años")
            trombofilia = st.checkbox("Trombofilia")
            reproduccion_asistida = st.checkbox("Reproducción asistida")
            apnea_sueno = st.checkbox("Apnea del sueño")
            baja_ingesta_calcio = st.checkbox("Baja ingesta de calcio")

    with tabs[1]:
        st.subheader("Criterios diagnósticos y severidad")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            proteinuria_mg24 = st.number_input("Proteinuria 24 h (mg)", min_value=0.0, max_value=10000.0, value=0.0, step=50.0)
            relacion_prot_creat = st.number_input("Relación proteína/creatinina", min_value=0.0, max_value=20.0, value=0.0, step=0.1)
            tira_proteinas_2plus = st.checkbox("Tira reactiva ≥2+")
        with c2:
            plaquetas = st.number_input("Plaquetas (/µL)", min_value=0.0, max_value=600000.0, value=220000.0, step=1000.0)
            creatinina = st.number_input("Creatinina (mg/dL)", min_value=0.0, max_value=10.0, value=0.7, step=0.1)
            ast_alt_mayor_2x = st.checkbox("AST/ALT >2×")
        with c3:
            dolor_epigastrio = st.checkbox("Dolor epigástrico/HD")
            cefalea_visual = st.checkbox("Cefalea o síntomas visuales")
            edema_pulmonar = st.checkbox("Edema pulmonar")
            convulsion = st.checkbox("Convulsión/eclampsia")
        with c4:
            fgr_sospecha = st.checkbox("FGR/RCIU sospechado")
            doppler_uterino_anormal = st.checkbox("Doppler uterino anormal")
            plgf_bajo_o_sflt_alto = st.checkbox("PlGF bajo o sFlt-1/PlGF alto")

    with tabs[2]:
        st.subheader("Cardiografía de impedancia / hemodinamia basal")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ic = st.number_input("IC (L/min/m²)", min_value=0.0, max_value=10.0, value=3.6, step=0.1)
            irv = st.number_input("IRV / SVRI", min_value=0.0, max_value=7000.0, value=1600.0, step=50.0)
            fc = st.number_input("FC (lpm)", min_value=0.0, max_value=200.0, value=82.0, step=1.0)
        with c2:
            ca_ica = st.number_input("ICA / CA", min_value=0.0, max_value=10.0, value=1.8, step=0.1)
            ih = st.number_input("IH", min_value=0.0, max_value=80.0, value=18.0, step=0.5)
            iv = st.number_input("IV", min_value=0.0, max_value=200.0, value=50.0, step=1.0)
        with c3:
            iac = st.number_input("IAC", min_value=0.0, max_value=80.0, value=10.0, step=0.5)
            cts = st.number_input("CTS / PEP-LVET", min_value=0.0, max_value=2.0, value=0.35, step=0.01)
            cte = st.number_input("CTE", min_value=0.0, max_value=2.0, value=0.32, step=0.01)
        with c4:
            its_itc = st.number_input("ITS / ITC", min_value=0.0, max_value=200.0, value=45.0, step=1.0)
            cft = st.number_input("CFT / TFC", min_value=0.0, max_value=120.0, value=35.0, step=1.0)
            ea = st.number_input("Ea", min_value=0.0, max_value=20.0, value=1.8, step=0.1)
            ees = st.number_input("Ees", min_value=0.0, max_value=20.0, value=2.2, step=0.1)
            default_ac = round(ea / ees, 2) if ees else 0.0
            ac = st.number_input("EA/EES", min_value=0.0, max_value=10.0, value=float(default_ac), step=0.05)

    with tabs[3]:
        st.subheader("Respuesta ortostática opcional")
        st.caption("En el protocolo ICG embarazo puede registrarse decúbito/basal y bipedestación a 3 minutos. Normal esperado: IC desciende e IRV aumenta.")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ic_de_pie = st.number_input("IC de pie", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
        with c2:
            irv_de_pie = st.number_input("IRV de pie", min_value=0.0, max_value=7000.0, value=0.0, step=50.0)
        with c3:
            ca_de_pie = st.number_input("ICA/CA de pie", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
        with c4:
            ih_de_pie = st.number_input("IH de pie", min_value=0.0, max_value=80.0, value=0.0, step=0.5)

    return PatientInput(
        paciente=paciente,
        documento=documento,
        fecha=fecha,
        edad=edad,
        edad_gestacional=edad_gestacional,
        embarazo_multiple=embarazo_multiple,
        nulipara=nulipara,
        intervalo_embarazo_mayor_10=intervalo_embarazo_mayor_10,
        antecedente_pe=antecedente_pe,
        antecedente_fgr=antecedente_fgr,
        antecedente_familiar_pe=antecedente_familiar_pe,
        hta_cronica=hta_cronica,
        enfermedad_renal=enfermedad_renal,
        diabetes_previa=diabetes_previa,
        diabetes_gestacional=diabetes_gestacional,
        autoinmune_saf_lupus=autoinmune_saf_lupus,
        trombofilia=trombofilia,
        reproduccion_asistida=reproduccion_asistida,
        apnea_sueno=apnea_sueno,
        bmi=bmi,
        baja_ingesta_calcio=baja_ingesta_calcio,
        pas=pas,
        pad=pad,
        proteinuria_mg24=proteinuria_mg24,
        relacion_prot_creat=relacion_prot_creat,
        tira_proteinas_2plus=tira_proteinas_2plus,
        plaquetas=plaquetas,
        creatinina=creatinina,
        ast_alt_mayor_2x=ast_alt_mayor_2x,
        dolor_epigastrio=dolor_epigastrio,
        cefalea_visual=cefalea_visual,
        edema_pulmonar=edema_pulmonar,
        convulsion=convulsion,
        fgr_sospecha=fgr_sospecha,
        doppler_uterino_anormal=doppler_uterino_anormal,
        plgf_bajo_o_sflt_alto=plgf_bajo_o_sflt_alto,
        ic=ic,
        irv=irv,
        ca_ica=ca_ica,
        ih=ih,
        iv=iv,
        iac=iac,
        cts=cts,
        cte=cte,
        its_itc=its_itc,
        cft=cft,
        ea=ea,
        ees=ees,
        ac=ac,
        fc=fc,
        ic_de_pie=ic_de_pie,
        irv_de_pie=irv_de_pie,
        ca_de_pie=ca_de_pie,
        ih_de_pie=ih_de_pie,
    )


def render_results(p: PatientInput) -> None:
    pred = integrated_prediction(p)
    aspirin_dose = st.session_state.get("aspirin_dose", "150 mg/día")
    bp_target = st.session_state.get("bp_target", "≈135/85 mmHg")
    plan = management_plan(p, pred, aspirin_dose, bp_target)
    report_md = build_markdown_report(p, pred, plan)

    color_class = {"green": "risk-low", "orange": "risk-mid", "red": "risk-high"}.get(pred["color"], "risk-mid")
    badge_class = {"green": "badge-green", "orange": "badge-orange", "red": "badge-red"}.get(pred["color"], "badge-orange")

    st.markdown(
        f"""
        <div class="result-card {color_class}">
            <span class="badge {badge_class}">{pred['category']}</span>
            <span class="badge badge-blue">{pred['hemo']['phenotype']}</span>
            <h3 style="margin-top:10px">Resultado integrado</h3>
            <p><b>Diagnóstico clínico actual:</b> {pred['dx']['diagnosis']}<br>
            <b>Urgencia:</b> {pred['dx']['urgency']}<br>
            <b>Tipo probable:</b> {pred['pe_type']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Riesgo operativo", f"{pred['risk_percent']:.1f}%")
    c2.metric("IC", f"{p.ic:.2f}", pred["hemo"]["ic_class"])
    c3.metric("IRV", f"{p.irv:.0f}", pred["hemo"]["irv_class"])
    c4.metric("PAM", f"{mmhg_mean(p.pas,p.pad) or 0:.0f} mmHg")

    g1, g2 = st.columns([1.2, 1.0])
    with g1:
        st.pyplot(plot_hemo_quadrant(p, pred["hemo"]), clear_figure=True)
    with g2:
        st.pyplot(plot_risk_gauge(pred["risk_percent"]), clear_figure=True)

    st.subheader("Lectura clínica")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Factores y señales de riesgo**")
        items = []
        items += [f"Factor mayor: {x}" for x in pred["clinical"]["high_factors"]]
        items += [f"Factor moderado: {x}" for x in pred["clinical"]["moderate_factors"]]
        items += pred["flags"]
        items += pred["hemo_reasons"]
        if not items:
            items = ["Sin señales de alto riesgo ingresadas."]
        for x in items:
            st.write("• " + x)

    with col2:
        st.markdown("**Criterios de severidad / diagnóstico**")
        sev = pred["dx"]["severe_features"]
        if sev:
            for x in sev:
                st.error(x)
        else:
            st.success("No se cargaron criterios de severidad.")
        st.write(f"Proteinuria: {'positiva' if pred['dx']['proteinuria'] else 'no documentada/negativa'}")
        st.write(f"HTA actual: {'sí' if pred['dx']['htn'] else 'no'}")

    st.subheader("Plan de manejo sugerido")
    for section, items in plan.items():
        with st.expander(section, expanded=section in ["Prevención", "Tratamiento antihipertensivo", "Manejo guiado por hemodinamia"]):
            for item in items:
                st.write("• " + item)

    st.subheader("Informe")
    st.text_area("Informe editable", value=report_md, height=440)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Descargar informe .md", report_md.encode("utf-8"), "informe_preeclampsia.md", "text/markdown")
    with c2:
        st.download_button("⬇️ Descargar datos .xlsx", make_excel(p, pred, plan), "preeclampsia_smart_icg.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c3:
        try:
            pdf_bytes = make_pdf(report_md)
            st.download_button("⬇️ Descargar informe .pdf", pdf_bytes, "informe_preeclampsia.pdf", "application/pdf")
        except Exception as e:
            st.warning(f"PDF no disponible. Instale reportlab. Detalle: {e}")

    with st.expander("Base de conocimiento y límites"):
        st.markdown(
            """
            **Componentes del motor:**
            - Riesgo clínico basal: factores mayores y moderados.
            - Diagnóstico actual: PA, proteinuria, severidad materna y marcadores fetales.
            - Fenotipo ICG: IC/IRV por edad gestacional, ICA/CA, IH, EA/EES, CFT y respuesta ortostática.
            - Conducta: prevención, evaluación, tratamiento antihipertensivo, manejo hemodinámico y seguimiento.

            **Límites:**
            - El score no es un modelo calibrado poblacionalmente en esta versión.
            - Para publicar o usar como predictor autónomo se requiere validación externa, calibración, curva ROC, DCA y auditoría de falsos positivos/negativos.
            - Puede importarse luego un árbol J48 real exportado desde Weka/PMML/JSON para reemplazar el score operativo.
            """
        )


def render_batch() -> None:
    st.header("Evaluación masiva desde Excel/CSV")
    st.write("Columnas reconocidas: paciente, documento/DNI, edad, edad_gestacional/EG, PAS, PAD, IMC/BMI, IC, IRV, ICA/CA, IH, CTS, CTE, CFT, EA/EES.")
    up = st.file_uploader("Cargar Excel o CSV", type=["xlsx", "csv"], key="batch_file")
    if up is None:
        st.info("Suba una planilla para procesar múltiples pacientes.")
        return
    try:
        if up.name.lower().endswith(".csv"):
            df = pd.read_csv(up)
        else:
            df = pd.read_excel(up)
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")
        return

    st.write("Vista previa")
    st.dataframe(df.head(20), use_container_width=True)

    if st.button("Procesar cohorte"):
        res = process_batch(df)
        st.success(f"Procesadas {len(res)} filas.")
        st.dataframe(res, use_container_width=True)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            res.to_excel(writer, index=False, sheet_name="resultados")
        st.download_button(
            "⬇️ Descargar resultados batch",
            out.getvalue(),
            "resultados_preeclampsia_batch.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def render_references() -> None:
    st.header("Fundamento científico resumido")
    st.markdown(
        """
        Esta app integra tres líneas de razonamiento:

        1. **Clínica obstétrica actual**: diagnóstico de hipertensión del embarazo, proteinuria, criterios de severidad,
        prevención con AAS/calcio cuando corresponde, antihipertensivos seguros y derivación urgente en PA severa.
        2. **Hemodinamia materna**: la PE no es un fenotipo único; puede expresarse como patrón hipodinámico
        vasoconstrictor, normodinámico, hiperdinámico o desacoplado IC/IRV.
        3. **Aprendizaje automático local**: variables ICG como ICA/CA, IC, ITS/ITC, CTE e IH pueden aportar
        patrones ocultos de riesgo, especialmente en embarazadas de alto riesgo.

        **Próximo paso recomendado:** reemplazar el score operativo por el árbol J48 exacto o por un modelo calibrado
        con la base local; exportar métricas ROC, calibración, DCA y auditoría de errores.
        """
    )

    refs = [
        "Olano RD y cols. Modelo por inteligencia artificial con hemodinamia no invasiva para predecir preeclampsia. Rev Argent Cardiol. 2023.",
        "Olano D y cols. Prediction for the development of preeclampsia through non-invasive hemodynamics using machine learning, distinguishing early from late. Pregnancy Hypertension. 2025.",
        "Vasapollo B y cols. Maternal Hemodynamics from Preconception to Delivery. AIPE/SIMP Position Statement. Am J Perinatol. 2024.",
        "Ferrazzi E y cols. Maternal hemodynamics: a method to classify hypertensive disorders of pregnancy. AJOG. 2018.",
        "ACOG/SMFM. Low-dose aspirin use for prevention of preeclampsia.",
        "NICE NG133. Hypertension in pregnancy: diagnosis and management.",
        "WHO. Calcium supplementation during pregnancy to reduce the risk of pre-eclampsia.",
        "ISSHP. Classification, diagnosis and management recommendations for hypertensive disorders of pregnancy.",
    ]
    for r in refs:
        st.write("• " + r)


def main() -> None:
    render_header()

    main_tab, batch_tab, refs_tab = st.tabs(["🧭 Evaluación individual", "📊 Cohorte / Excel", "📚 Fundamento"])
    with main_tab:
        p = input_form()
        st.divider()
        if st.button("Calcular predicción y plan", type="primary"):
            render_results(p)
        else:
            st.info("Complete los datos y presione **Calcular predicción y plan**.")
    with batch_tab:
        render_batch()
    with refs_tab:
        render_references()


if __name__ == "__main__":
    main()
