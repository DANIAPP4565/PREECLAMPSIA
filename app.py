# =========================================================
# FLUJO DE IMPORTACIÓN: PDF Z-LOGIC (INTEGRACIÓN COMPLETO + 4 HOJAS)
# =========================================================

def single_pdf_flow(cfg: Dict[str, Any], logo_bytes: Optional[bytes], firma_bytes: Optional[bytes], medico: str, institucion: str) -> None:
    st.markdown(
        """
        <div class='card'>
        <h3>Pestaña PDF Z-Logic: Importación Binómica</h3>
        <p>Cargue de forma independiente el <b>Informe Completo Z-Logic</b> y el <b>Informe de 4 Hojas</b>. 
        El sistema fusionará de forma inteligente las variables de ambos archivos (preservando ortostatismo y acoplamiento ventrículo-arterial).</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Inicialización estricta de estados de sesión para evitar pantallas en blanco
    if "zlogic_raw_completo" not in st.session_state:
        st.session_state.zlogic_raw_completo = None
    if "zlogic_raw_4hojas" not in st.session_state:
        st.session_state.zlogic_raw_4hojas = None
    if "zlogic_merged_data" not in st.session_state:
        st.session_state.zlogic_merged_data = None

    # Disposición visual en dos columnas para los cargadores de archivos
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 1️⃣ Archivo: INFORME COMPLETO")
        file_completo = st.file_uploader("Subir PDF Completo (Original/Tradicional)", type=["pdf"], key="pdf_single_completo")
        
        if file_completo is not None:
            if st.button("1. IMPORTAR INFORME COMPLETO", type="primary", use_container_width=True):
                with st.spinner("Extrayendo texto del informe completo..."):
                    try:
                        # Respetamos tu parser original (retorna: pages, demo, full_text)
                        pages, demo, full_text = parse_zlogic_pdf(file_completo)
                        
                        # Agrupar las variables por su posición hemodinámica
                        grouped: Dict[str, Dict[str, float]] = {}
                        for p in pages:
                            pos_name = p.get("position", "Acostado")
                            if pos_name not in grouped:
                                grouped[pos_name] = {}
                            for val_obj in p.get("values", []):
                                grouped[pos_name][val_obj.variable] = val_obj.value
                        
                        st.session_state.zlogic_raw_completo = {
                            "demo": demo,
                            "grouped": grouped,
                            "full_text": full_text
                        }
                        st.success("¡Informe Completo cargado en memoria!")
                    except Exception as e:
                        st.error(f"Error procesando Informe Completo: {str(e)}")
                        st.stop()

        if st.session_state.zlogic_raw_completo:
            st.caption("✅ Datos del Informe Completo listos para fusión.")

    with col2:
        st.markdown("### 2️⃣ Archivo: INFORME DE 4 HOJAS")
        file_4hojas = st.file_uploader("Subir PDF de 4 Hojas (Variables Adicionales)", type=["pdf"], key="pdf_single_4hojas")
        
        if file_4hojas is not None:
            if st.button("2. IMPORTAR INFORME DE 4 HOJAS", type="primary", use_container_width=True):
                with st.spinner("Extrayendo variables adicionales..."):
                    try:
                        pages, demo, full_text = parse_zlogic_pdf(file_4hojas)
                        
                        grouped: Dict[str, Dict[str, float]] = {}
                        for p in pages:
                            pos_name = p.get("position", "Acostado")
                            if pos_name not in grouped:
                                grouped[pos_name] = {}
                            for val_obj in p.get("values", []):
                                grouped[pos_name][val_obj.variable] = val_obj.value
                        
                        st.session_state.zlogic_raw_4hojas = {
                            "demo": demo,
                            "grouped": grouped,
                            "full_text": full_text
                        }
                        st.success("¡Informe de 4 Hojas cargado en memoria!")
                    except Exception as e:
                        st.error(f"Error procesando Informe de 4 Hojas: {str(e)}")
                        st.stop()

        if st.session_state.zlogic_raw_4hojas:
            st.caption("✅ Datos de 4 Hojas listos para fusión.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón de Fusión e Integración
    if st.button("3. COMPLEMENTAR VARIABLES Y ANALIZAR COMPLETO + 4 HOJAS", type="primary", use_container_width=True):
        if not st.session_state.zlogic_raw_completo and not st.session_state.zlogic_raw_4hojas:
            st.warning("Por favor, importe al menos uno de los dos archivos PDF para proceder con la integración.")
        else:
            with st.spinner("Integrando bases de datos y correlacionando ortostatismo..."):
                # Fusionar datos demográficos prioritarios
                base_demo = {}
                if st.session_state.zlogic_raw_completo:
                    base_demo.update(st.session_state.zlogic_raw_completo["demo"])
                if st.session_state.zlogic_raw_4hojas:
                    base_demo.update(st.session_state.zlogic_raw_4hojas["demo"])

                # Fusión de diccionarios posicionales
                merged_grouped: Dict[str, Dict[str, float]] = {}
                
                # Paso A: Volcar datos del informe completo
                if st.session_state.zlogic_raw_completo:
                    for pos, vars_dict in st.session_state.zlogic_raw_completo["grouped"].items():
                        if pos not in merged_grouped:
                            merged_grouped[pos] = {}
                        merged_grouped[pos].update(vars_dict)

                # Paso B: Integrar variables críticas del de 4 Hojas (CFTnr, EA, EES, AC, Ortostatismo)
                if st.session_state.zlogic_raw_4hojas:
                    for pos, vars_dict in st.session_state.zlogic_raw_4hojas["grouped"].items():
                        if pos not in merged_grouped:
                            merged_grouped[pos] = {}
                        merged_grouped[pos].update(vars_dict)

                # Construir el objeto consolidado final
                st.session_state.zlogic_merged_data = {
                    "demo": base_demo,
                    "grouped": merged_grouped,
                    "full_text_audit": (st.session_state.zlogic_raw_completo["full_text"] if st.session_state.zlogic_raw_completo else "") + 
                                       "\n\n--- COMPLEMENTO INFORME 4 HOJAS ---\n\n" + 
                                       (st.session_state.zlogic_raw_4hojas["full_text"] if st.session_state.zlogic_raw_4hojas else "")
                }
                st.success("¡Integración completada de manera exitosa!")

    # 2. Renderizado condicional: Solo se muestra si el estado consolidado existe
    if st.session_state.zlogic_merged_data:
        data = st.session_state.zlogic_merged_data
        
        with st.expander("Auditoría de integración y textos raw extraídos", expanded=False):
            st.text_area("Pool de texto consolidado", value=data["full_text_audit"][:15000], height=200)
        
        st.markdown("---")
        st.markdown("## 2) Confirmar posición basal y corregir variables")
        
        position_options = list(data["grouped"].keys())
        if not position_options:
            position_options = ["Acostado"]
            
        default_index = 0
        for idx, pos in enumerate(position_options):
            ln = pos.lower()
            if "basal" in ln or "acostado" in ln or "supino" in ln:
                default_index = idx
                break
                
        selected_position = st.selectbox(
            "Posición hemodinámica para análisis de riesgo (Fisiología de Embarazo):", 
            position_options, 
            index=default_index
        )
        
        # Carga del formulario demográfico original de la app
        patient_extracted = data["demo"]
        patient_data = demographic_form(patient_extracted, key_prefix="pdf_flow_integrated")
        
        # Extraer el set de variables cruzadas para la posición seleccionada
        vars_extracted = data["grouped"].get(selected_position, {})
        
        st.markdown("### Variables Hemodinámicas Consolidadas")
        st.caption(f"Visualizando y permitiendo edición fina sobre la posición: **{selected_position}**")
        
        c1, c2, c3, c4 = st.columns(4)
        vars_finales = {}
        
        # Lista exhaustiva de las variables requeridas por tu motor de cálculo matemático
        all_model_vars = ["IC", "IRV", "RVS", "CA", "ITC", "CTE", "CTS", "IH", "IAC", "IV", "CFT", "CFTnr", "EA", "EES", "AC", "FC", "PAS", "PAD", "PAM", "DS", "IDS", "Z0", "VM"]
        
        for i, v_name in enumerate(all_model_vars):
            target_col = [c1, c2, c3, c4][i % 4]
            with target_col:
                v_info = VARIABLE_INFO.get(v_name, {"label": v_name, "unit": ""})
                val_def = clean_num(vars_extracted.get(v_name))
                
                # Fallbacks clínicos por seguridad si la variable no existiese en los PDFs
                if val_def is None:
                    if v_name == "FC": val_def = 75.0
                    elif v_name in ["PAS", "PAD", "PAM"]: 
                        val_def = 110.0 if v_name=="PAS" else (70.0 if v_name=="PAD" else 83.3)
                    else: val_def = 0.0

                vars_finales[v_name] = st.number_input(
                    f"{v_info['label']} ({v_name})",
                    value=float(val_def),
                    step=0.1 if val_def < 10 else 1.0,
                    key=f"pdf_integrated_edit_{v_name}"
                )

        # Mantenimiento estricto de banderas clínicas y paraclínicas
        st.markdown("#### Banderas clínicas y paraclínicas adicionales")
        cx, cy, cz = st.columns(3)
        flags = {}
        with cx:
            flags["proteinuria"] = st.checkbox("Proteinuria significativa o afectación renal", value=False, key="pdf_int_flag_prot")
            flags["severe_symptoms"] = st.checkbox("Síntomas neurológicos o visuales severos", value=False, key="pdf_int_flag_sev")
        with cy:
            flags["platelets_low"] = st.checkbox("Trombocitopenia severa (< 100.000 /µL)", value=False, key="pdf_int_flag_plat")
            flags["creatinine_high"] = st.checkbox("Disfunción renal (Creatinina > 1.1 mg/dL)", value=False, key="pdf_int_flag_creat")
        with cz:
            flags["liver_high"] = st.checkbox("Afectación hepática (Enzimas dobles)", value=False, key="pdf_int_flag_liver")
            flags["low_calcium_intake"] = st.checkbox("Baja ingesta dietética de Calcio conocida", value=False, key="pdf_int_flag_calcium")

        # Normalización matemática de relaciones porcentuales originales de tu app
        for ratio_var in ("CTE", "CTS"):
            if vars_finales[ratio_var] is not None:
                vars_finales[ratio_var] = normalize_ratio_if_percent(ratio_var, vars_finales[ratio_var])

        # Envío directo al motor diagnóstico sin alterar lógica analítica o de ML
        res = compute_all_results(patient_data, vars_finales, flags, cfg)
        
        # Renderización de dashboards dinámicos, descargas de PDF/MD y gráficos nativos
        render_results(res, logo_bytes, firma_bytes, medico, institucion)
