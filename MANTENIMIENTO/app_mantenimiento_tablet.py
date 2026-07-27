import streamlit as st
from supabase import create_client
from datetime import datetime, date

# ───────────────────────────────────────────────
# CONFIGURACIÓN SUPABASE
# ───────────────────────────────────────────────
supabase = create_client(
    st.secrets["SUPABASE_URL"], 
    st.secrets["SUPABASE_KEY"]
)

# ───────────────────────────────────────────────
# FUNCIÓN: Actualizar solo los campos que el técnico modifica
# ───────────────────────────────────────────────
def actualizar_actividad_tecnico(id_fila, datos_actualizar):
    """
    Solo actualiza los campos que le pasas en 'datos_actualizar'.
    El resto de la fila NO se toca.

    Ejemplo:
        actualizar_actividad_tecnico(123, {
            "tecnico_asignado": "LUIS ALVARO RIVERA SANTOS",
            "estado": "En Proceso",
            "hora_inicio": "08:00"
        })
    """
    try:
        # Filtrar campos vacíos para no sobreescribir con NULL
        datos_limpios = {k: v for k, v in datos_actualizar.items() if v is not None and v != ""}

        response = (
            supabase.table("ordenes_trabajo")
            .update(datos_limpios)
            .eq("id", id_fila)
            .execute()
        )
        return True, response
    except Exception as e:
        st.error(f"❌ Error actualizando: {e}")
        return False, None


# ───────────────────────────────────────────────
# FUNCIÓN: Leer actividades filtradas (para asignación de técnicos)
# ───────────────────────────────────────────────
def obtener_actividades_filtradas(filtros=None):
    """
    Obtiene actividades de la tabla ordenes_trabajo con filtros opcionales.

    Args:
        filtros: dict con columnas y valores para filtrar
                 Ej: {"ubicacion": "Planta A", "estado": "Pendiente"}

    Returns:
        Lista de diccionarios con las actividades
    """
    try:
        query = supabase.table("ordenes_trabajo").select("*")

        if filtros:
            for columna, valor in filtros.items():
                if valor:
                    query = query.eq(columna, valor)

        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error obteniendo actividades: {e}")
        return []


# ───────────────────────────────────────────────
# FUNCIÓN: Obtener lista única de técnicos
# ───────────────────────────────────────────────
def obtener_tecnicos():
    """Retorna lista de técnicos disponibles."""
    return [
        "LUIS ALVARO RIVERA SANTOS",
        "WILSON ABDON QUEVEDO PASTOR"
    ]


# ───────────────────────────────────────────────
# PANTALLA: Técnico ejecuta actividad (Tablet)
# ───────────────────────────────────────────────
def pantalla_ejecutar_actividad():
    st.title("🔧 Ejecutar Actividad")

    # Datos que vienen de la BD (solo lectura, NO se modifican)
    id_fila = st.session_state.get("id_actividad_seleccionada")
    actividad = st.session_state.get("datos_actividad", {})

    if not id_fila:
        st.warning("⚠️ No hay actividad seleccionada. Vuelve a la lista.")
        return

    # Mostrar info de solo lectura
    st.info(f"**OT:** {actividad.get('id_ot', 'N/A')}")
    st.info(f"**Procedimiento:** {actividad.get('descripcion_procedimiento', 'N/A')}")
    st.info(f"**Equipo:** {actividad.get('equipo', 'N/A')}")
    st.info(f"**Ubicación:** {actividad.get('ubicacion', 'N/A')}")

    st.divider()

    # Campos EDITABLES por el técnico (solo estos se guardan)
    with st.form("form_ejecucion"):
        tecnico = st.selectbox(
            "👤 Técnico", 
            obtener_tecnicos()
        )

        prioridad = st.selectbox(
            "🔥 Prioridad", 
            ["Alta", "Media", "Baja"]
        )

        col1, col2 = st.columns(2)
        with col1:
            hora_inicio = st.time_input("⏰ Hora Inicio", value=None)
        with col2:
            hora_fin = st.time_input("⏰ Hora Fin", value=None)

        estado = st.selectbox(
            "📋 Estado", 
            ["Pendiente", "En Proceso", "Completada"]
        )

        actividades_hechas = st.text_area("✅ Actividades realizadas")
        comentarios = st.text_area("📝 Comentarios / Observaciones")

        guardar = st.form_submit_button("💾 Guardar Avance", use_container_width=True)

    if guardar:
        # Solo estos campos se envían al UPDATE
        datos_a_guardar = {
            "tecnico_asignado": tecnico,
            "prioridad_actividad": prioridad,
            "hora_inicio": str(hora_inicio) if hora_inicio else None,
            "hora_fin": str(hora_fin) if hora_fin else None,
            "estado": estado,
            "actividades_hechas": actividades_hechas if actividades_hechas else None,
            "comentarios": comentarios if comentarios else None,
            "fecha_ejecucion": str(date.today()),
        }

        exito, respuesta = actualizar_actividad_tecnico(id_fila, datos_a_guardar)

        if exito:
            st.success("✅ Solo se actualizaron los campos del técnico. El resto quedó igual.")
            st.balloons()
        else:
            st.error("❌ No se pudo guardar. Revisa la conexión con Supabase.")


# ───────────────────────────────────────────────
# PANTALLA: Listado de actividades para seleccionar
# ───────────────────────────────────────────────
def pantalla_lista_actividades():
    st.title("📋 Órdenes de Trabajo")

    # Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_ubicacion = st.text_input("Ubicación")
        with col2:
            filtro_equipo = st.text_input("Equipo")
        with col3:
            filtro_estado = st.selectbox(
                "Estado", 
                ["Todos", "Pendiente", "En Proceso", "Completada"]
            )

    # Construir filtros
    filtros = {}
    if filtro_ubicacion:
        filtros["ubicacion"] = filtro_ubicacion
    if filtro_equipo:
        filtros["equipo"] = filtro_equipo
    if filtro_estado != "Todos":
        filtros["estado"] = filtro_estado

    # Obtener datos
    actividades = obtener_actividades_filtradas(filtros)

    if not actividades:
        st.info("📭 No hay actividades con esos filtros.")
        return

    st.write(f"📊 {len(actividades)} actividades encontradas")

    for act in actividades:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**OT {act.get('id_ot', 'N/A')}** - {act.get('descripcion_procedimiento', 'Sin descripción')}")
                st.caption(f"📍 {act.get('ubicacion', 'N/A')} | 🔧 {act.get('equipo', 'N/A')}")

            with col2:
                estado = act.get('estado', 'Pendiente')
                color = {"Completada": "green", "En Proceso": "orange", "Pendiente": "gray"}.get(estado, "gray")
                st.markdown(f":{color}[**{estado}**]")

            with col3:
                if st.button("▶️ Ejecutar", key=f"btn_{act.get('id')}"):
                    st.session_state["id_actividad_seleccionada"] = act.get('id')
                    st.session_state["datos_actividad"] = act
                    st.rerun()


# ───────────────────────────────────────────────
# MAIN / NAVEGACIÓN
# ───────────────────────────────────────────────
if __name__ == "__main__":
    # Navegación simple
    pagina = st.sidebar.radio(
        "Navegación", 
        ["📋 Lista de Actividades", "🔧 Ejecutar Actividad"]
    )

    if pagina == "📋 Lista de Actividades":
        pantalla_lista_actividades()
    elif pagina == "🔧 Ejecutar Actividad":
        pantalla_ejecutar_actividad()
