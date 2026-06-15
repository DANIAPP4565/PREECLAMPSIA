# =========================================================
# FLUJO DE IMPORTACIÓN: PDF Z-LOGIC (DOS INFORMES INTEGRADOS)
# =========================================================

def single_pdf_flow(cfg: Dict[str, Any], logo_bytes: Optional[bytes], firma_bytes: Optional[bytes], medico: str, institucion: str) -> None:
    st.markdown(
        """
        <div class='card'>
        <h3>Pestaña PDF Z-Logic: Dos Informes</h3>
        <p>Cargue de manera independiente el <b>Informe Completo Z-Logic</b> y el <b>Informe de 4 Hojas</b>. 
        El sistema integrará las variables de ambos informes para consolidar la base de análisis (incluyendo ortostatismo y acoplamiento ventrículo-arterial).</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Inicializar llaves en session_state si no existen
    if "zlogic_raw_completo" not in st.session_state:
        st.session_state.zlogic_raw_completo = None
    if "zlogic_raw_4hojas" not in st.session_state:
        st.session_state.zlogic_raw_4hojas = None
    if "zlogic_merged_data" not in st.session_state:
        st.session_state.zlogic_merged_data = None

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 1️⃣ Informe COMPLETO Z-Logic")
        file_completo = st.file_uploader("Subir PDF Completo Z-Logic", type=["pdf"], key="pdf_uploader_completo")
        
        if file_completo is not None:
            if st.button("1. IMPORTAR INFORME COMPLETO Z-LOGIC", type="primary", use_container_width=True):
                with st.spinner("Procesando Informe Completo..."):
                    try:
                        pages, demo, full_text = parse_zlogic_pdf(file_completo)
                        # Agrupar variables por posición
                        grouped: Dict[str, Dict[str, float]] = {}
                        for p in pages:
                            pos_name = p.get("position", "Desconocida")
                            if pos_name not in grouped:
                                grouped[pos_name] = {}
                            for val_obj in p.get("values", []):
                                grouped[pos_name][val_obj.variable] = val_obj.value
                        
                        st.session_state.zlogic_raw_completo = {
                            "demo": demo,
                            "grouped": grouped,
                            "full_text": full_text
                        }
                        st.success("¡Informe Completo importado con éxito en memoria!")
                    except Exception as e:
                        st.error(f"Error al parsear el informe completo: {str(e)}")

        if st.session_state.zlogic_raw_completo:
            st.info("✅ Datos del Informe Completo listos para integración.")

    with col2:
        st.markdown("### 2️⃣ Informe de 4 HOJAS Z-Logic")
        file_4hojas = st.file_uploader("Subir PDF de 4 Hojas Z-Logic", type=["pdf"], key="pdf_uploader_4hojas")
        
        if file_4hojas is not None:
            if st.button("2. IMPORTAR INFORME DE 4 HOJAS", type="primary", use_container_width=True):
                with st.spinner("Procesando Informe de 4 Hojas..."):
                    try:
                        pages, demo, full_text = parse_zlogic_pdf(file_4hojas)
                        # Agrupar variables por posición (Acostado, Sentado, Parado)
                        grouped: Dict[str, Dict[str, float]] = {}
                        for p in pages:
                            pos_name = p.get("position", "Desconocida")
                            if pos_name not in grouped:
                                grouped[pos_name] = {}
                            for val_obj in p.get("values", []):
                                grouped[pos_name][val_obj.variable] = val_obj.value
                        
                        st.session_state.zlogic_raw_4hojas = {
                            "demo": demo,
                            "grouped": grouped,
                            "full_text": full_text
                        }
                        st.success("¡Informe de 4 Hojas importado con éxito en memoria!")
                    except Exception as e:
                        st.error(f"Error al parsear el informe de 4 hojas: {str(e)}")

        if st.session_state.zlogic_raw_4hojas:
            st.info("✅ Datos del Informe de 4 Hojas listos para integración.")

    st.markdown("---")
    
    # Botón 3: Integración final de variables
    if st.button("3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS", type="primary", use_container_width=True):
        if not st.session_state.zlogic_raw_completo and not st.session_state.zlogic_raw_4hojas:
            st.error("Debe importar al menos uno de los archivos PDF para realizar el análisis consolidado.")
        else:
            with st.spinner("Fusionando bases de datos de PDFs..."):
                # Priorizar datos demográficos del informe de 4 hojas si están ambos
                base_demo = {}
                if st.session_state.zlogic_raw_completo:
                    base_demo.update(st.session_state.zlogic_raw_completo["demo"])
                if st.session_state.zlogic_raw_4hojas:
                    base_demo.update(st.session_state.zlogic_raw_4hojas["demo"])

                # Fusión inteligente de grupos posicionales y variables hemodinámicas
                merged_grouped: Dict[str, Dict[str, float]] = {}
                
                # 1. Cargar datos del completo
                if st.session_state.zlogic_raw_completo:
                    for pos, vars_dict in st.session_state.zlogic_raw_completo["grouped"].items():
                        if pos not in merged_grouped:
                            merged_grouped[pos] = {}
                        merged_grouped[pos].update(vars_dict)

                # 2. Sobrescribir/Complementar con el de 4 hojas (Aporta Ortostatismo y variables avanzadas)
                if st.session_state.zlogic_raw_4hojas:
                    for pos, vars_dict in st.session_state.zlogic_raw_4hojas["grouped"].items():
                        if pos not in merged_grouped:
                            merged_grouped[pos] = {}
                        # Combina/sobreescribe aportando CFTnr, EA, EES, AC, etc.
                        merged_grouped[pos].update(vars_dict)

                st.session_state.zlogic_merged_data = {
                    "demo": base_demo,
                    "grouped": merged_grouped,
                    "full_text_audit": (st.session_state.zlogic_raw_completo["full_text"] if st.session_state.zlogic_raw_completo else "") + 
                                       "\n\n--- DIVISION 4 HOJAS ---\n\n" + 
                                       (st.session_state.zlogic_raw_4hojas["full_text"] if st.session_state.zlogic_raw_4hojas else "")
                }
                st.success("¡Integración completada correctamente! Se unificaron los perfiles hemodinámicos.")

    # Renderizar resultados si existe la consolidación de datos
    if st.session_state.zlogic_merged_data:
        data = st.session_state.zlogic_merged_data
        
        with st.expander("Auditoría de integración y textos extraídos", expanded=False):
            st.text_area("Pool de texto consolidado", value=data["full_text_audit"][:15000], height=250)
        
        st.markdown("## 2) Confirmar posición basal y corregir variables")
        position_options = list(data["grouped"].keys())
        
        default_index = 0
        for idx, pos in enumerate(position_options):
            ln = pos.lower()
            if "basal" in ln or "acostado" in ln or "supino" in ln:
                default_index = idx
                break
                
        selected_position = st.selectbox("Posición hemodinámica para análisis de riesgo (Fisiología de Embarazo)", position_options, index=default_index)
        
        # Carga del formulario demográfico con defaults extraídos
        patient_extracted = data["demo"]
        patient_data = demographic_form(patient_extracted, key_prefix="pdf_flow")
        
        # Extraer variables de la posición seleccionada
        vars_extracted = data["grouped"].get(selected_position, {})
        
        st.markdown("### Variables de la posición seleccionada")
        st.caption(f"Visualizando y editando datos medidos en posición: **{selected_position}**")
        
        # Mostrar grilla editable con las variables del modelo
        c1, c2, c3, c4 = st.columns(4)
        vars_finales = {}
        
        all_model_vars = ["IC", "IRV", "RVS", "CA", "ITC", "CTE", "CTS", "IH", "IAC", "IV", "CFT", "CFTnr", "EA", "EES", "AC", "FC", "PAS", "PAD", "PAM", "DS", "IDS", "Z0", "VM"]
        
        for i, v_name in enumerate(all_model_vars):
            # Repartir dinámicamente en columnas
            target_col = [c1, c2, c3, c4][i % 4]
            with target_col:
                v_info = VARIABLE_INFO.get(v_name, {"label": v_name, "unit": ""})
                val_def = clean_num(vars_extracted.get(v_name))
                
                # Valores de fallback razonables si la variable está ausente en el PDF
                if val_def is None:
                    if v_name == "FC": val_def = 75.0
                    elif v_name in ["PAS", "PAD", "PAM"]: val_def = 110.0 if v_name=="PAS" else (70.0 if v_name=="PAD" else 83.3)
                    else: val_def = 0.0

                vars_finales[v_name] = st.number_input(
                    f"{v_info['label']} ({v_name} - {v_info['unit']})",
                    value=float(val_def),
                    step=0.1 if val_def < 10 else 1.0,
                    key=f"pdf_edit_{v_name}"
                )

        # Inputs de banderas de laboratorio y criterios de severidad clínicos
        st.markdown("#### Banderas clínicas y paraclínicas adicionales")
        cx, cy, cz = st.columns(3)
        flags = {}
        with cx:
            flags["proteinuria"] = st.checkbox("Proteinuria significativa o criterio alternativo de afectación renal", value=False, key="pdf_flag_prot")
            flags["severe_symptoms"] = st.checkbox("Síntomas neurológicos o visuales severos (Eclampsia/Imminente)", value=False, key="pdf_flag_sev")
        with cy:
            flags["platelets_low"] = st.checkbox("Trombocitopenia severa (< 100.000 /µL)", value=False, key="pdf_flag_plat")
            flags["creatinine_high"] = st.checkbox("Disfunción renal (Creatinina > 1.1 mg/dL)", value=False, key="pdf_flag_creat")
        with cz:
            flags["liver_high"] = st.checkbox("Afectación hepática (Enzimas dobles del valor normal)", value=False, key="pdf_flag_liver")
            flags["low_calcium_intake"] = st.checkbox("Baja ingesta dietética de Calcio conocida", value=False, key="pdf_flag_calcium")

        # Mantener el procesamiento core intacto de la app original
        for ratio_var in ("CTE", "CTS"):
            if vars_finales[ratio_var] is not None:
                vars_finales[ratio_var] = normalize_ratio_if_percent(ratio_var, vars_finales[ratio_var])

        # Ejecución del motor diagnóstico sin perder funcionalidades
        res = compute_all_results(patient_data, vars_finales, flags, cfg)
        
        # Render completo del dashboard, PDF, MD y gráficos nativos
        render_results(res, logo_bytes, firma_bytes, medico, institucion)
