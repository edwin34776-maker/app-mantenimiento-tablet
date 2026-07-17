# ==================== PANTALLA ASIGNACION DE TECNICOS ====================
def pantalla_asignacion():
    df = st.session_state.df_mantenimientos
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Asignacion de Tecnicos</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("asignacion_top")

    st.subheader("Filtros de Asignacion")
    col1, col2 = st.columns(2)
    with col1:
        esp_opciones = ["Todas", "ELE", "MEC"]
        idx_esp = esp_opciones.index(st.session_state.filtro_esp_asig) if st.session_state.filtro_esp_asig in esp_opciones else 0
        filtro_esp = st.selectbox("Especialidad", esp_opciones, index=idx_esp, key="asig_esp")
        st.session_state.filtro_esp_asig = filtro_esp
    with col2:
        maquinas = obtener_maquinas_disponibles(df)
        idx_maq = maquinas.index(st.session_state.filtro_maq_asig) if st.session_state.filtro_maq_asig in maquinas else 0
        filtro_maq = st.selectbox("Maquina", maquinas, index=idx_maq, key="asig_maq")
        st.session_state.filtro_maq_asig = filtro_maq

    df_asig = df.copy()
    if filtro_esp != "Todas" and "Especialidad" in df_asig.columns:
        df_asig = df_asig[df_asig["Especialidad"] == filtro_esp]
    if filtro_maq != "Todas" and "Ubicacion" in df_asig.columns:
        df_asig = df_asig[df_asig["Ubicacion"] == filtro_maq]

    st.subheader(f"Ordenes sin asignar o reasignables ({len(df_asig)})")

    if df_asig.empty:
        st.info("No hay ordenes con los filtros seleccionados.")
        return

    for idx, row in df_asig.iterrows():
        id_ot = str(row.get("ID OT", ""))
        tipo = str(row.get("Especialidad", ""))
        equipo = str(row.get("Equipo", ""))
        ubicacion = str(row.get("Ubicacion", ""))
        estado = str(row.get("Estado", "Pendiente"))
        tecnico_actual = str(row.get("Tecnico_Asignado", ""))
        descripcion = str(row.get("Descripcion de procedimiento", ""))
        desc_corta = descripcion[:40] + "..." if len(descripcion) > 40 else descripcion

        estado_clase = obtener_estado_visual(estado)
        prioridad = str(row.get("Prioridad_Actividad", ""))
        clase_prioridad = obtener_clase_css_prioridad(prioridad)

        with st.container():
            st.markdown(f"""
            <div class="tabla-fila-asig {clase_prioridad}">
                <div class="asig-info">
                    <div class="asig-ot"><strong>OT {id_ot}</strong> | <span class="asig-esp">{tipo}</span></div>
                    <div class="asig-equipo">{equipo} — {ubicacion}</div>
                    <div style="font-size: 10px; color: #666; margin-top: 2px;">{desc_corta}</div>
                </div>
                <div class="asig-estado">
                    <span class="estado-badge {estado_clase}">{estado}</span>
                    <div style="font-size: 10px; color: #888; margin-top: 4px;">{tecnico_actual if tecnico_actual else 'Sin asignar'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            tecnicos = obtener_tecnicos_por_especialidad(tipo)
            tecnicos = ["Sin asignar"] + tecnicos
            try:
                idx_tec = tecnicos.index(tecnico_actual) if tecnico_actual in tecnicos else 0
            except:
                idx_tec = 0

            nuevo_tec = st.selectbox(f"Asignar tecnico", tecnicos, index=idx_tec, key=f"asig_select_{idx}")
            if nuevo_tec == "Sin asignar": nuevo_tec = ""

            if st.button(f"ASIGNAR", use_container_width=True, type="primary", key=f"asig_btn_{idx}"):
                df.at[idx, "Tecnico_Asignado"] = nuevo_tec
                if actualizar_orden_supabase(id_ot, "Tecnico_Asignado", nuevo_tec):
                    st.success(f"Tecnico asignado a OT {id_ot}")
                    st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                    st.rerun()
                else:
                    st.error("Error al guardar asignacion")

# ==================== PANTALLA VERIFICAR (SUPERVISOR) ====================
def pantalla_verificar():
    df = st.session_state.df_mantenimientos
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Verificar Ordenes Ejecutadas</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("verificar_top")

    df_ejecutadas = df[df["Estado"] == "Ejecutado"] if not df.empty and "Estado" in df.columns else pd.DataFrame()

    st.subheader(f"Ordenes ejecutadas pendientes de verificacion ({len(df_ejecutadas)})")

    if df_ejecutadas.empty:
        st.info("No hay ordenes ejecutadas pendientes de verificacion.")
        return

    for idx, row in df_ejecutadas.iterrows():
        id_ot = str(row.get("ID OT", ""))
        tipo = str(row.get("Especialidad", ""))
        equipo = str(row.get("Equipo", ""))
        ubicacion = str(row.get("Ubicacion", ""))
        tecnico = str(row.get("Tecnico_Asignado", "Sin asignar"))
        descripcion = str(row.get("Descripcion de procedimiento", ""))
        desc_corta = descripcion[:40] + "..." if len(descripcion) > 40 else descripcion
        fecha_ejec = str(row.get("Fecha_Ejecucion", "N/A"))
        hora_ini = str(row.get("Hora_Inicio", "N/A"))
        hora_fin = str(row.get("Hora_Fin", "N/A"))

        st.markdown(f"""
        <div class="detail-panel" style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong>OT {id_ot}</strong>
                <span class="estado-badge estado-ejecutado">Ejecutado</span>
            </div>
            <div style="font-size: 12px; color: #666;">
                <strong>{tipo}</strong> | {equipo} — {ubicacion}<br>
                Tecnico: {tecnico}<br>
                Ejecutado: {fecha_ejec} | {hora_ini} - {hora_fin}
            </div>
            <div style="font-size: 11px; color: #333; margin-top: 6px;">{desc_corta}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Ver detalles y comentarios"):
            st.write(f"**Descripcion completa:** {descripcion}")
            st.write(f"**Actividades realizadas:** {row.get('Actividades_Hechas', 'Sin registro')}")
            st.write(f"**Comentarios:** {row.get('Comentarios', 'Sin comentarios')}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"VERIFICAR", use_container_width=True, type="primary", key=f"verif_btn_{idx}"):
                    df.at[idx, "Estado"] = "Verificado"
                    if actualizar_orden_supabase(id_ot, "Estado", "Verificado"):
                        st.success(f"OT {id_ot} verificada correctamente")
                        st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                        st.rerun()
                    else:
                        st.error("Error al verificar")
            with col2:
                if st.button(f"RECHAZAR", use_container_width=True, type="secondary", key=f"rech_btn_{idx}"):
                    df.at[idx, "Estado"] = "Pendiente"
                    if actualizar_orden_supabase(id_ot, "Estado", "Pendiente"):
                        st.warning(f"OT {id_ot} devuelta a Pendiente")
                        st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                        st.rerun()
                    else:
                        st.error("Error al rechazar")

# ==================== FLUJO PRINCIPAL ====================
if st.session_state.pagina == "login":
    pantalla_login()
elif st.session_state.pagina == "home":
    pantalla_home()
elif st.session_state.pagina == "ordenes":
    pantalla_ordenes()
elif st.session_state.pagina == "mis_ordenes":
    pantalla_mis_ordenes()
elif st.session_state.pagina == "ejecutar":
    pantalla_ejecutar()
elif st.session_state.pagina == "detalle_tecnico":
    pantalla_detalle_tecnico()
elif st.session_state.pagina == "detalle":
    pantalla_detalle()
elif st.session_state.pagina == "asignacion":
    pantalla_asignacion()
elif st.session_state.pagina == "verificar":
    pantalla_verificar()
else:
    st.session_state.pagina = "login"
    st.rerun()
