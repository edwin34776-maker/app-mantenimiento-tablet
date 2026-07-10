
import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuracion de la pagina - MODO TABLET
st.set_page_config(
    page_title="App Tablet Mtto Preventivo",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== ESTILOS CSS - DISENO TABLET ====================
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f5;
    }

    .tablet-header {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 0 0 16px 16px;
        text-align: center;
        font-size: 20px;
        font-weight: 700;
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 4px 15px rgba(26,35,158,0.3);
        position: sticky;
        top: 0;
        z-index: 100;
    }

    .home-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
        padding: 20px;
    }

    .big-counter {
        font-size: 80px;
        font-weight: 900;
        color: #1a237e;
        line-height: 1;
        margin: 20px 0;
    }

    .counter-label {
        font-size: 18px;
        color: #666;
        margin-bottom: 30px;
    }

    .estado-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        text-align: center;
    }

    .estado-ejecutado { background-color: #d4edda; color: #155724; }
    .estado-pendiente { background-color: #fff3cd; color: #856404; }
    .estado-verificado { background-color: #cce5ff; color: #004085; }
    .estado-cerrada { background-color: #d1ecf1; color: #0c5460; }

    .progress-bar-container {
        display: flex;
        gap: 15px;
        justify-content: center;
        margin: 20px 0;
        padding: 15px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .progress-item {
        text-align: center;
    }

    .progress-value {
        font-size: 24px;
        font-weight: 800;
    }

    .progress-label {
        font-size: 12px;
        color: #666;
    }

    .detail-panel {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-top: 10px;
    }

    .equipo-info {
        background: #f5f5f5;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        font-size: 14px;
    }

    .equipo-info strong {
        color: #1a237e;
    }

    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }

    .prioridad-critico {
        border-left: 5px solid #dc3545 !important;
        background: linear-gradient(90deg, #fff5f5 0%, #ffffff 100%) !important;
    }
    .prioridad-secundario {
        border-left: 5px solid #ffc107 !important;
        background: linear-gradient(90deg, #fffbea 0%, #ffffff 100%) !important;
    }
    .prioridad-estandar {
        border-left: 5px solid #28a745 !important;
        background: linear-gradient(90deg, #f0fff4 0%, #ffffff 100%) !important;
    }

    .leyenda-prioridad {
        display: flex;
        gap: 20px;
        justify-content: center;
        margin: 15px 0;
        padding: 12px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        flex-wrap: wrap;
    }

    .leyenda-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
    }

    .leyenda-dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
    }

    .actividad-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.2s;
    }

    .actividad-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        transform: translateY(-1px);
    }

    .actividad-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .actividad-titulo {
        font-size: 15px;
        font-weight: 700;
        color: #1f2937;
        flex: 1;
    }

    .actividad-prioridad-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .badge-critico {
        background: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
    }

    .badge-secundario {
        background: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }

    .badge-estandar {
        background: #d1fae5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }

    .actividad-descripcion {
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 12px;
        line-height: 1.5;
    }

    .actividad-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 10px;
        border-top: 1px solid #f3f4f6;
    }

    .actividad-meta {
        display: flex;
        gap: 12px;
        font-size: 12px;
        color: #9ca3af;
    }

    @media (max-width: 768px) {
        .actividad-header { flex-direction: column; align-items: flex-start; gap: 8px; }
        .leyenda-prioridad { gap: 10px; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== BASE DE DATOS DE TECNICOS ====================

TECNICOS_ELE = [
    "RIVERA SANTOS LUIS ALVARO",
    "NESTOR LEONARDO CORTES TORRES",
    "JAVIER FELIPE ROZO CALDERON",
    "JHON FREDY BERNAL AVILA",
    "YUPER YAIL CASTILLO",
    "ERIK SANTIAGO MARTINEZ HERRERA",
    "QUECANO ANGARITA CARLOS",
    "PULIDO RIOS JAHIR",
    "GARCIA CASAS JEFFERSSON DAVID",
    "CASTANEDA ORTIZ EDISON ORACIO",
    "DIAZ SEGURA DANIEL STEVEN",
    "FRANCO SIERRA JOSE ALEJANDRO",
    "MOJICA GARCES JEAN CARLOS",
    "CAROLOINA RINCON",
    "PINILLA ARIAS JHONATAN FERNANDO",
    "JUAN DAVID CHACON VELANDIA"
]

TECNICOS_MEC = [
    "WILSON ABDON QUEVEDO PASTOR",
    "LUIS FERNANDO DELGADO CARMONA",
    "SAENZ SAENZ CARLOS EFREN",
    "PABLO ENRRIQUE TORRES BARON",
    "FELIPE LATORRE DIAZ",
    "MOLINA GONZALEZ MICHAEL ANDRES",
    "MURILLO MURILLO WILLIAM OBER",
    "MOLANO ALFONSO LUIS",
    "MARTINEZ TORRES FREDY ALEXANDER",
    "VARGAS VARGAS JHON ALEJANDER",
    "MERINO GIL JOSE MANUEL",
    "DILAN MEDINA",
    "RODRIGUEZ CAMACHO LUIS ALVEIRO",
    "MENDIVIELSO CANTOR JUAN CARLOS",
    "ARIAS  PERDOMO JUAN ESTEBAN",
    "VELASQUEZ OSPINA CRISTIAN JAIR"
]

# ==================== FUNCIONES AUXILIARES ====================

@st.cache_data
def cargar_excel_mantenimiento():
    try:
        df = pd.read_excel("MANTENIMIENTO/Formato de mantenimiento preventivo.xlsx", sheet_name="Inicial")
        # Eliminar fila de encabezados duplicados si existe
        if "UN" in df.columns:
            df = df[df["UN"] != "UN"].reset_index(drop=True)

        # Normalizar nombres de columnas: quitar espacios extra
        df.columns = df.columns.str.strip()

        # Mapeo de columnas con tildes a nombres sin tildes para facilitar el codigo
        columnas_mapeo = {
            "Ubicacion": "Ubicacion",
            "Descripcion de procedimiento": "Descripcion de procedimiento",
            "Especialidad": "Especialidad",
        }
        for original, nuevo in columnas_mapeo.items():
            if original in df.columns and nuevo not in df.columns:
                df = df.rename(columns={original: nuevo})

        columnas_default = {
            "Estado": "Pendiente",
            "Comentarios": "",
            "Tecnico_Asignado": "",
            "Actividades_Hechas": "",
            "Fecha_Ejecucion": "",
            "Hora_Inicio": "",
            "Hora_Fin": "",
            "Prioridad_Actividad": ""
        }
        for col, default in columnas_default.items():
            if col not in df.columns:
                df[col] = default
        return df
    except FileNotFoundError:
        st.error("No se encontro el archivo: MANTENIMIENTO/Formato de mantenimiento preventivo.xlsx")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar el archivo de mantenimiento: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_excel_tecnicos():
    try:
        df = pd.read_excel("MANTENIMIENTO/tecnico.xlsx", sheet_name="query")
        df = df[df["ACTIVIDAD"] != "ACTIVIDAD"].reset_index(drop=True)
        df["TECNICOS"] = df["TECNICOS"].str.strip()
        df["ESPE"] = df["ESPE"].str.strip()
        return df
    except FileNotFoundError:
        st.error("No se encontro el archivo: MANTENIMIENTO/tecnico.xlsx")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar el archivo de tecnicos: {e}")
        return pd.DataFrame()

def obtener_tecnicos_por_nodo(nodo, especialidad):
    df_tec = st.session_state.df_tecnicos
    if df_tec.empty:
        return []
    tecnicos = df_tec[
        (df_tec["ACTIVIDAD"] == nodo) &
        (df_tec["ESPE"] == especialidad) &
        (df_tec["TECNICOS"].notna()) &
        (df_tec["TECNICOS"] != "")
    ]["TECNICOS"].unique().tolist()
    return tecnicos

def obtener_tecnicos_por_especialidad(especialidad):
    if especialidad == "ELE":
        return TECNICOS_ELE
    elif especialidad == "MEC":
        return TECNICOS_MEC
    return TECNICOS_ELE + TECNICOS_MEC

def limpiar_nombre_equipo(nombre):
    nombre = str(nombre).strip().upper()
    prefijos = ["MOTOR ", "REDUCTOR ", "MOTOREDUCTOR ", "SERVOMOTOR ", "CAJA DE ",
                "TABLERO ", "BORNEA ", "AIRE ACONDICIONADO ", "AIRE ACOND  ",
                "SISTEMA DE ", "ESTACION DE ", "SISTEMA "]
    for prefijo in prefijos:
        if nombre.startswith(prefijo):
            return nombre.replace(prefijo, "")
    return nombre

def calcular_progreso(df):
    total = len(df)
    if total == 0:
        return 0, 0, 0
    ejecutado = len(df[df["Estado"] == "Ejecutado"])
    verificado = len(df[df["Estado"] == "Verificado"])
    cerrada = len(df[df["Estado"] == "Cerrada"])
    pct_ejec = round((ejecutado / total) * 100, 1)
    pct_verif = round((verificado / total) * 100, 1)
    pct_pdte = round(100 - pct_ejec - pct_verif, 1)
    return pct_ejec, pct_pdte, pct_verif

def obtener_estado_visual(estado):
    estados = {
        "Ejecutado": "estado-ejecutado",
        "Verificado": "estado-verificado",
        "Cerrada": "estado-cerrada",
        "Pendiente": "estado-pendiente"
    }
    return estados.get(estado, "estado-pendiente")

def obtener_color_prioridad(prioridad):
    colores = {
        "Rojo": {"label": "CRITICO", "desc": "Si o si se debe realizar"},
        "Amarillo": {"label": "SECUNDARIO", "desc": "Realizar despues de las obligatorias"},
        "Verde": {"label": "ESTANDAR", "desc": "Actividad simple, poco requisito"},
        "": {"label": "SIN CLASIFICAR", "desc": "No definida"}
    }
    return colores.get(prioridad, colores[""])

def obtener_clase_css_prioridad(prioridad):
    clases = {
        "Rojo": "prioridad-critico",
        "Amarillo": "prioridad-secundario",
        "Verde": "prioridad-estandar",
        "": ""
    }
    return clases.get(prioridad, "")

def boton_volver_inicio(key_suffix=""):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("VOLVER AL INICIO", use_container_width=True, type="secondary", key=f"volver_inicio_{key_suffix}"):
            st.session_state.pagina = "home"
            st.session_state.orden_seleccionada = None
            st.session_state.busqueda = ""
            st.rerun()

def obtener_maquinas_disponibles(df):
    """Obtiene la lista de maquinas/ubicaciones disponibles de forma segura."""
    if df.empty or "Ubicacion" not in df.columns:
        return ["Todas"]
    try:
        maquinas = df["Ubicacion"].dropna().unique().tolist()
        maquinas = [m for m in maquinas if str(m).strip()]
        return ["Todas"] + sorted(maquinas)
    except Exception:
        return ["Todas"]

# ==================== INICIALIZAR ESTADO ====================

if "pagina" not in st.session_state:
    st.session_state.pagina = "home"
if "orden_seleccionada" not in st.session_state:
    st.session_state.orden_seleccionada = None
if "df_mantenimientos" not in st.session_state:
    st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
if "df_tecnicos" not in st.session_state:
    st.session_state.df_tecnicos = cargar_excel_tecnicos()
if "filtro_especialidad" not in st.session_state:
    st.session_state.filtro_especialidad = "Todas"
if "filtro_maquina" not in st.session_state:
    st.session_state.filtro_maquina = "Todas"
if "filtro_esp_asig" not in st.session_state:
    st.session_state.filtro_esp_asig = "Todas"
if "filtro_maq_asig" not in st.session_state:
    st.session_state.filtro_maq_asig = "Todas"
if "filtro_estado_asig" not in st.session_state:
    st.session_state.filtro_estado_asig = "Todos"
if "busqueda" not in st.session_state:
    st.session_state.busqueda = ""
if "actividades_check" not in st.session_state:
    st.session_state.actividades_check = {}
if "prioridades_actividades" not in st.session_state:
    st.session_state.prioridades_actividades = {}

# ==================== PANTALLA DE INICIO (HOME) ====================

def pantalla_home():
    df = st.session_state.df_mantenimientos
    st.markdown('<div class="tablet-header">App Tablet Mtto Preventivo</div>', unsafe_allow_html=True)
    total_ordenes = len(df)
    st.markdown(f"""
    <div class="home-screen">
        <div class="counter-label">ORDENES PREVENTIVAS</div>
        <div class="big-counter">{total_ordenes}</div>
        <div class="counter-label">Total de ordenes activas</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; margin-bottom: 10px; font-weight: 600; color: #666;'>Filtrar por Especialidad</div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1,1,1,1])
    with col1:
        if st.button("TODAS", use_container_width=True,
                    type="primary" if st.session_state.filtro_especialidad == "Todas" else "secondary"):
            st.session_state.filtro_especialidad = "Todas"
            st.rerun()
    with col2:
        if st.button("ELE", use_container_width=True,
                    type="primary" if st.session_state.filtro_especialidad == "ELE" else "secondary"):
            st.session_state.filtro_especialidad = "ELE"
            st.rerun()
    with col3:
        if st.button("MEC", use_container_width=True,
                    type="primary" if st.session_state.filtro_especialidad == "MEC" else "secondary"):
            st.session_state.filtro_especialidad = "MEC"
            st.rerun()
    with col4:
        if st.button("LIMPIAR", use_container_width=True):
            st.session_state.filtro_especialidad = "Todas"
            st.session_state.busqueda = ""
            st.rerun()

    # USAR FUNCION SEGURA PARA OBTENER MAQUINAS
    maquinas = obtener_maquinas_disponibles(df)

    # Asegurar que el valor seleccionado este en la lista
    index_sel = 0
    if st.session_state.filtro_maquina in maquinas:
        index_sel = maquinas.index(st.session_state.filtro_maquina)

    maquina_sel = st.selectbox("Maquina / Ubicacion", maquinas, index=index_sel)
    st.session_state.filtro_maquina = maquina_sel

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("VER ORDENES PREVENTIVAS", use_container_width=True, type="primary"):
            st.session_state.pagina = "ordenes"
            st.rerun()
    with col_btn2:
        if st.button("ASIGNACION DE TECNICOS", use_container_width=True, type="primary"):
            st.session_state.pagina = "asignacion"
            st.rerun()

    if not df.empty and "Especialidad" in df.columns:
        st.divider()
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("ELE", len(df[df["Especialidad"] == "ELE"]))
        with col_b:
            st.metric("MEC", len(df[df["Especialidad"] == "MEC"]))
        with col_c:
            st.metric("Cerradas", len(df[df["Estado"].isin(["Cerrada", "Verificado"])]))

# ==================== PANTALLA DE ORDENES (LISTA) ====================

def pantalla_ordenes():
    df = st.session_state.df_mantenimientos
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Ordenes Preventivas</span>
        <span style="font-size: 14px; opacity: 0.8;">{st.session_state.filtro_especialidad}</span>
    </div>
    """, unsafe_allow_html=True)

    boton_volver_inicio("ordenes_top")

    busqueda = st.text_input("Buscar ID OT, equipo o descripcion...",
                            value=st.session_state.busqueda,
                            placeholder="Escribe para buscar...")
    st.session_state.busqueda = busqueda

    pct_ejec, pct_pdte, pct_verif = calcular_progreso(df)
    st.markdown(f"""
    <div class="progress-bar-container">
        <div class="progress-item"><div class="progress-value" style="color:#28a745">{pct_ejec}%</div><div class="progress-label">Ejecutado</div></div>
        <div class="progress-item"><div class="progress-value" style="color:#dc3545">{pct_pdte}%</div><div class="progress-label">Pendiente</div></div>
        <div class="progress-item"><div class="progress-value" style="color:#007bff">{pct_verif}%</div><div class="progress-label">Verificado</div></div>
    </div>
    """, unsafe_allow_html=True)

    df_filtrado = df.copy()
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Especialidad"] == st.session_state.filtro_especialidad]
    if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Ubicacion"] == st.session_state.filtro_maquina]
    if busqueda:
        busqueda_lower = busqueda.lower()
        mask = pd.Series([False] * len(df_filtrado), index=df_filtrado.index)
        if "Equipo" in df_filtrado.columns:
            mask |= df_filtrado["Equipo"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "Ubicacion" in df_filtrado.columns:
            mask |= df_filtrado["Ubicacion"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "ID OT" in df_filtrado.columns:
            mask |= df_filtrado["ID OT"].astype(str).str.contains(busqueda_lower, na=False)
        if "Descripcion de procedimiento" in df_filtrado.columns:
            mask |= df_filtrado["Descripcion de procedimiento"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        df_filtrado = df_filtrado[mask]

    st.subheader(f"Ordenes ({len(df_filtrado)})")
    for idx, row in df_filtrado.iterrows():
        id_ot = str(row.get("ID OT", ""))
        tipo = str(row.get("Especialidad", ""))
        descripcion = str(row.get("Descripcion de procedimiento", ""))[:50] + "..." if len(str(row.get("Descripcion de procedimiento", ""))) > 50 else str(row.get("Descripcion de procedimiento", ""))
        estado = str(row.get("Estado", "Pendiente"))
        tecnico = str(row.get("Tecnico_Asignado", ""))[:15] + "..." if len(str(row.get("Tecnico_Asignado", ""))) > 15 else str(row.get("Tecnico_Asignado", ""))
        if not tecnico:
            tecnico = "Sin asignar"
        estado_clase = obtener_estado_visual(estado)

        cols = st.columns([1, 1, 4, 1, 1])
        with cols[0]:
            st.write(f"**{id_ot}**")
        with cols[1]:
            st.write(f"{tipo}")
     
