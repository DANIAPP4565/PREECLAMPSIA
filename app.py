# -*- coding: utf-8 -*-
"""
APP PREECLAMPSIA - Z-LOGIC ICG
DOS IMPORTADORES REALES: INFORME COMPLETO + INFORME DE 4 HOJAS
Integración de variables, cuadrantes IC/IRV, ortostatismo y PDF médico.

Autor / Desarrollador: Dr. Olano Ricardo Daniel - Cardiólogo Hipertensólogo
"""

from __future__ import annotations

import io
import math
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

APP_VERSION = "Versión 2026-06-14L · OBLIGATORIO: DOS PDF SEPARADOS · BOTÓN COMPLETO + BOTÓN 4 HOJAS · INTEGRACIÓN FINAL"
AUTHOR = "Dr. Olano Ricardo Daniel - Cardiólogo Hipertensólogo"

st.set_page_config(
    page_title="Preeclampsia ICG Z-Logic",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# ESTILO
# ============================================================

def css() -> None:
    st.markdown(
        """
        <style>
        .stApp {background: linear-gradient(180deg,#eef6fb 0%,#f8fbfd 100%);} 
        .block-container {max-width: 1350px; padding-top: 1rem;}
        .hero {background:linear-gradient(135deg,#062a47,#0e5f88,#0f8f7a); color:#fff; border-radius:20px; padding:24px 28px; margin-bottom:18px; box-shadow:0 12px 30px rgba(15,23,42,.14);} 
        .hero h1,.hero p{color:#fff!important; margin:0;}
        .hero .ver{margin-top:8px;color:#dff6ff!important;font-weight:800;}
        .box {background:white; border:1px solid #dbe7ef; border-radius:18px; padding:18px; margin-bottom:16px; box-shadow:0 5px 18px rgba(15,23,42,.06);} 
        .ok {color:#065f46;font-weight:800}.warn{color:#92400e;font-weight:800}.bad{color:#991b1b;font-weight:800}
        .big-button-note {background:#fff7ed;border:2px solid #fb923c;border-radius:14px;padding:12px 14px;font-weight:800;color:#7c2d12;margin:8px 0 14px 0;}
        div.stButton > button {font-weight:800!important;border-radius:12px!important;}
        div.stDownloadButton > button {font-weight:800!important;border-radius:12px!important;}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# UTILIDADES
# ============================================================

def clean_num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float, np.number)) and not pd.isna(x):
        return float(x)
    s = str(x).strip()
    if not s or s.lower() in {"nan", "none", "sd", "---"}:
        return None
    s = re.sub(r"[^0-9,\.\-+]", "", s)
    if not s or s in {".", ",", "-", "+"}:
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


def fmt(x: Any, dec: int = 2) -> str:
    v = clean_num(x)
    if v is None:
        return "No disponible"
    return f"{v:.{dec}f}".replace(".", ",")


def norm(s: Any) -> str:
    s = str(s or "").lower()
    for a, b in {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ü":"u","ñ":"n"}.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def read_upload_bytes(up) -> bytes:
    try:
        up.seek(0)
    except Exception:
        pass
    b = up.read()
    try:
        up.seek(0)
    except Exception:
        pass
    return b


def pdf_pages_from_bytes(pdf_bytes: bytes) -> List[str]:
    pages: List[str] = []
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text(x_tolerance=1.5, y_tolerance=3) or ""
                pages.append(txt)
    except Exception:
        pages = []
    if not any(pages):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages = [(p.extract_text() or "") for p in reader.pages]
        except Exception:
            pages = []
    return pages


def nums_in_line(line: str) -> List[float]:
    out = []
    for m in re.findall(r"[-+]?\d+(?:[\.,]\d+)?%?", line):
        v = clean_num(m)
        if v is not None:
            out.append(v)
    return out

# ============================================================
# PARSER Z-LOGIC ESPECÍFICO PARA LOS DOS FORMATOS
# ============================================================

VAR_LABELS = {
    "FC": ["FC", "Frecuencia Cardíaca", "Frecuencia Cardiaca"],
    "PA": ["PA", "Presión Arterial S/D", "Presion Arterial S/D"],
    "PAS": ["PAS"],
    "PAD": ["PAD"],
    "PAM": ["PAM"],
    "DS": ["DS", "Descarga Sistólica", "Descarga Sistolica"],
    "IDS": ["IDS", "Indice de Descarga Sistólica", "Índice de Descarga Sistólica"],
    "VM": ["VM", "Volumen Minuto"],
    "IC": ["IC", "Indice Cardíaco", "Índice Cardíaco", "Indice Cardiaco"],
    "RVS": ["RVS", "Resistencia Vascular Sistémica", "Resistencia Vascular Sistemica"],
    "IRV": ["IRV", "Indice de Resistencia Vascular", "Índice de Resistencia Vascular", "Indice de Res. Vascular"],
    "CA": ["CA", "Complacencia Arterial"],
    "ICA": ["Indice de Complacencia Arterial", "Índice de Complacencia Arterial"],
    "IV": ["IV", "Indice de Velocidad", "Índice de Velocidad"],
    "IAC": ["IAC", "Indice de Aceleración Cardíaca", "Índice de Aceleración Cardíaca", "Indice de Aceleracion Cardiaca"],
    "CTS": ["CTS", "Cociente de Tiempo Sistólico", "Cociente de Tiempo Sistolico", "Coeficiente de Tiempo Sistólico"],
    "ITC": ["ITC", "Indice de Trabajo Cardíaco", "Índice de Trabajo Cardíaco", "Indice de Trabajo Cardiaco"],
    "CFT": ["CFT", "Contenido de Fluidos Torácicos", "Contenido de Fluidos Toracicos"],
    "CFTnr": ["CFT n.r.", "CFT n.r", "CFTnr"],
    "EA": ["EA"],
    "EES_W": ["EES (Weissler)"],
    "EES": ["EES (Capan)", "EES"],
    "AC_W": ["AC (Weissler)"],
    "AC": ["AC (Capan)", "AC"],
    "FE_W": ["FE (Weissler)"],
    "FE": ["FE (Capan)", "FE"],
    "Z0": ["Z0", "Z0 (Impedancia Basal)"],
    "RR": ["RR"],
    "PE": ["PE"],
    "PPE": ["PPE"],
    "DZDT": ["dz/dt", "dz/dt |max"],
    "IMC": ["IMC", "BMI"],
    "PESO": ["Peso"],
    "TALLA": ["Altura", "Talla"],
    "BSA": ["BSA", "SC"],
}

NORMAL_RANGES = {
    "IC": (2.2, 4.4),
    "IRV": (1400, 3100),
    "CA": (1.3, 3.2),
    "FC": (56, 87),
    "RVS": (800, 1600),
    "IAC": (134, 380),
    "CTS": (0.34, 0.51),
    "ITC": (3.0, 6.2),
    "CFT": (37, 48),
}

REFERENCE_EG = pd.DataFrame(
    {
        "semana": [10, 12, 16, 20, 24, 28, 32, 36, 40],
        "ic_media": [2.80, 3.00, 3.35, 3.80, 4.15, 4.35, 4.25, 4.00, 3.80],
        "ic_sd": [0.45, 0.45, 0.48, 0.50, 0.52, 0.52, 0.52, 0.50, 0.50],
        "irv_media": [2300, 2150, 1900, 1650, 1450, 1350, 1450, 1600, 1750],
        "irv_sd": [320, 310, 300, 280, 260, 260, 280, 300, 320],
    }
)


def extract_demographics(text: str) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    patterns = {
        "paciente": [r"Paciente\s+([^\n\r]+?)(?:\s+H\.C\.|$)", r"Nombre del paciente:\s*([^\n\r]+)"],
        "fecha_estudio": [r"Fecha\s+(\d{1,2}/\d{1,2}/\d{2,4})", r"La Plata,\s*(\d{1,2}/\d{1,2}/\d{2,4})"],
        "edad": [r"Edad\s+(\d{1,3})"],
        "sexo": [r"Sexo\s+([FM])\b"],
        "peso": [r"Peso\s+([0-9.,]+)\s*kg"],
        "talla": [r"(?:Altura|Talla)\s+([0-9.,]+)\s*cm"],
        "imc": [r"(?:BMI|IMC)\s+([0-9.,]+)"],
        "bsa": [r"(?:BSA|SC)\s+([0-9.,]+)\s*m2"],
        "diagnostico": [r"Diagn[oó]stico\s+([^\n\r]+)"],
        "situacion": [r"Situaci[oó]n\s+([^\n\r]+)", r"ESTUDIO BASAL\s*\(([^\)]+)\)"],
    }
    for k, pats in patterns.items():
        for pat in pats:
            m = re.search(pat, text, flags=re.I)
            if m:
                d[k] = m.group(1).strip(" -|;:")
                break
    # Edad gestacional desde diagnóstico tipo HTA Y EMB S11.
    diag = str(d.get("diagnostico", ""))
    m = re.search(r"\b(?:S|SEM|SEMANA)\s*(\d{1,2})(?:[+\.]([0-6]))?\b", diag, flags=re.I)
    if m:
        d["edad_gestacional"] = float(m.group(1)) + (float(m.group(2) or 0) / 7.0)
    else:
        # Búsqueda global de EG.
        m = re.search(r"(?:edad gestacional|eg|emb\s*s)\s*(\d{1,2})(?:[+\.]([0-6]))?", norm(text), flags=re.I)
        if m:
            d["edad_gestacional"] = float(m.group(1)) + (float(m.group(2) or 0) / 7.0)
    return d


def parse_pressure(s: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})\s*\(?\s*(\d{2,3})?\s*\)?", s)
    if not m:
        return None, None, None
    return clean_num(m.group(1)), clean_num(m.group(2)), clean_num(m.group(3))


def set_var(pos: Dict[str, Dict[str, Any]], position: str, var: str, value: Any, source: str, conflicts: List[Dict[str, Any]]) -> None:
    v = clean_num(value)
    if v is None:
        return
    if var in {"CTS", "CTE", "AC"} and v > 2:
        v = v / 100.0
    pos.setdefault(position, {})
    src_key = f"_{var}_fuente"
    old = clean_num(pos[position].get(var))
    if old is not None and abs(old - v) > max(0.02, abs(old) * 0.03):
        conflicts.append({"Posición": position, "Variable": var, "Valor previo": old, "Valor nuevo": v, "Fuente nueva": source})
        # Mantiene el primer valor; el editor permite corregir.
        return
    pos[position][var] = v
    pos[position][src_key] = source


def parse_complete_pdf(pdf_bytes: bytes, filename: str = "COMPLETO") -> Dict[str, Any]:
    pages = pdf_pages_from_bytes(pdf_bytes)
    text = "\n".join(pages)
    demo = extract_demographics(text)
    position = "Acostado"
    if norm(demo.get("situacion")):
        if "parado" in norm(demo.get("situacion")) or "pie" in norm(demo.get("situacion")):
            position = "Parado"
        else:
            position = "Acostado"
    pos: Dict[str, Dict[str, Any]] = {position: {}}
    conflicts: List[Dict[str, Any]] = []

    # Parse por líneas del informe completo de 1 página.
    for line in text.splitlines():
        line_n = norm(line)
        # Presión arterial
        if re.search(r"\bPA\b|presion arterial|sistolica/diastolica", line_n):
            pas, pad, pam = parse_pressure(line)
            set_var(pos, position, "PAS", pas, f"{filename}: PA", conflicts)
            set_var(pos, position, "PAD", pad, f"{filename}: PA", conflicts)
            set_var(pos, position, "PAM", pam, f"{filename}: PA", conflicts)
        # Variables con etiqueta clara.
        patterns = [
            ("FC", r"(?:\bFC\b|Frecuencia Card[ií]aca)\D+([0-9.,]+)"),
            ("DS", r"(?:^\s*DS\b|^\s*Descarga Sist[oó]lica)\D+([0-9.,]+)"),
            ("IDS", r"(?:\bIDS\b|Indice de Descarga Sist[oó]lica|Índice de Descarga Sist[oó]lica)\D+([0-9.,]+)"),
            ("VM", r"(?:\bVM\b|Volumen Minuto)\D+([0-9.,]+)"),
            ("IC", r"(?:\bIC\b|Indice Card[ií]aco|Índice Card[ií]aco)\D+([0-9.,]+)"),
            ("RVS", r"(?:\bRVS\b|Resistencia Vascular Sist[eé]mica)\D+([0-9.,]+)"),
            ("IRV", r"(?:\bIRV\b|Indice de Resistencia Vascular|Índice de Resistencia Vascular)\D+([0-9.,]+)"),
            ("CA", r"(?:\bCA\b|Complacencia Arterial)\D+([0-9.,]+)"),
            ("IV", r"(?:\bIV\b|Indice de Velocidad|Índice de Velocidad)\D+([0-9.,]+)"),
            ("IAC", r"(?:\bIAC\b|Indice de Aceleraci[oó]n Card[ií]aca|Índice de Aceleraci[oó]n Card[ií]aca)\D+([0-9.,]+)"),
            ("CTS", r"(?:\bCTS\b|Cociente de Tiempo Sist[oó]lico)\D+([0-9.,]+)\s*%?"),
            ("ITC", r"(?:\bITC\b|Indice de Trabajo Card[ií]aco|Índice de Trabajo Card[ií]aco)\D+([0-9.,]+)"),
            ("CFT", r"(?:\bCFT\b|Contenido de Fluidos Tor[aá]cicos)\D+([0-9.,]+)"),
            ("Z0", r"\bZ0\D+([0-9.,]+)"),
            ("RR", r"\bRR\D+([0-9.,]+)"),
        ]
        for var, pat in patterns:
            m = re.search(pat, line, flags=re.I)
            if m:
                set_var(pos, position, var, m.group(1), f"{filename}: {line[:80]}", conflicts)
    for var, k in [("PESO", "peso"), ("TALLA", "talla"), ("IMC", "imc"), ("BSA", "bsa")]:
        set_var(pos, position, var, demo.get(k), f"{filename}: demografía", conflicts)
    return {"tipo": "COMPLETO", "filename": filename, "pages": pages, "text": text, "demo": demo, "positions": pos, "conflicts": conflicts}


def parse_rows_three_positions(text: str, pos: Dict[str, Dict[str, Any]], source: str, conflicts: List[Dict[str, Any]]) -> None:
    """Parsea filas del informe de 4 hojas que traen Acostado / Sentado / Parado.

    Maneja dos formatos del PDF:
    1) etiqueta y valores en la misma línea: Indice Cardíaco 5.7 3.6 3.2 ---
    2) etiqueta en una línea y valores en la siguiente: EA\n0.59 1.17 1.28 ---
    """
    row_map = {
        "Presión Arterial S/D (M)": "PA", "Presion Arterial S/D (M)": "PA",
        "Indice de Descarga Sistólica": "IDS", "Índice de Descarga Sistólica": "IDS", "Indice de Descarga Sistolica": "IDS",
        "Indice de Res. Vascular": "IRV", "Indice de Resistencia Vascular": "IRV", "Índice de Resistencia Vascular": "IRV",
        "Resistencia Vascular Sistémica": "RVS", "Resistencia Vascular Sistemica": "RVS",
        "Contenido de Fluidos Torácicos": "CFT", "Contenido de Fluidos Toracicos": "CFT",
        "Z0 (Impedancia Basal)": "Z0",
        "Descarga Sistólica": "DS", "Descarga Sistolica": "DS",
        "Frecuencia Cardíaca": "FC", "Frecuencia Cardiaca": "FC",
        "Indice Cardíaco": "IC", "Indice Cardiaco": "IC", "Índice Cardíaco": "IC",
        "Complacencia Arterial": "CA",
        "Presión de Pulso": "PP", "Presion de Pulso": "PP",
        "Volumen Minuto": "VM",
        "FE (Weissler)": "FE_W", "FE (Capan)": "FE",
        "RPVFSE Suga": "RPVFSE",
        "IC/PAS": "IC_PAS",
        "ISRVS": "ISRVS",
        "CFT n.r.": "CFTnr", "CFT n.r": "CFTnr",
        "EES (Weissler)": "EES_W",
        "EES (Capan)": "EES",
        "AC (Weissler)": "AC_W",
        "AC (Capan)": "AC",
        "EA": "EA",
    }
    labels = sorted(row_map, key=len, reverse=True)
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    candidates: List[str] = list(raw_lines)
    # Une etiqueta sola + línea de valores para variables adicionales de página 4.
    # Evita falsos positivos de la página basal como: "Frecuencia Cardíaca" + "67 ... Peso 92 Edad 32".
    for i in range(len(raw_lines) - 1):
        line = raw_lines[i]
        line_norm = norm(line)
        next_line = raw_lines[i + 1]
        next_norm = norm(next_line)
        is_exact_label = any(line_norm == norm(label) for label in labels)
        next_looks_like_values = len(nums_in_line(next_line)) >= 3 and (
            "---" in next_line or re.fullmatch(r"[0-9.,+\-\s]+", next_line) is not None
        )
        has_demographic_noise = any(w in next_norm for w in ["peso", "edad", "sexo", "altura", "sc ", " imc", "bmi"])
        if is_exact_label and next_looks_like_values and not has_demographic_noise:
            candidates.append(f"{line} {next_line}")

    for line in candidates:
        line_norm = norm(line)
        for label in labels:
            label_norm = norm(label)
            # Requiere que el rótulo esté al inicio de la línea para evitar que
            # "Descarga Sistólica" se lea dentro de "Índice de Descarga Sistólica".
            if not re.match(rf"^{re.escape(label_norm)}(\b|\s)", line_norm):
                continue
            var = row_map[label]
            if var == "PA":
                triples = re.findall(r"(\d{2,3})\s*/\s*(\d{2,3})\s*\((\d{2,3})\)", line)
                for p_name, triple in zip(["Acostado", "Sentado", "Parado"], triples[:3]):
                    set_var(pos, p_name, "PAS", triple[0], source, conflicts)
                    set_var(pos, p_name, "PAD", triple[1], source, conflicts)
                    set_var(pos, p_name, "PAM", triple[2], source, conflicts)
                break
            nums = nums_in_line(line)
            if var == "Z0" and len(nums) >= 4 and nums[0] == 0:
                # Evita que el cero de la etiqueta Z0 sea tomado como valor Acostado.
                nums = nums[1:]
            if len(nums) >= 3:
                values = nums[:3]
                for p_name, val in zip(["Acostado", "Sentado", "Parado"], values):
                    set_var(pos, p_name, var, val, source, conflicts)
            break

def parse_four_pages_pdf(pdf_bytes: bytes, filename: str = "4_HOJAS") -> Dict[str, Any]:
    pages = pdf_pages_from_bytes(pdf_bytes)
    text = "\n".join(pages)
    demo = extract_demographics(text)
    pos: Dict[str, Dict[str, Any]] = {"Acostado": {}, "Sentado": {}, "Parado": {}}
    conflicts: List[Dict[str, Any]] = []

    # Basal page 2: para el caso en que page 3 no se lea, se rescatan valores principales.
    for line in text.splitlines():
        if "Presión Arterial" in line or "Presion Arterial" in line:
            pas, pad, pam = parse_pressure(line)
            set_var(pos, "Acostado", "PAS", pas, f"{filename}: PA basal", conflicts)
            set_var(pos, "Acostado", "PAD", pad, f"{filename}: PA basal", conflicts)
            set_var(pos, "Acostado", "PAM", pam, f"{filename}: PA basal", conflicts)

    parse_rows_three_positions(text, pos, filename, conflicts)

    # En página 2, algunos rótulos tienen valor en línea siguiente. Se rescatan con patrones de bloque.
    block_patterns = [
        ("FC", r"Frecuencia Card[ií]aca\s+([0-9.,]+)"),
        ("IC", r"Indice Card[ií]aco\s+([0-9.,]+)"),
        ("DS", r"Descarga Sist[oó]lica\s+([0-9.,]+)"),
        ("IDS", r"Indice de Descarga Sist[oó]lica\s+([0-9.,]+)"),
        ("VM", r"Volumen Minuto\s+([0-9.,]+)"),
        ("IRV", r"Indice de Resistencia Vascular\s+([0-9.,]+)"),
        ("RVS", r"Resistencia Vascular Sist[eé]mica\s+([0-9.,]+)"),
        ("CA", r"Complacencia Arterial\s+([0-9.,]+)"),
        ("ICA", r"Indice de Complacencia Arterial\s+([0-9.,]+)"),
    ]
    # Reemplaza saltos con espacios, pero conserva orden.
    flat = re.sub(r"\s+", " ", text)
    for var, pat in block_patterns:
        m = re.search(pat, flat, flags=re.I)
        if m:
            set_var(pos, "Acostado", var, m.group(1), f"{filename}: basal", conflicts)

    for var, k in [("PESO", "peso"), ("TALLA", "talla"), ("IMC", "imc"), ("BSA", "bsa")]:
        for p in ["Acostado", "Sentado", "Parado"]:
            set_var(pos, p, var, demo.get(k), f"{filename}: demografía", conflicts)

    # Calcula AC si falta y están EA/EES.
    for p_name, values in pos.items():
        if clean_num(values.get("AC")) is None and clean_num(values.get("EA")) is not None and clean_num(values.get("EES")):
            set_var(pos, p_name, "AC", clean_num(values["EA"]) / clean_num(values["EES"]), f"{filename}: calculado EA/EES", conflicts)
    return {"tipo": "4_HOJAS", "filename": filename, "pages": pages, "text": text, "demo": demo, "positions": pos, "conflicts": conflicts}


def merge_demographics(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(b or {})
    for k, v in (a or {}).items():
        if v not in (None, "", "---"):
            out[k] = v
    return out


def integrate_two_reports(complete: Dict[str, Any], four: Dict[str, Any]) -> Dict[str, Any]:
    conflicts: List[Dict[str, Any]] = []
    positions: Dict[str, Dict[str, Any]] = {"Acostado": {}, "Sentado": {}, "Parado": {}}

    # Primero se carga 4 hojas porque aporta ortostatismo y variables adicionales.
    for p, vals in (four.get("positions") or {}).items():
        canonical = "Acostado" if "acost" in norm(p) or "basal" in norm(p) else "Parado" if "parad" in norm(p) or "pie" in norm(p) else "Sentado" if "sent" in norm(p) else p
        positions.setdefault(canonical, {})
        for k, v in vals.items():
            if not k.startswith("_"):
                positions[canonical][k] = v
                positions[canonical][f"_{k}_fuente"] = vals.get(f"_{k}_fuente", "4 hojas")

    # Luego el informe completo complementa/valida basal Acostado.
    for p, vals in (complete.get("positions") or {}).items():
        canonical = "Acostado" if "acost" in norm(p) or "basal" in norm(p) or "cinta" in norm(p) else p
        positions.setdefault(canonical, {})
        for k, v in vals.items():
            if k.startswith("_"):
                continue
            old = clean_num(positions[canonical].get(k))
            new = clean_num(v)
            if new is None:
                continue
            if old is not None and abs(old - new) > max(0.02, abs(old) * 0.03):
                conflicts.append({"Posición": canonical, "Variable": k, "4 hojas": old, "Completo": new, "Decisión": "se conserva COMPLETO para basal; corregir en editor si corresponde"})
            # El informe completo es la fuente basal detallada: actualiza Acostado.
            positions[canonical][k] = new
            positions[canonical][f"_{k}_fuente"] = vals.get(f"_{k}_fuente", "completo")

    demo = merge_demographics(complete.get("demo", {}), four.get("demo", {}))
    audit = []
    all_vars = sorted({k for p in positions.values() for k in p.keys() if not k.startswith("_")})
    for var in all_vars:
        audit.append({
            "Variable": var,
            "Acostado": positions.get("Acostado", {}).get(var),
            "Sentado": positions.get("Sentado", {}).get(var),
            "Parado": positions.get("Parado", {}).get(var),
            "Fuente acostado": positions.get("Acostado", {}).get(f"_{var}_fuente", ""),
            "Fuente parado": positions.get("Parado", {}).get(f"_{var}_fuente", ""),
        })
    return {"demo": demo, "positions": positions, "conflicts": conflicts + complete.get("conflicts", []) + four.get("conflicts", []), "audit": audit}

# ============================================================
# ANÁLISIS Y GRÁFICOS
# ============================================================

def ref_at_week(week: Optional[float]) -> Dict[str, float]:
    w = 24.0 if clean_num(week) is None else float(clean_num(week))
    w = float(np.clip(w, REFERENCE_EG.semana.min(), REFERENCE_EG.semana.max()))
    return {
        "week": w,
        "ic_media": float(np.interp(w, REFERENCE_EG.semana, REFERENCE_EG.ic_media)),
        "ic_sd": float(np.interp(w, REFERENCE_EG.semana, REFERENCE_EG.ic_sd)),
        "irv_media": float(np.interp(w, REFERENCE_EG.semana, REFERENCE_EG.irv_media)),
        "irv_sd": float(np.interp(w, REFERENCE_EG.semana, REFERENCE_EG.irv_sd)),
    }


def z(value: Any, mean: float, sd: float) -> Optional[float]:
    v = clean_num(value)
    if v is None or sd == 0:
        return None
    return (v - mean) / sd


def hemo_diagnosis(acostado: Dict[str, Any], eg: Optional[float]) -> Dict[str, Any]:
    ref = ref_at_week(eg)
    ic = clean_num(acostado.get("IC"))
    irv = clean_num(acostado.get("IRV"))
    zic = z(ic, ref["ic_media"], ref["ic_sd"])
    zirv = z(irv, ref["irv_media"], ref["irv_sd"])
    ic_level = "No disponible" if zic is None else "bajo para EG" if zic <= -1 else "elevado para EG" if zic >= 1 else "normal para EG"
    irv_level = "No disponible" if zirv is None else "bajo para EG" if zirv <= -1 else "elevado para EG" if zirv >= 1 else "normal para EG"
    if ic is None or irv is None:
        profile = "No clasificable: falta IC o IRV"
    elif zic is not None and zirv is not None and zic >= 1 and zirv <= -1:
        profile = "Hiperdinamia: IC elevado con IRV baja para la EG"
    elif zic is not None and zirv is not None and zic <= -1 and zirv >= 1:
        profile = "Hipodinamia: IC bajo con IRV elevada para la EG"
    elif zic is not None and zirv is not None and -1 < zic < 1 and zirv >= 1:
        profile = "IC normal con IRV inadecuadamente elevada para la EG"
    elif zic is not None and zirv is not None and zic >= 1 and -1 < zirv < 1:
        profile = "IC elevado con IRV normal para la EG"
    elif zic is not None and zirv is not None and -1 < zic < 1 and -1 < zirv < 1:
        profile = "Normodinamia para edad gestacional"
    else:
        profile = "Alteración hemodinámica parcial"
    return {"profile": profile, "ic_level": ic_level, "irv_level": irv_level, "zic": zic, "zirv": zirv, "ref": ref}


def ortho_analysis(acostado: Dict[str, Any], parado: Dict[str, Any]) -> Tuple[pd.DataFrame, str]:
    variables = ["IC", "IRV", "CA", "FC", "DS", "IDS", "VM", "RVS", "CFT", "CFTnr", "EA", "EES", "AC"]
    rows = []
    for var in variables:
        a = clean_num(acostado.get(var))
        p = clean_num(parado.get(var))
        if a is None and p is None:
            continue
        delta = None if a is None or p is None else p - a
        delta_pct = None if a in (None, 0) or p is None else 100 * (p - a) / a
        rows.append({"Variable": var, "Acostado": a, "Parado": p, "Delta": delta, "Delta %": delta_pct})
    df = pd.DataFrame(rows)
    ic_a, ic_p = clean_num(acostado.get("IC")), clean_num(parado.get("IC"))
    irv_a, irv_p = clean_num(acostado.get("IRV")), clean_num(parado.get("IRV"))
    if ic_a is None or ic_p is None or irv_a is None or irv_p is None:
        interp = "No se puede interpretar ortostatismo porque falta IC o IRV en acostado/parado."
    elif ic_p < ic_a and irv_p > irv_a:
        interp = "Patrón ortostático esperado: al pasar a bipedestación baja el IC y sube la IRV."
    elif ic_p >= ic_a and irv_p <= irv_a:
        interp = "Patrón ortostático no esperado: no cae el IC y no aumenta la IRV; revisar adaptación autonómica/volemia/técnica."
    else:
        interp = "Respuesta ortostática parcial o discordante; interpretar con PA, FC, CFT y calidad de señal."
    return df, interp


def j48_ml(acostado: Dict[str, Any]) -> Dict[str, str]:
    # Árbol J48 Olano 2025 operativo: STR/CTS, IA/IAC, ELV/EES y ACI/CA.
    cts = clean_num(acostado.get("CTS"))
    ia = clean_num(acostado.get("IAC"))
    ees = clean_num(acostado.get("EES"))
    ca = clean_num(acostado.get("CA"))
    if cts is None:
        return {"resultado": "No clasificable por ML J48", "ruta": "Falta STR/CTS"}
    cts_pct = cts * 100 if cts <= 2 else cts
    ruta = [f"STR/CTS={cts_pct:.2f}%"]
    if cts_pct > 43.37:
        ruta.append(">43,37")
        return {"resultado": "PE tardía / materno-metabólica por J48", "ruta": " → ".join(ruta)}
    if ia is None:
        return {"resultado": "No clasificable por ML J48", "ruta": " → ".join(ruta + ["falta IA/IAC"])}
    ruta.append(f"IA/IAC={ia:.2f}")
    if ia <= 190.87:
        ruta.append("<=190,87")
        return {"resultado": "PE tardía / materno-metabólica por J48", "ruta": " → ".join(ruta)}
    if ees is None:
        return {"resultado": "No clasificable por ML J48", "ruta": " → ".join(ruta + ["falta ELV/EES"])}
    ruta.append(f"EES/ELV={ees:.2f}")
    if ees > 1.53:
        ruta.append(">1,53")
        return {"resultado": "PE temprana / placentaria por J48", "ruta": " → ".join(ruta)}
    if cts_pct > 41.21:
        ruta.append("STR/CTS>41,21")
        return {"resultado": "PE temprana / placentaria por J48", "ruta": " → ".join(ruta)}
    if ca is None:
        return {"resultado": "No clasificable por ML J48", "ruta": " → ".join(ruta + ["falta ACI/CA"])}
    ruta.append(f"ACI/CA={ca:.2f}")
    if ca <= 1.30:
        return {"resultado": "PE tardía / materno-metabólica por J48", "ruta": " → ".join(ruta + ["<=1,30"])}
    if ca <= 1.51:
        return {"resultado": "PE temprana / placentaria por J48", "ruta": " → ".join(ruta + ["<=1,51"])}
    return {"resultado": "PE tardía / materno-metabólica por J48", "ruta": " → ".join(ruta + [">1,51"])}


def fig_to_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()


def plot_quadrant_units(acostado: Dict[str, Any], parado: Optional[Dict[str, Any]] = None) -> Tuple[plt.Figure, bytes]:
    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    ax.axvspan(2.2, 4.4, ymin=0, ymax=1, alpha=0.08)
    ax.axhspan(1400, 3100, xmin=0, xmax=1, alpha=0.08)
    ax.axvline(2.2, linestyle="--", linewidth=1)
    ax.axvline(4.4, linestyle="--", linewidth=1)
    ax.axhline(1400, linestyle="--", linewidth=1)
    ax.axhline(3100, linestyle="--", linewidth=1)
    ax.set_xlim(1.0, 6.5)
    ax.set_ylim(800, 4500)
    ax.set_xlabel("Índice cardíaco IC (L/min/m²)")
    ax.set_ylabel("Índice de resistencia vascular IRV (dyn·s·cm⁻5·m²)")
    ax.set_title("Cuadrante IC/IRV con punto del paciente")
    ax.text(1.15, 4100, "Hipodinamia\nIC bajo / IRV alta", fontsize=9, va="top")
    ax.text(4.6, 950, "Hiperdinamia\nIC alto / IRV baja", fontsize=9, va="bottom")
    ax.text(2.45, 2600, "zona de referencia Z-Logic", fontsize=9)
    ic_a, irv_a = clean_num(acostado.get("IC")), clean_num(acostado.get("IRV"))
    if ic_a is not None and irv_a is not None:
        ax.scatter(ic_a, irv_a, s=120, marker="o", label="Acostado / basal")
        ax.annotate(f"Acostado\nIC {fmt(ic_a,1)} / IRV {fmt(irv_a,0)}", (ic_a, irv_a), xytext=(8, 8), textcoords="offset points")
    if parado:
        ic_p, irv_p = clean_num(parado.get("IC")), clean_num(parado.get("IRV"))
        if ic_p is not None and irv_p is not None:
            ax.scatter(ic_p, irv_p, s=120, marker="s", label="Parado / bipedestación")
            ax.annotate(f"Parado\nIC {fmt(ic_p,1)} / IRV {fmt(irv_p,0)}", (ic_p, irv_p), xytext=(8, -28), textcoords="offset points")
            if ic_a is not None and irv_a is not None:
                ax.annotate("", xy=(ic_p, irv_p), xytext=(ic_a, irv_a), arrowprops=dict(arrowstyle="->", lw=2))
                ax.text((ic_a + ic_p) / 2, (irv_a + irv_p) / 2, "acostado → parado", fontsize=9)
    ax.grid(True, alpha=.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig, fig_to_bytes(fig)


def plot_eg(acostado: Dict[str, Any], eg: Optional[float]) -> Tuple[plt.Figure, bytes]:
    weeks = np.linspace(REFERENCE_EG.semana.min(), REFERENCE_EG.semana.max(), 200)
    ic_mean = np.interp(weeks, REFERENCE_EG.semana, REFERENCE_EG.ic_media)
    ic_sd = np.interp(weeks, REFERENCE_EG.semana, REFERENCE_EG.ic_sd)
    irv_mean = np.interp(weeks, REFERENCE_EG.semana, REFERENCE_EG.irv_media)
    irv_sd = np.interp(weeks, REFERENCE_EG.semana, REFERENCE_EG.irv_sd)
    ic, irv, egv = clean_num(acostado.get("IC")), clean_num(acostado.get("IRV")), clean_num(eg)
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.6))
    axes[0].plot(weeks, ic_mean, label="Media")
    axes[0].fill_between(weeks, ic_mean-ic_sd, ic_mean+ic_sd, alpha=.18, label="±1 DE")
    if ic is not None and egv is not None:
        axes[0].scatter([egv], [ic], s=100, label="Paciente")
        axes[0].annotate(f"IC {fmt(ic,1)}", (egv, ic), xytext=(8, 8), textcoords="offset points")
    axes[0].set_title("IC vs edad gestacional")
    axes[0].set_xlabel("Semanas")
    axes[0].set_ylabel("IC")
    axes[0].grid(True, alpha=.25)
    axes[0].legend(fontsize=8)
    axes[1].plot(weeks, irv_mean, label="Media")
    axes[1].fill_between(weeks, irv_mean-irv_sd, irv_mean+irv_sd, alpha=.18, label="±1 DE")
    if irv is not None and egv is not None:
        axes[1].scatter([egv], [irv], s=100, label="Paciente")
        axes[1].annotate(f"IRV {fmt(irv,0)}", (egv, irv), xytext=(8, 8), textcoords="offset points")
    axes[1].set_title("IRV vs edad gestacional")
    axes[1].set_xlabel("Semanas")
    axes[1].set_ylabel("IRV")
    axes[1].grid(True, alpha=.25)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    return fig, fig_to_bytes(fig)

# ============================================================
# PDF Y EXPORTACIONES
# ============================================================

def temp_image(b: Optional[bytes]) -> Optional[str]:
    if not b:
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(b)
    tmp.close()
    return tmp.name


def make_pdf(demo: Dict[str, Any], positions: Dict[str, Dict[str, Any]], hemo: Dict[str, Any], ortho_df: pd.DataFrame, ortho_text: str, ml: Dict[str, str], fig_quad_b: bytes, fig_eg_b: bytes, logo_b: Optional[bytes], firma_b: Optional[bytes], medico: str, institucion: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.2*cm, leftMargin=1.2*cm, topMargin=1*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="T", parent=styles["Title"], alignment=TA_CENTER, fontSize=14, textColor=colors.HexColor("#0B3D6E")))
    styles.add(ParagraphStyle(name="H", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#0B3D6E")))
    styles.add(ParagraphStyle(name="S", parent=styles["BodyText"], fontSize=8, leading=10))
    story: List[Any] = []
    logo = temp_image(logo_b)
    if logo:
        story.append(RLImage(logo, width=3.0*cm, height=1.8*cm, kind="proportional"))
    story.append(Paragraph("INFORME HEMODINÁMICO MATERNO ICG - PREECLAMPSIA", styles["T"]))
    if institucion:
        story.append(Paragraph(institucion, styles["S"]))
    story.append(Spacer(1, .15*cm))
    data = [
        ["Paciente", demo.get("paciente", "No disponible"), "Fecha", demo.get("fecha_estudio", "No disponible")],
        ["Edad", demo.get("edad", ""), "Edad gestacional", f"{fmt(demo.get('edad_gestacional'),1)} semanas"],
        ["Diagnóstico", demo.get("diagnostico", ""), "Médico", medico],
    ]
    t = Table(data, colWidths=[2.6*cm, 6.5*cm, 3*cm, 5.5*cm])
    t.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .25, colors.grey), ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#EAF3FB")), ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#EAF3FB")), ("FONTSIZE", (0,0), (-1,-1), 8)]))
    story.append(t)
    story.append(Paragraph("Diagnóstico integrado", styles["H"]))
    story.append(Paragraph(f"Fenotipo: {hemo.get('profile')}", styles["S"]))
    story.append(Paragraph(f"IC: {fmt(positions.get('Acostado',{}).get('IC'),2)} ({hemo.get('ic_level')}) - IRV: {fmt(positions.get('Acostado',{}).get('IRV'),0)} ({hemo.get('irv_level')})", styles["S"]))
    story.append(Paragraph(f"ML J48: {ml.get('resultado')} | Ruta: {ml.get('ruta')}", styles["S"]))
    story.append(Paragraph("Ortostatismo", styles["H"]))
    story.append(Paragraph(ortho_text, styles["S"]))
    if not ortho_df.empty:
        table_data = [["Variable", "Acostado", "Parado", "Delta", "Delta %"]]
        for _, r in ortho_df.iterrows():
            table_data.append([str(r["Variable"]), fmt(r["Acostado"],2), fmt(r["Parado"],2), fmt(r["Delta"],2), fmt(r["Delta %"],1)])
        tt = Table(table_data, colWidths=[3*cm, 3*cm, 3*cm, 3*cm, 3*cm])
        tt.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .25, colors.grey), ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B3D6E")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTSIZE", (0,0), (-1,-1), 7)]))
        story.append(tt)
    for title, img_b in [("Cuadrante y desplazamiento IC/IRV", fig_quad_b), ("IC e IRV vs edad gestacional", fig_eg_b)]:
        story.append(Paragraph(title, styles["H"]))
        img = temp_image(img_b)
        if img:
            story.append(RLImage(img, width=16.5*cm, height=8*cm, kind="proportional"))
    firma = temp_image(firma_b)
    if firma:
        story.append(Spacer(1, .2*cm))
        story.append(RLImage(firma, width=5*cm, height=2.2*cm, kind="proportional"))
    story.append(Paragraph(f"Firma y sello: {medico}", styles["S"]))
    story.append(Paragraph("Herramienta de apoyo clínico. No reemplaza el juicio médico ni las guías obstétricas vigentes.", styles["S"]))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def excel_bytes(demo: Dict[str, Any], positions: Dict[str, Dict[str, Any]], audit: List[Dict[str, Any]], conflicts: List[Dict[str, Any]], ortho: pd.DataFrame, hemo: Dict[str, Any], ml: Dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([demo]).to_excel(writer, index=False, sheet_name="Paciente")
        for p, vals in positions.items():
            pd.DataFrame([{"Variable": k, "Valor": v} for k, v in vals.items() if not k.startswith("_")]).to_excel(writer, index=False, sheet_name=p[:31])
        pd.DataFrame(audit).to_excel(writer, index=False, sheet_name="Auditoria")
        pd.DataFrame(conflicts).to_excel(writer, index=False, sheet_name="Conflictos")
        ortho.to_excel(writer, index=False, sheet_name="Ortostatismo")
        pd.DataFrame([hemo]).to_excel(writer, index=False, sheet_name="Hemodinamia")
        pd.DataFrame([ml]).to_excel(writer, index=False, sheet_name="ML")
    buf.seek(0)
    return buf.getvalue()

# ============================================================
# UI
# ============================================================

def sidebar() -> Tuple[Optional[bytes], Optional[bytes], str, str]:
    st.sidebar.header("Firma e institución")
    medico = st.sidebar.text_input("Médico firmante", value=AUTHOR)
    institucion = st.sidebar.text_input("Institución", value="")
    logo = st.sidebar.file_uploader("Logo institucional", type=["png", "jpg", "jpeg"], key="logo")
    firma = st.sidebar.file_uploader("Firma con sello", type=["png", "jpg", "jpeg"], key="firma")
    logo_b = read_upload_bytes(logo) if logo else None
    firma_b = read_upload_bytes(firma) if firma else None
    return logo_b, firma_b, medico, institucion


def show_parsed_card(name: str, parsed: Dict[str, Any]) -> None:
    pos = parsed.get("positions", {})
    nvars = sum(1 for vals in pos.values() for k in vals if not k.startswith("_"))
    st.success(f"{name} importado: {len(parsed.get('pages', []))} página(s), {nvars} valores detectados.")
    with st.expander(f"Auditoría {name}", expanded=False):
        st.write("Demografía detectada")
        st.json(parsed.get("demo", {}))
        rows = []
        for p, vals in pos.items():
            for k, v in vals.items():
                if not k.startswith("_"):
                    rows.append({"Posición": p, "Variable": k, "Valor": v, "Fuente": vals.get(f"_{k}_fuente", "")})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.text_area("Texto extraído", parsed.get("text", "")[:12000], height=220, key=f"text_{name}")


def dual_pdf_flow(logo_b: Optional[bytes], firma_b: Optional[bytes], medico: str, institucion: str) -> None:
    st.markdown("## PDF Z-Logic: DOS PDF SEPARADOS OBLIGATORIOS")
    st.error("NO USAR UN SOLO PDF: esta pantalla exige importar DOS PDF distintos: primero COMPLETO y luego DE 4 HOJAS.")
    st.markdown(
        """
        <div class="big-button-note">
        Esta pantalla debe mostrar DOS CAMPOS DE CARGA y DOS BOTONES INDEPENDIENTES:<br>
        1) IMPORTAR INFORME COMPLETO Z-LOGIC &nbsp;&nbsp; 2) IMPORTAR INFORME DE 4 HOJAS
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_complete, col_four = st.columns(2)

    with col_complete:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        st.subheader("1) PDF COMPLETO Z-Logic")
        complete_up = st.file_uploader(
            "CARGAR PDF COMPLETO Z-Logic",
            type=["pdf"],
            accept_multiple_files=False,
            key="uploader_pdf_completo_zlogic_independiente",
        )
        if st.button("1. IMPORTAR INFORME COMPLETO Z-LOGIC", type="primary", disabled=complete_up is None, key="btn_importar_pdf_completo_zlogic"):
            with st.spinner("Importando informe COMPLETO Z-Logic..."):
                b = read_upload_bytes(complete_up)
                st.session_state["parsed_completo"] = parse_complete_pdf(b, getattr(complete_up, "name", "completo.pdf"))
        if "parsed_completo" in st.session_state:
            show_parsed_card("COMPLETO", st.session_state["parsed_completo"])
        st.markdown('</div>', unsafe_allow_html=True)

    with col_four:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        st.subheader("2) PDF Z-Logic DE 4 HOJAS")
        four_up = st.file_uploader(
            "CARGAR PDF Z-Logic DE 4 HOJAS",
            type=["pdf"],
            accept_multiple_files=False,
            key="uploader_pdf_4_hojas_zlogic_independiente",
        )
        if st.button("2. IMPORTAR INFORME DE 4 HOJAS", type="primary", disabled=four_up is None, key="btn_importar_pdf_4_hojas_zlogic"):
            with st.spinner("Importando informe de 4 hojas Z-Logic..."):
                b = read_upload_bytes(four_up)
                st.session_state["parsed_4hojas"] = parse_four_pages_pdf(b, getattr(four_up, "name", "4_hojas.pdf"))
        if "parsed_4hojas" in st.session_state:
            show_parsed_card("4 HOJAS", st.session_state["parsed_4hojas"])
        st.markdown('</div>', unsafe_allow_html=True)

    ready = "parsed_completo" in st.session_state and "parsed_4hojas" in st.session_state
    if not ready:
        st.warning("Para integrar, primero importe ambos informes: COMPLETO y DE 4 HOJAS.")

    if st.button("3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS", type="primary", disabled=not ready, key="btn_integrar_dos_pdf_completo_4hojas"):
        st.session_state["integrated"] = integrate_two_reports(st.session_state["parsed_completo"], st.session_state["parsed_4hojas"])

    if "integrated" not in st.session_state:
        return

    integrated = st.session_state["integrated"]
    demo = integrated["demo"]
    positions = integrated["positions"]

    st.markdown("## Integración final y análisis")
    if integrated.get("conflicts"):
        st.warning("Se detectaron diferencias entre los dos informes. Se muestran para auditoría; puede corregir abajo en el editor.")
        st.dataframe(pd.DataFrame(integrated["conflicts"]), use_container_width=True, hide_index=True)

    st.markdown("### Datos obstétricos")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        demo["paciente"] = st.text_input("Paciente", value=str(demo.get("paciente", "")), key="demo_paciente_final")
        demo["fecha_estudio"] = st.text_input("Fecha", value=str(demo.get("fecha_estudio", "")), key="demo_fecha_final")
    with c2:
        demo["edad"] = st.text_input("Edad", value=str(demo.get("edad", "")), key="demo_edad_final")
        demo["edad_gestacional"] = st.number_input("Edad gestacional (semanas)", min_value=5.0, max_value=42.0, value=float(clean_num(demo.get("edad_gestacional")) or 24.0), step=0.1, key="demo_eg_final")
    with c3:
        demo["diagnostico"] = st.text_input("Diagnóstico Z-Logic", value=str(demo.get("diagnostico", "")), key="demo_diag_final")
        demo["sexo"] = st.text_input("Sexo", value=str(demo.get("sexo", "")), key="demo_sexo_final")
    with c4:
        demo["peso"] = st.text_input("Peso", value=str(demo.get("peso", "")), key="demo_peso_final")
        demo["imc"] = st.text_input("IMC", value=str(demo.get("imc", "")), key="demo_imc_final")

    # Editor por posición
    st.markdown("### Variables complementadas por posición")
    all_vars = sorted({k for vals in positions.values() for k in vals if not k.startswith("_")})
    edit_rows = []
    for var in all_vars:
        edit_rows.append({
            "Variable": var,
            "Acostado": positions.get("Acostado", {}).get(var),
            "Sentado": positions.get("Sentado", {}).get(var),
            "Parado": positions.get("Parado", {}).get(var),
        })
    editor = st.data_editor(pd.DataFrame(edit_rows), use_container_width=True, hide_index=True, key="editor_variables_integradas")
    # Vuelca editor a positions
    new_positions = {"Acostado": {}, "Sentado": {}, "Parado": {}}
    for _, r in editor.iterrows():
        var = str(r.get("Variable"))
        for p in ["Acostado", "Sentado", "Parado"]:
            val = clean_num(r.get(p))
            if val is not None:
                new_positions[p][var] = val
    positions = new_positions

    acostado = positions.get("Acostado", {})
    parado = positions.get("Parado", {})
    hemo = hemo_diagnosis(acostado, demo.get("edad_gestacional"))
    ortho_df, ortho_text = ortho_analysis(acostado, parado)
    ml = j48_ml(acostado)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("IC acostado", fmt(acostado.get("IC"), 2), hemo.get("ic_level"))
    k2.metric("IRV acostado", fmt(acostado.get("IRV"), 0), hemo.get("irv_level"))
    k3.metric("IC parado", fmt(parado.get("IC"), 2))
    k4.metric("IRV parado", fmt(parado.get("IRV"), 0))

    st.markdown("### Diagnóstico hemodinámico")
    st.write(f"**{hemo['profile']}**")
    st.write(f"**ML J48:** {ml['resultado']}")
    st.caption(f"Ruta ML: {ml['ruta']}")

    fig_quad, fig_quad_b = plot_quadrant_units(acostado, parado)
    fig_eg, fig_eg_b = plot_eg(acostado, demo.get("edad_gestacional"))
    st.pyplot(fig_quad, clear_figure=False)
    st.pyplot(fig_eg, clear_figure=False)

    st.markdown("### Análisis ortostático")
    if not ortho_df.empty:
        st.dataframe(ortho_df, use_container_width=True, hide_index=True)
    st.info(ortho_text)

    audit_df = pd.DataFrame(integrated.get("audit", []))
    with st.expander("Auditoría completa de complementación", expanded=False):
        st.dataframe(audit_df, use_container_width=True, hide_index=True)

    pdf_b = make_pdf(demo, positions, hemo, ortho_df, ortho_text, ml, fig_quad_b, fig_eg_b, logo_b, firma_b, medico, institucion)
    xls_b = excel_bytes(demo, positions, integrated.get("audit", []), integrated.get("conflicts", []), ortho_df, hemo, ml)
    base = re.sub(r"[^A-Za-z0-9_]+", "_", f"ICG_PE_{demo.get('paciente','paciente')}_{datetime.now().strftime('%Y%m%d_%H%M')}")
    d1, d2 = st.columns(2)
    d1.download_button("Descargar PDF médico", data=pdf_b, file_name=f"{base}.pdf", mime="application/pdf")
    d2.download_button("Descargar Excel integrado", data=xls_b, file_name=f"{base}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def manual_flow() -> None:
    st.markdown("## Carga manual rápida")
    st.info("Esta pestaña no reemplaza la importación doble. Sirve para validar valores aislados.")
    c1, c2, c3 = st.columns(3)
    with c1:
        ic = st.number_input("IC", value=5.7, step=0.1)
        irv = st.number_input("IRV", value=1095.0, step=10.0)
        eg = st.number_input("Edad gestacional", value=11.0, step=0.1)
    with c2:
        icp = st.number_input("IC parado", value=3.2, step=0.1)
        irvp = st.number_input("IRV parado", value=2097.0, step=10.0)
    with c3:
        cts = st.number_input("CTS/STR", value=0.36, step=0.01)
        iac = st.number_input("IAC/IA", value=304.0, step=1.0)
    a = {"IC": ic, "IRV": irv, "CTS": cts, "IAC": iac}
    p = {"IC": icp, "IRV": irvp}
    hemo = hemo_diagnosis(a, eg)
    ortho_df, ortho_text = ortho_analysis(a, p)
    ml = j48_ml(a)
    st.write(hemo["profile"])
    st.write(ml)
    fig, _ = plot_quadrant_units(a, p)
    st.pyplot(fig)
    st.dataframe(ortho_df)
    st.info(ortho_text)


def main() -> None:
    css()
    st.markdown(
        f"""
        <div class="hero">
          <h1>Predicción y manejo hemodinámico de preeclampsia por ICG Z-Logic</h1>
          <p>Integración obligatoria de dos informes: PDF COMPLETO + PDF DE 4 HOJAS.</p>
          <p class="ver">{APP_VERSION}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    logo_b, firma_b, medico, institucion = sidebar()
    tab1, tab2, tab3 = st.tabs(["PDF Z-Logic: dos informes", "Carga manual", "Base de conocimiento"])
    with tab1:
        dual_pdf_flow(logo_b, firma_b, medico, institucion)
    with tab2:
        manual_flow()
    with tab3:
        st.markdown("### Base de conocimiento interna")
        st.write("- Se integran dos PDF distintos: informe COMPLETO y informe DE 4 HOJAS.")
        st.write("- El completo aporta la tabla basal detallada.")
        st.write("- El de 4 hojas aporta cambios hemodinámicos acostado/sentado/parado y variables adicionales: CFTnr, EA, EES, AC, FE, ISRVS.")
        st.write("- El análisis ortostático esperado es: IC baja e IRV sube en bipedestación.")
        st.write("- El ML J48 utiliza STR/CTS, IA/IAC, EES/ELV y ACI/CA para subclasificación temprana/tardía.")

if __name__ == "__main__":
    main()
