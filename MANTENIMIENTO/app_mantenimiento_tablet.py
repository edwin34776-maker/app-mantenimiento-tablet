
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

    /* Fix para tablet - evitar scroll horizontal */
    .main .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 100% !important;
    }

    /* Asegurar que el contenido no se desborde */
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

    .progress-item {
        text-align: center;
    }

    .progress-value {
        font-size: 22px;
        font-weight: 800;
    }

    .progress-label {
        font-size: 11px;
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

    /* ==================== TABLA COMPACTA ORDENES ==================== */
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

    .tabla-fila .col-id {
        font-family: monospace;
        font-size: 11px;
        color: #495057;
    }

    .tabla-fila .col-esp {
        font-weight: 600;
        font-size: 11px;
        color: #1a237e;
    }

    .tabla-fila .col-desc {
        font-size: 11px;
        color: #212529;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .tabla-fila .col-estado {
        text-align: center;
    }

    .tabla-fila .col-tec {
        font-size: 10px;
        color: #6c757d;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* ==================== TABLA ASIGNACION ==================== */
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

    .asig-info {
        min-width: 0;
        overflow: hidden;
    }

    .asig-ot {
        font-size: 12px;
        color: #212529;
        margin-bottom: 2px;
    }

    .asig-esp {
        color: #1a237e;
        font-weight: 600;
        font-size: 11px;
    }

    .asig-equipo {
        font-size: 10px;
        color: #6c757d;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .asig-estado {
        text-align: right;
        flex-shrink: 0;
    }

    /* ==================== RESPONSIVE ==================== */
    @media (max-width: 768px) {
        .big-counter { font-size: 48px; }
        .tablet-header { font-size: 16px; padding: 10px 12px; }
        .home-screen { padding: 5px; }
       
        .tabla-header {
            font-size: 9px;
            grid-template-columns: 60px 40px 1fr 80px 90px;
            padding: 6px 8px;
        }
       
        .tabla-fila {
            font-size: 11px;
            grid-template-columns: 60px 40px 1fr 80px 90px;
            padding: 6px 8px;
        }
    }

    @media (max-width: 480px) {
        .tabla-header {
            display: none;
        }
       
        .tabla-fila {
            grid-template-columns: 1fr 1fr;
            gap: 4px;
            padding: 8px;
        }
       
        .tabla-fila .col-id { grid-column: 1; }
        .tabla-fila .col-esp { grid-column: 2; text-align: right; font-size: 12px; }
        .tabla-fila .col-desc { grid-column: 1 / -1; font-size: 12px; padding: 2px 0; }
        .tabla-fila .col-estado { grid-column: 1; }
        .tabla-fila .col-tec { grid-column: 2; text-align: right; font-size: 11px; }
    }

    /* Fix para evitar que el contenido se oculte */
    iframe { max-width: 100%; }
    .stSelectbox, .stTextInput, .stButton { max-width: 100%; }
   
    /* Reducir espacio entre elementos de Streamlit */
    .stMarkdown { margin-bottom: 0 !important; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: 0.2rem !important; }
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

        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip()
       
        # Mapeo robusto: buscar columnas por coincidencia de texto
        columnas_originales = list(df.columns)
        columnas_mapeo = {}
       
        for col in columnas_originales:
            col_norm = col.lower().replace(" ", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            if "ubicacion" in col_norm:
                columnas_mapeo[col] = "Ubicacion"
            elif "descripcion" in col_norm and "procedimiento" in col_norm:
                columnas_mapeo[col] = "Descripcion de procedimiento"
            elif "especialidad" in col_norm:
                columnas_mapeo[col] = "Especialidad"
            elif "equipo" in col_norm:
                columnas_mapeo[col] = "Equipo"
            elif "id" in col_norm and ("ot" in col_norm or "orden" in col_norm):
                columnas_mapeo[col] = "ID OT"
       
        df = df.rename(columns=columnas_mapeo)

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
       
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip()
       
        columnas_originales = list(df.columns)
        columnas_mapeo = {}
        for col in columnas_originales:
            col_upper = col.upper().strip()
            if col_upper == "ACTIVIDAD":
                columnas_mapeo[col] = "ACTIVIDAD"
            elif col_upper == "TECNICOS" or col_upper == "TECNICO":
                columnas_mapeo[col] = "TECNICOS"
            elif col_upper == "ESPE" or col_upper == "ESPECIALIDAD":
                columnas_mapeo[col] = "ESPE"
       
        df = df.rename(columns=columnas_mapeo)
       
        if "ACTIVIDAD" in df.columns:
            df = df[df["ACTIVIDAD"] != "ACTIVIDAD"].reset_index(drop=True)
        if "TECNICOS" in df.columns:
            df["TECNICOS"] = df["TECNICOS"].astype(str).str.strip()
        if "ESPE" in df.columns:
            df["ESPE"] = df["ESPE"].astype(str).str.strip()
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

    # Asegurar que el valor seleccionado esté en la lista
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
            st.metric("Ce
