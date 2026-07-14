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

# ==================== ESTILOS CSS - DISENO TABLET COMPACTO ====================
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f5;
        max-width: 100vw;
        overflow-x: hidden;
    }
    .main .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 100% !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.3rem !important;
    }
    .tablet-header {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 0 0 16px 16px;
        text-align: center;
        font-size: 18px;
        font-weight: 700;
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 4px 15px rgba(26,35,158,0.3);
        position: sticky;
        top: 0;
        z-index: 100;
        width: 100%;
        box-sizing: border-box;
        word-wrap: break-word;
    }
    .home-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        min-height: auto;
        text-align: center;
        padding: 10px;
        width: 100%;
        box-sizing: border-box;
    }
    .big-counter {
        font-size: 60px;
        font-weight: 900;
        color: #1a237e;
        line-height: 1;
        margin: 10px 0;
        word-wrap: break-word;
    }
    .counter-label {
        font-size: 18px;
        color: #666;
        margin-bottom: 30px;
    }
    .estado-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        text-align: center;
        white-space: nowrap;
    }
    .estado-ejecutado { background-color: #d4edda; color: #155724; }
    .estado-pendiente { background-color: #fff3cd; color: #856404; }
    .estado-verificado { background-color: #cce5ff; color: #004085; }
    .estado-cerrada { background-color: #d1ecf1; color: #0c5460; }
    .progress-bar-container {
        display: flex;
        gap: 15px;
        justify-content: center;
        margin: 15px 0;
        padding: 12px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .progress-item { text-align: center; }
    .progress-value { font-size: 22px; font-weight: 800; }
    .progress-label { font-size: 11px; color: #666; }
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
    .equipo-info strong { color: #1a237e; }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px !important;
        padding: 4px 12px !important;
    }
    .prioridad-critico {
        border-left: 4px solid #dc3545 !important;
        background: linear-gradient(90deg, #fff5f5 0%, #ffffff 100%) !important;
    }
    .prioridad-secundario {
        border-left: 4px solid #ffc107 !important;
        background: linear-gradient(90deg, #fffbea 0%, #ffffff 100%) !important;
    }
    .prioridad-estandar {
        border-left: 4px solid #28a745 !important;
        background: linear-gradient(90deg, #f0fff4 0%, #ffffff 100%) !important;
    }
    .tabla-header {
        display: grid;
        grid-template-columns: 70px 45px 1fr 90px 110px;
        gap: 6px;
        padding: 8px 10px;
        background: #f8f9fa;
        border-bottom: 2px solid #dee2e6;
        font-weight: 700;
        font-size: 10px;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        align-items: center;
        margin-bottom: 6px;
    }
    .tabla-fila {
        display: grid;
        grid-template-columns: 70px 45px 1fr 90px 110px;
        gap: 6px;
        padding: 8px 10px;
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        align-items: center;
        font-size: 12px;
        margin-bottom: 6px;
        transition: all 0.2s;
    }
    .tabla-fila:hover {
        background: #f8f9fa;
        border-color: #adb5bd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .tabla-fila .col-id { font-family: monospace; font-size: 11px; color: #495057; }
    .tabla-fila .col-esp { font-weight: 600; font-size: 11px; color: #1a237e; }
    .tabla-fila .col-desc { font-size: 11px; color: #212529; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tabla-fila .col-estado { text-align: center; }
    .tabla-fila .col-tec { font-size: 10px; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tabla-fila-asig {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 10px;
        padding: 8px 10px;
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 6px;
        align-items: center;
        margin-bottom: 4px;
    }
    .asig-info { min-width: 0; overflow: hidden; }
    .asig-ot { font-size: 12px; color: #212529; margin-bottom: 2px; }
    .asig-esp { color: #1a237e; font-weight: 600; font-size: 11px; }
    .asig-equipo { font-size: 10px; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .asig-estado { text-align: right; flex-shrink: 0; }
    .perfil-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.2s, box-shadow 0.2s;
        cursor: pointer;
        border: 3px solid transparent;
    }
    .perfil-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }
    .perfil-admin { border-color: #dc3545; }
    .perfil-tecnico { border-color: #28a745; }
    .perfil-supervisor { border-color: #007bff; }
    .perfil-icon { font-size: 48px; margin-bottom: 12px; }
    .perfil-titulo { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
    .perfil-desc { font-size: 12px; color: #666; }
    @media (max-width: 768px) {
        .big-counter { font-size: 48px; }
        .tablet-header { font-size: 16px; padding: 10px 12px; }
        .home-screen { padding: 5px; }
        .tabla-header { font-size: 9px; grid-template-columns: 60px 40px 1fr 80px 90px; padding: 6px 8px; }
        .tabla-fila { font-size: 11px; grid-template-columns: 60px 40px 1fr 80px 90px; padding: 6px 8px; }
    }
    @media (max-width: 480px) {
        .tabla-header { display: none; }
        .tabla-fila { grid-template-columns: 1fr 1fr; gap: 4px; padding: 8px; }
        .tabla-fila .col-id { grid-column: 1; }
        .tabla-fila .col-esp { grid-column: 2; text-align: right; font-size: 12px; }
        .tabla-fila .col-desc { grid-column: 1 / -1; font-size: 12px; padding: 2px 0; }
        .tabla-fila .col-estado { grid-column: 1; }
        .tabla-fila .col-tec { grid-column: 2; text-align: right; font-size: 11px; }
    }
    iframe { max-width: 100%; }
    .stSelectbox, .stTextInput, .stButton { max-width: 100%; }
    .stMarkdown { margin-bottom: 0 !important; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: 0.2rem !important; }
</style>
""", unsafe_allow_html=True)

# ==================== BASE DE DATOS DE TECNICOS ====================
TECNICOS_ELE = [
    "RIVERA SANTOS LUIS ALVARO", "NESTOR LEONARDO CORTES TORRES", "JAVIER FELIPE ROZO CALDERON",
    "JHON FREDY BERNAL AVILA", "YUPER YAIL CASTILLO", "ERIK SANTIAGO MARTINEZ HERRERA",
    "QUECANO ANGARITA CARLOS", "PULIDO RIOS JAHIR", "GARCIA CASAS JEFFERSSON DAVID",
    "CASTANEDA ORTIZ EDISON ORACIO", "DIAZ SEGURA DANIEL STEVEN", "FRANCO SIERRA JOSE ALEJANDRO",
    "MOJICA GARCES JEAN CARLOS", "CAROLOINA RINCON", "PINILLA ARIAS JHONATAN FERNANDO",
    "JUAN DAVID CHACON VELANDIA"
]
TECNICOS_MEC = [
    "WILSON ABDON QUEVEDO PASTOR", "LUIS FERNANDO DELGADO CARMONA", "SAENZ SAENZ CARLOS EFREN",
    "PABLO ENRRIQUE TORRES BARON", "FELIPE LATORRE DIAZ", "MOLINA GONZALEZ MICHAEL ANDRES",
    "MURILLO MURILLO WILLIAM OBER", "MOLANO ALFONSO LUIS", "MARTINEZ TORRES FREDY ALEXANDER",
    "VARGAS VARGAS JHON ALEJANDER", "MERINO GIL JOSE MANUEL", "DILAN MEDINA",
    "RODRIGUEZ CAMACHO LUIS ALVEIRO", "MENDIVIELSO CANTOR JUAN CARLOS", "ARIAS  PERDOMO JUAN ESTEBAN",
    "VELASQUEZ OSPINA CRISTIAN JAIR"
]

# ==================== FUNCIONES AUXILIARES ====================
@st.cache_data
def cargar_excel_mantenimiento():
    try:
        df = pd.read_excel("MANTENIMIENTO/Formato de mantenimiento preventivo.xlsx", sheet_name="Inicial")
        if "UN" in df.columns:
            df = df[df["UN"] != "UN"].reset_index(drop=True)
        df.columns = df.columns.str.strip()
        columnas_originales = list(df.columns)
        columnas_mapeo = {}
        for col in columnas_originales:
            col_norm = col.lower().replace(" ", "").replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ñ","n")
            if "ubicacion" in col_norm: columnas_mapeo[col] = "Ubicacion"
            elif "descripcion" in col_norm and "procedimiento" in col_norm: columnas_mapeo[col] = "Descripcion de procedimiento"
            elif "especialidad" in col_norm: columnas_mapeo[col] = "Especialidad"
            elif "equipo" in col_norm: columnas_mapeo[col] = "Equipo"
            elif "id" in col_norm and ("ot" in col_norm or "orden" in col_norm): columnas_mapeo[col] = "ID OT"
        df = df.rename(columns=columnas_mapeo)
        columnas_default = {
            "Estado": "Pendiente", "Comentarios": "", "Tecnico_Asignado": "",
            "Actividades_Hechas": "", "Fecha_Ejecucion": "", "Hora_Inicio": "",
            "Hora_Fin": "", "Prioridad_Actividad": ""
        }
        for col, default in columnas_default.items():
            if col not in df.columns: df[col] = default
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
        df.columns = df.columns.str.strip()
        columnas_originales = list(df.columns)
        columnas_mapeo = {}
        for col in columnas_originales:
            col_upper = col.upper().strip()
            if col_upper == "ACTIVIDAD": columnas_mapeo[col] = "ACTIVIDAD"
            elif col_upper in ["TECNICOS", "TECNICO"]: columnas_mapeo[col] = "TECNICOS"
            elif col_upper in ["ESPE", "ESPECIALIDAD"]: columnas_mapeo[col] = "ESPE"
        df = df.rename(columns=columnas_mapeo)
        if "ACTIVIDAD" in df.columns: df = df[df["ACTIVIDAD"] != "ACTIVIDAD"].reset_index(drop=True)
        if "TECNICOS" in df.columns: df["TECNICOS"] = df["TECNICOS"].astype(str).str.strip()
        if "ESPE" in df.columns: df["ESPE"] = df["ESPE"].astype(str).str.strip()
        return df
    except FileNotFoundError:
        st.error("No se encontro el archivo: MANTENIMIENTO/tecnico.xlsx")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar el archivo de tecnicos: {e}")
        return pd.DataFrame()

def obtener_tecnicos_por_especialidad(especialidad):
    if especialidad == "ELE": return TECNICOS_ELE
    elif especialidad == "MEC": return TECNICOS_MEC
    return TECNICOS_ELE + TECNICOS_MEC

def calcular_progreso(df):
    total = len(df)
    if total == 0: return 0, 0, 0
    ejecutado = len(df[df["Estado"] == "Ejecutado"])
    verificado = len(df[df["Estado"] == "Verificado"])
    pct_ejec = round((ejecutado / total) * 100, 1)
    pct_verif = round((verificado / total) * 100, 1)
    pct_pdte = round(100 - pct_ejec - pct_verif, 1)
    return pct_ejec, pct_pdte, pct_verif

def obtener_estado_visual(estado):
    estados = {"Ejecutado": "estado-ejecutado", "Verificado": "estado-verificado", "Cerrada": "estado-cerrada", "Pendiente": "estado-pendiente"}
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
    clases = {"Rojo": "prioridad-critico", "Amarillo": "prioridad-secundario", "Verde": "prioridad-estandar", "": ""}
    return clases.get(prioridad, "")

def boton_volver_inicio(key_suffix=""):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("VOLVER AL INICIO", use_container_width=True, type="secondary", key=f"volver_inicio_{key_suffix}"):
            st.session_state.pagina = "home"
            st.session_state.orden_seleccionada = None
            st.session_state.busqueda = ""
            st.rerun()

def boton_cerrar_sesion():
    if st.button("🔒 CERRAR SESION", use_container_width=True, type="secondary"):
        st.session_state.perfil = None
        st.session_state.pagina = "login"
        st.session_state.orden_seleccionada = None
        st.session_state.busqueda = ""
        st.rerun()

def obtener_maquinas_disponibles(df):
    if df.empty or "Ubicacion" not in df.columns: return ["Todas"]
    try:
        maquinas = df["Ubicacion"].dropna().unique().tolist()
        maquinas = [m for m in maquinas if str(m).strip()]
        return ["Todas"] + sorted(maquinas)
    except Exception:
        return ["Todas"]

# ==================== INICIALIZAR ESTADO ====================
if "perfil" not in st.session_state: st.session_state.perfil = None
if "pagina" not in st.session_state: st.session_state.pagina = "login"
if "orden_seleccionada" not in st.session_state: st.session_state.orden_seleccionada = None
if "df_mantenimientos" not in st.session_state: st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
if "df_tecnicos" not in st.session_state: st.session_state.df_tecnicos = cargar_excel_tecnicos()
if "filtro_especialidad" not in st.session_state: st.session_state.filtro_especialidad = "Todas"
if "filtro_maquina" not in st.session_state: st.session_state.filtro_maquina = "Todas"
if "filtro_esp_asig" not in st.session_state: st.session_state.filtro_esp_asig = "Todas"
if "filtro_maq_asig" not in st.session_state: st.session_state.filtro_maq_asig = "Todas"
if "filtro_estado_asig" not in st.session_state: st.session_state.filtro_estado_asig = "Todos"
if "busqueda" not in st.session_state: st.session_state.busqueda = ""

# ==================== PANTALLA DE LOGIN ====================
def pantalla_login():
    st.markdown('<div class="tablet-header">App Tablet Mtto Preventivo</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <div style="font-size: 14px; color: #666; margin-bottom: 20px;">Selecciona tu perfil para continuar</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="perfil-card perfil-admin" style="text-align: center; padding: 20px;">
            <div class="perfil-icon">👤</div>
            <div class="perfil-titulo" style="color: #dc3545;">ADMIN</div>
            <div class="perfil-desc">Asigna técnicos<br>Cambia prioridades<br>Ve todo el sistema</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("ENTRAR COMO ADMIN", use_container_width=True, type="primary", key="login_admin"):
            st.session_state.perfil = "admin"
            st.session_state.pagina = "home"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="perfil-card perfil-tecnico" style="text-align: center; padding: 20px;">
            <div class="perfil-icon">🔧</div>
            <div class="perfil-titulo" style="color: #28a745;">TÉCNICO</div>
            <div class="perfil-desc">Ve sus órdenes<br>Ejecuta actividades<br>Comenta y reporta</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("ENTRAR COMO TÉCNICO", use_container_width=True, type="primary", key="login_tecnico"):
            st.session_state.perfil = "tecnico"
            st.session_state.pagina = "home"
            st.rerun()

    with col3:
        st.markdown("""
        <div class="perfil-card perfil-supervisor" style="text-align: center; padding: 20px;">
            <div class="perfil-icon">✓</div>
            <div class="perfil-titulo" style="color: #007bff;">SUPERVISOR</div>
            <div class="perfil-desc">Verifica ejecuciones<br>Revisa calidad<br>Cierra órdenes</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("ENTRAR COMO SUPERVISOR", use_container_width=True, type="primary", key="login_supervisor"):
            st.session_state.perfil = "supervisor"
            st.session_state.pagina = "home"
            st.rerun()

# ==================== PANTALLA DE INICIO (HOME) ====================
def pantalla_home():
    perfil = st.session_state.perfil
    df = st.session_state.df_mantenimientos

    # Header con perfil
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>App Tablet Mtto</span>
        <span style="font-size: 12px; opacity: 0.8;">{'👤 Admin' if perfil == 'admin' else '🔧 Técnico' if perfil == 'tecnico' else '✓ Supervisor'}</span>
    </div>
    """, unsafe_allow_html=True)

    total_ordenes = len(df)
    st.markdown(f"""
    <div class="home-screen">
        <div class="counter-label">ORDENES PREVENTIVAS</div>
        <div class="big-counter">{total_ordenes}</div>
        <div class="counter-label">Total de ordenes activas</div>
    </div>
    """, unsafe_allow_html=True)

    # Filtros por especialidad (todos los perfiles)
    st.markdown("<div style='text-align: center; margin-bottom: 10px; font-weight: 600; color: #666;'>Filtrar por Especialidad</div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1,1,1,1])
    with col1:
        if st.button("TODAS", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "Todas" else "secondary"):
            st.session_state.filtro_especialidad = "Todas"; st.rerun()
    with col2:
        if st.button("ELE", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "ELE" else "secondary"):
            st.session_state.filtro_especialidad = "ELE"; st.rerun()
    with col3:
        if st.button("MEC", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "MEC" else "secondary"):
            st.session_state.filtro_especialidad = "MEC"; st.rerun()
    with col4:
        if st.button("LIMPIAR", use_container_width=True):
            st.session_state.filtro_especialidad = "Todas"; st.session_state.busqueda = ""; st.rerun()

    maquinas = obtener_maquinas_disponibles(df)
    index_sel = 0
    if st.session_state.filtro_maquina in maquinas: index_sel = maquinas.index(st.session_state.filtro_maquina)
    maquina_sel = st.selectbox("Maquina / Ubicacion", maquinas, index=index_sel)
    st.session_state.filtro_maquina = maquina_sel

    st.markdown("<br>", unsafe_allow_html=True)

    # Botones según perfil
    if perfil == "admin":
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("VER ORDENES PREVENTIVAS", use_container_width=True, type="primary"):
                st.session_state.pagina = "ordenes"; st.rerun()
        with col_btn2:
            if st.button("ASIGNACION DE TECNICOS", use_container_width=True, type="primary"):
                st.session_state.pagina = "asignacion"; st.rerun()
    elif perfil == "tecnico":
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("MIS ORDENES ASIGNADAS", use_container_width=True, type="primary"):
                st.session_state.pagina = "mis_ordenes"; st.rerun()
        with col_btn2:
            if st.button("VER TODAS LAS ORDENES", use_container_width=True, type="secondary"):
                st.session_state.pagina = "ordenes"; st.rerun()
    elif perfil == "supervisor":
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("VER ORDENES EJECUTADAS", use_container_width=True, type="primary"):
                st.session_state.pagina = "verificar"; st.rerun()
        with col_btn2:
            if st.button("VER TODAS LAS ORDENES", use_container_width=True, type="secondary"):
                st.session_state.pagina = "ordenes"; st.rerun()

    if not df.empty and "Especialidad" in df.columns:
        st.divider()
        col_a, col_b, col_c = st.columns(3)
        with col_a: st.metric("ELE", len(df[df["Especialidad"] == "ELE"]))
        with col_b: st.metric("MEC", len(df[df["Especialidad"] == "MEC"]))
        with col_c: st.metric("Cerradas", len(df[df["Estado"].isin(["Cerrada", "Verificado"])]))

    st.markdown("<br>", unsafe_allow_html=True)
    boton_cerrar_sesion()

# ==================== PANTALLA DE ORDENES (LISTA) ====================
def pantalla_ordenes():
    df = st.session_state.df_mantenimientos
    perfil = st.session_state.perfil
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Ordenes Preventivas</span>
        <span style="font-size: 14px; opacity: 0.8;">{st.session_state.filtro_especialidad}</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("ordenes_top")

    busqueda = st.text_input("Buscar ID OT, equipo o descripcion...", value=st.session_state.busqueda, placeholder="Escribe para buscar...")
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
        if "Equipo" in df_filtrado.columns: mask |= df_filtrado["Equipo"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "Ubicacion" in df_filtrado.columns: mask |= df_filtrado["Ubicacion"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "ID OT" in df_filtrado.columns: mask |= df_filtrado["ID OT"].astype(str).str.contains(busqueda_lower, na=False)
        if "Descripcion de procedimiento" in df_filtrado.columns: mask |= df_filtrado["Descripcion de procedimiento"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        df_filtrado = df_filtrado[mask]

    st.subheader(f"Ordenes ({len(df_filtrado)})")

    st.markdown("""
    <div class="tabla-header">
        <div class="col-id">ID OT</div><div class="col-esp">ESP</div><div class="col-desc">DESCRIPCION</div>
        <div class="col-estado">ESTADO</div><div class="col-tec">TECNICO</div>
    </div>
    """, unsafe_allow_html=True)

    for idx, row in df_filtrado.iterrows():
        id_ot = str(row.get("ID OT", "")); tipo = str(row.get("Especialidad", ""))
        descripcion = str(row.get("Descripcion de procedimiento", ""))
        estado = str(row.get("Estado", "Pendiente")); tecnico = str(row.get("Tecnico_Asignado", ""))
        if not tecnico or tecnico == "nan": tecnico = "Sin asignar"
        estado_clase = obtener_estado_visual(estado)
        desc_corta = descripcion[:35] + "..." if len(descripcion) > 35 else descripcion
        prioridad = str(row.get("Prioridad_Actividad", ""))
        clase_prioridad = obtener_clase_css_prioridad(prioridad)

        st.markdown(f"""
        <div class="tabla-fila {clase_prioridad}">
            <div class="col-id"><strong>{id_ot}</strong></div>
            <div class="col-esp">{tipo}</div>
            <div class="col-desc" title="{descripcion}">{desc_corta}</div>
            <div class="col-estado"><span class="estado-badge {estado_clase}">{estado}</span></div>
            <div class="col-tec">{tecnico}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"Ver detalle", key=f"btn_ver_{idx}", use_container_width=True):
            st.session_state.orden_seleccionada = idx; st.session_state.pagina = "detalle"; st.rerun()

# ==================== PANTALLA MIS ORDENES (TÉCNICO) ====================
def pantalla_mis_ordenes():
    df = st.session_state.df_mantenimientos
    perfil = st.session_state.perfil
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>🔧 Mis Ordenes Asignadas</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("mis_ordenes_top")

    # Filtrar solo las ordenes del técnico
    df_mias = df.copy()
    if "Tecnico_Asignado" in df_mias.columns:
        # Para demo, si no hay técnico logueado específico, mostramos todas las asignadas
        df_mias = df_mias[df_mias["Tecnico_Asignado"].notna() & (df_mias["Tecnico_Asignado"] != "")]
        # Filtrar por especialidad si aplica
        if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_mias.columns:
            df_mias = df_mias[df_mias["Especialidad"] == st.session_state.filtro_especialidad]
        if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_mias.columns:
            df_mias = df_mias[df_mias["Ubicacion"] == st.session_state.filtro_maquina]
    else:
        df_mias = pd.DataFrame()

    st.subheader(f"Tienes {len(df_mias)} orden(es) asignada(s)")

    if df_mias.empty:
        st.info("No tienes ordenes asignadas actualmente.")
        return

    for idx, row in df_mias.iterrows():
        id_ot = str(row.get("ID OT", "")); tipo = str(row.get("Especialidad", ""))
        descripcion = str(row.get("Descripcion de procedimiento", ""))
        estado = str(row.get("Estado", "Pendiente")); tecnico = str(row.get("Tecnico_Asignado", ""))
        estado_clase = obtener_estado_visual(estado)
        desc_corta = descripcion[:35] + "..." if len(descripcion) > 35 else descripcion
        prioridad = str(row.get("Prioridad_Actividad", ""))
        clase_prioridad = obtener_clase_css_prioridad(prioridad)
        info_prioridad = obtener_color_prioridad(prioridad)

        st.markdown(f"""
        <div class="tabla-fila {clase_prioridad}">
            <div class="col-id"><strong>{id_ot}</strong></div>
            <div class="col-esp">{tipo}</div>
            <div class="col-desc" title="{descripcion}">{desc_corta}</div>
            <div class="col-estado"><span class="estado-badge {estado_clase}">{estado}</span></div>
            <div class="col-tec">{tecnico[:15]}...</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Ver detalle", key=f"btn_ver_tec_{idx}", use_container_width=True):
                st.session_state.orden_seleccionada = idx; st.session_state.pagina = "detalle_tecnico"; st.rerun()
        with col2:
            if estado == "Pendiente" and st.button(f"▶ Ejecutar", key=f"btn_ejec_{idx}", use_container_width=True, type="primary"):
                st.session_state.orden_seleccionada = idx; st.session_state.pagina = "ejecutar"; st.rerun()

# ==================== PANTALLA EJECUTAR ORDEN (TÉCNICO) ====================
def pantalla_ejecutar():
    df = st.session_state.df_mantenimientos
    idx = st.session_state.orden_seleccionada
    if idx is None or idx not in df.index:
        st.session_state.pagina = "mis_ordenes"; st.rerun(); return

    row = df.loc[idx]
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>🔧 Ejecutar OT {row.get('ID OT', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("⬅ Volver", use_container_width=True, type="secondary"):
            st.session_state.pagina = "mis_ordenes"; st.rerun()
    with col_home:
        if st.button("🏠 Inicio", use_container_width=True, type="secondary"):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()

    st.markdown(f"""
    <div class="detail-panel">
        <div class="equipo-info">
            <strong>Equipo:</strong> {row.get('Equipo', '')}<br>
            <strong>Ubicacion:</strong> {row.get('Ubicacion', '')}<br>
            <strong>Especialidad:</strong> {row.get('Especialidad', '')}<br>
            <strong>Estado actual:</strong> {row.get('Estado', 'Pendiente')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Descripcion del Procedimiento")
    st.write(row.get("Descripcion de procedimiento", "Sin descripcion"))

    st.subheader("Registro de Ejecucion")
    col1, col2 = st.columns(2)
    with col1:
        hora_inicio = st.time_input("Hora Inicio", value=datetime.now().time(), key="hora_inicio_ejec")
    with col2:
        hora_fin = st.time_input("Hora Fin", value=datetime.now().time(), key="hora_fin_ejec")

    st.subheader("Comentarios de Ejecucion")
    comentarios = row.get("Comentarios", "")
    nuevo_comentario = st.text_area("Describa lo realizado...", value=comentarios, key="comentario_ejecucion")

    st.subheader("Actividades Realizadas")
    actividades = st.text_area("Liste las actividades hechas (una por linea)...", value=row.get("Actividades_Hechas", ""), key="actividades_hechas")

    if st.button("✅ MARCAR COMO EJECUTADO", use_container_width=True, type="primary"):
        df.at[idx, "Estado"] = "Ejecutado"
        df.at[idx, "Comentarios"] = nuevo_comentario
        df.at[idx, "Actividades_Hechas"] = actividades
        df.at[idx, "Fecha_Ejecucion"] = datetime.now().strftime("%Y-%m-%d")
        df.at[idx, "Hora_Inicio"] = hora_inicio.strftime("%H:%M")
        df.at[idx, "Hora_Fin"] = hora_fin.strftime("%H:%M")
        st.success("Orden marcada como EJECUTADA correctamente")
        st.balloons()
        st.session_state.pagina = "mis_ordenes"
        st.rerun()

# ==================== PANTALLA DETALLE TÉCNICO ====================
def pantalla_detalle_tecnico():
    df = st.session_state.df_mantenimientos
    idx = st.session_state.orden_seleccionada
    if idx is None or idx not in df.index:
        st.session_state.pagina = "mis_ordenes"; st.rerun(); return

    row = df.loc[idx]
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Detalle OT {row.get('ID OT', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("⬅ Volver", use_container_width=True, type="secondary"):
            st.session_state.pagina = "mis_ordenes"; st.rerun()
    with col_home:
        if st.button("🏠 Inicio", use_container_width=True, type="secondary"):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()

    prioridad = str(row.get("Prioridad_Actividad", ""))
    info_prioridad = obtener_color_prioridad(prioridad)
    if prioridad:
        st.info(f"**Prioridad: {info_prioridad['label']}** — {info_prioridad['desc']}")

    st.markdown(f"""
    <div class="detail-panel">
        <div class="equipo-info">
            <strong>Equipo:</strong> {row.get('Equipo', '')}<br>
            <strong>Ubicacion:</strong> {row.get('Ubicacion', '')}<br>
            <strong>Especialidad:</strong> {row.get('Especialidad', '')}<br>
            <strong>Estado:</strong> {row.get('Estado', 'Pendiente')}<br>
            <strong>Tecnico Asignado:</strong> {row.get('Tecnico_Asignado', 'Sin asignar')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Descripcion del Procedimiento")
    st.write(row.get("Descripcion de procedimiento", "Sin descripcion"))

    if row.get("Actividades_Hechas"):
        st.subheader("Actividades Realizadas")
        st.write(row.get("Actividades_Hechas"))

    if row.get("Comentarios"):
        st.subheader("Comentarios")
        st.info(row.get("Comentarios"))

    if row.get("Fecha_Ejecucion"):
        st.success(f"Ejecutado el: {row.get('Fecha_Ejecucion')} | Inicio: {row.get('Hora_Inicio', 'N/A')} | Fin: {row.get('Hora_Fin', 'N/A')}")

# ==================== PANTALLA VERIFICAR (SUPERVISOR) ====================
def pantalla_verificar():
    df = st.session_state.df_mantenimientos
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>✓ Verificar Ordenes Ejecutadas</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("verificar_top")

    df_verificar = df.copy()
    if "Estado" in df_verificar.columns:
        df_verificar = df_verificar[df_verificar["Estado"] == "Ejecutado"]
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_verificar.columns:
        df_verificar = df_verificar[df_verificar["Especialidad"] == st.session_state.filtro_especialidad]
    if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_verificar.columns:
        df_verificar = df_verificar[df_verificar["Ubicacion"] == st.session_state.filtro_maquina]

    st.subheader(f"Ordenes por verificar: {len(df_verificar)}")

    if df_verificar.empty:
        st.success("No hay ordenes ejecutadas pendientes de verificacion.")
        return

    for idx, row in df_verificar.iterrows():
        id_ot = str(row.get("ID OT", "")); tipo = str(row.get("Especialidad", ""))
        descripcion = str(row.get("Descripcion de procedimiento", ""))
        tecnico = str(row.get("Tecnico_Asignado", "Sin asignar"))
        desc_corta = descripcion[:35] + "..." if len(descripcion) > 35 else descripcion

        with st.container():
            st.markdown(f"""
            <div class="tabla-fila-asig">
                <div class="asig-info">
                    <div class="asig-ot"><strong>OT {id_ot}</strong> | <span class="asig-esp">{tipo}</span></div>
                    <div class="asig-equipo">{desc_corta}</div>
                    <div style="font-size: 10px; color: #28a745;">Ejecutado por: {tecnico} | Fecha: {row.get('Fecha_Ejecucion', 'N/A')}</div>
                </div>
                <div class="asig-estado"><span class="estado-badge estado-ejecutado">Ejecutado</span></div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Ver detalle de ejecucion"):
                st.write(f"**Actividades:** {row.get('Actividades_Hechas', 'No registradas')}")
                st.write(f"**Comentarios:** {row.get('Comentarios', 'Sin comentarios')}")
                st.write(f"**Horario:** {row.get('Hora_Inicio', 'N/A')} - {row.get('Hora_Fin', 'N/A')}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✓ VERIFICAR", key=f"btn_verif_{idx}", use_container_width=True, type="primary"):
                        df.at[idx, "Estado"] = "Verificado"
                        st.success(f"OT {id_ot} verificada correctamente")
                        st.rerun()
                with col2:
                    if st.button("✕ RECHAZAR", key=f"btn_rech_{idx}", use_container_width=True, type="secondary"):
                        df.at[idx, "Estado"] = "Pendiente"
                        st.warning(f"OT {id_ot} devuelta a Pendiente")
                        st.rerun()

# ==================== PANTALLA DE DETALLE (ADMIN) ====================
def pantalla_detalle():
    df = st.session_state.df_mantenimientos
    idx = st.session_state.orden_seleccionada
    if idx is None or idx not in df.index:
        st.session_state.pagina = "ordenes"; st.rerun(); return

    row = df.loc[idx]
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Detalle OT {row.get('ID OT', '')}</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("detalle_top")

    prioridad = str(row.get("Prioridad_Actividad", ""))
    info_prioridad = obtener_color_prioridad(prioridad)
    if prioridad:
        st.info(f"**Prioridad: {info_prioridad['label']}** — {info_prioridad['desc']}")

    st.markdown(f"""
    <div class="detail-panel">
        <div class="equipo-info">
            <strong>Equipo:</strong> {row.get('Equipo', '')}<br>
            <strong>Ubicacion:</strong> {row.get('Ubicacion', '')}<br>
            <strong>Especialidad:</strong> {row.get('Especialidad', '')}<br>
            <strong>Estado:</strong> {row.get('Estado', 'Pendiente')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Descripcion del Procedimiento")
    st.write(row.get("Descripcion de procedimiento", "Sin descripcion"))

    st.subheader("Tecnico Asignado")
    tecnico_actual = row.get("Tecnico_Asignado", "")
    if tecnico_actual: st.success(f"{tecnico_actual}")
    else: st.warning("Sin tecnico asignado")

    # Cambiar estado (solo admin)
    estado_actual = row.get("Estado", "Pendiente")
    nuevo_estado = st.selectbox("Cambiar Estado", ["Pendiente", "Ejecutado", "Verificado", "Cerrada"], index=["Pendiente", "Ejecutado", "Verificado", "Cerrada"].index(estado_actual))
    if nuevo_estado != estado_actual:
        df.at[idx, "Estado"] = nuevo_estado
        if nuevo_estado == "Ejecutado":
            df.at[idx, "Fecha_Ejecucion"] = datetime.now().strftime("%Y-%m-%d")
        st.success(f"Estado cambiado a: {nuevo_estado}")
        st.rerun()

    st.subheader("Comentarios")
    comentarios = row.get("Comentarios", "")
    nuevo_comentario = st.text_area("Agregar comentario", value=comentarios, key="comentario_detalle")
    if st.button("Guardar Comentario", key="guardar_comentario"):
        df.at[idx, "Comentarios"] = nuevo_comentario
        st.success("Comentario guardado"); st.rerun()

    if st.button("GUARDAR CAMBIOS", use_container_width=True, type="primary"):
        st.success("Cambios guardados en memoria (recuerda: en Streamlit Cloud los cambios no persisten)")

    boton_volver_inicio("detalle_bottom")

# ==================== PANTALLA DE ASIGNACION (ADMIN) ====================
def pantalla_asignacion():
    df = st.session_state.df_mantenimientos
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Asignacion de Tecnicos</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("asignacion_top")

    col1, col2, col3 = st.columns(3)
    with col1:
        esp_sel = st.selectbox("Especialidad", ["Todas", "ELE", "MEC"], index=["Todas", "ELE", "MEC"].index(st.session_state.filtro_esp_asig))
        st.session_state.filtro_esp_asig = esp_sel
    with col2:
        maquinas = obtener_maquinas_disponibles(df)
        index_sel = 0
        if st.session_state.filtro_maq_asig in maquinas: index_sel = maquinas.index(st.session_state.filtro_maq_asig)
        maq_sel = st.selectbox("Maquina", maquinas, index=index_sel)
        st.session_state.filtro_maq_asig = maq_sel
    with col3:
        estados = ["Todos", "Pendiente", "Ejecutado", "Verificado", "Cerrada"]
        est_sel = st.selectbox("Estado", estados, index=estados.index(st.session_state.filtro_estado_asig))
        st.session_state.filtro_estado_asig = est_sel

    df_asig = df.copy()
    if st.session_state.filtro_esp_asig != "Todas" and "Especialidad" in df_asig.columns:
        df_asig = df_asig[df_asig["Especialidad"] == st.session_state.filtro_esp_asig]
    if st.session_state.filtro_maq_asig != "Todas" and "Ubicacion" in df_asig.columns:
        df_asig = df_asig[df_asig["Ubicacion"] == st.session_state.filtro_maq_asig]
    if st.session_state.filtro_estado_asig != "Todos" and "Estado" in df_asig.columns:
        df_asig = df_asig[df_asig["Estado"] == st.session_state.filtro_estado_asig]

    st.subheader(f"Ordenes para asignar ({len(df_asig)})")

    for idx, row in df_asig.iterrows():
        id_ot = str(row.get("ID OT", "")); equipo = str(row.get("Equipo", ""))
        ubicacion = str(row.get("Ubicacion", "")); especialidad = str(row.get("Especialidad", ""))
        estado = str(row.get("Estado", "Pendiente")); tecnico_actual = str(row.get("Tecnico_Asignado", ""))
        prioridad_actual = str(row.get("Prioridad_Actividad", ""))
        estado_clase = obtener_estado_visual(estado)

        st.markdown(f"""
        <div class="tabla-fila-asig">
            <div class="asig-info">
                <div class="asig-ot"><strong>OT {id_ot}</strong> | <span class="asig-esp">{especialidad}</span></div>
                <div class="asig-equipo">{equipo} | {ubicacion}</div>
            </div>
            <div class="asig-estado"><span class="estado-badge {estado_clase}">{estado}</span></div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            tecnicos_disponibles = obtener_tecnicos_por_especialidad(especialidad)
            opciones = ["-- Sin asignar --"] + tecnicos_disponibles
            indice_actual = 0
            if tecnico_actual and tecnico_actual in tecnicos_disponibles:
                indice_actual = tecnicos_disponibles.index(tecnico_actual) + 1
            tecnico_seleccionado = st.selectbox("Tecnico", opciones, index=indice_actual, key=f"tec_asig_{idx}", label_visibility="collapsed")
        with col2:
            prioridades = ["-- Sin prioridad --", "Rojo", "Amarillo", "Verde"]
            indice_prioridad = 0
            if prioridad_actual and prioridad_actual in prioridades:
                indice_prioridad = prioridades.index(prioridad_actual)
            prioridad_seleccionada = st.selectbox("Prioridad", prioridades, index=indice_prioridad, key=f"prio_asig_{idx}", label_visibility="collapsed")

        if tecnico_seleccionado != "-- Sin asignar --":
            if tecnico_seleccionado != tecnico_actual: df.at[idx, "Tecnico_Asignado"] = tecnico_seleccionado
        else:
            if tecnico_actual: df.at[idx, "Tecnico_Asignado"] = ""
        if prioridad_seleccionada != "-- Sin prioridad --":
            if prioridad_seleccionada != prioridad_actual: df.at[idx, "Prioridad_Actividad"] = prioridad_seleccionada
        else:
            if prioridad_actual: df.at[idx, "Prioridad_Actividad"] = ""
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if st.button("Guardar todas las asignaciones", use_container_width=True, type="primary"):
        st.success("Asignaciones guardadas correctamente")

    boton_volver_inicio("asignacion_bottom")

# ==================== MAIN ====================
if st.session_state.perfil is None or st.session_state.pagina == "login":
    pantalla_login()
elif st.session_state.pagina == "home":
    pantalla_home()
elif st.session_state.pagina == "ordenes":
    pantalla_ordenes()
elif st.session_state.pagina == "detalle":
    pantalla_detalle()
elif st.session_state.pagina == "asignacion":
    pantalla_asignacion()
elif st.session_state.pagina == "mis_ordenes":
    pantalla_mis_ordenes()
elif st.session_state.pagina == "detalle_tecnico":
    pantalla_detalle_tecnico()
elif st.session_state.pagina == "ejecutar":
    pantalla_ejecutar()
elif st.session_state.pagina == "verificar":
    pantalla_verificar()
