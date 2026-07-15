
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
import requests
from io import BytesIO

# ==================== CONFIGURACION GITHUB ====================
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "edwin34776-maker/app-mantenimiento-tablet")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

RUTA_EXCEL = "MANTENIMIENTO/Formato de mantenimiento preventivo.xlsx"
RUTA_TECNICOS = "MANTENIMIENTO/tecnico.xlsx"

# ==================== FUNCIONES GITHUB ====================
def leer_archivo_github(ruta_archivo):
    """Lee un archivo desde GitHub. Retorna (contenido_bytes, sha) o (None, None)."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ruta_archivo}"
    params = {"ref": GITHUB_BRANCH}
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            contenido = base64.b64decode(data["content"])
            return contenido, data["sha"]
        elif response.status_code == 404:
            return None, None
        else:
            st.error(f"Error leyendo {ruta_archivo}: {response.status_code}")
            return None, None
    except Exception as e:
        st.error(f"Error de conexion: {e}")
        return None, None

def escribir_archivo_github(ruta_archivo, contenido_bytes, mensaje_commit, sha=None):
    """Escribe o actualiza un archivo en GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ruta_archivo}"
    contenido_b64 = base64.b64encode(contenido_bytes).decode("utf-8")
    data = {"message": mensaje_commit, "content": contenido_b64, "branch": GITHUB_BRANCH}
    if sha:
        data["sha"] = sha
    try:
        response = requests.put(url, headers=HEADERS, json=data, timeout=20)
        if response.status_code in [200, 201]:
            return True
        else:
            st.error(f"Error guardando: {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        st.error(f"Error de conexion al guardar: {e}")
        return False

def cargar_excel_github(ruta_archivo, sheet_name="Inicial"):
    """Carga un Excel desde GitHub."""
    contenido, sha = leer_archivo_github(ruta_archivo)
    if contenido is None:
        return pd.DataFrame(), None
    try:
        df = pd.read_excel(BytesIO(contenido), sheet_name=sheet_name)
        return df, sha
    except Exception as e:
        # No mostrar error si la hoja no existe (es normal la primera vez)
        if "not found" in str(e).lower() or "no sheet" in str(e).lower():
            return pd.DataFrame(), sha
        st.error(f"Error leyendo Excel: {e}")
        return pd.DataFrame(), sha

def guardar_excel_github(ruta_archivo, df_dict, mensaje_commit, sha=None):
    """Guarda DataFrames en un Excel en GitHub."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for nombre_hoja, df in df_dict.items():
            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    buffer.seek(0)
    return escribir_archivo_github(ruta_archivo, buffer.getvalue(), mensaje_commit, sha)

def fusionar_asignaciones(df_base, df_asig):
    """Fusiona las asignaciones guardadas con los datos base."""
    if df_asig.empty:
        return df_base
    columnas_editables = [
        "Tecnico_Asignado", "Estado", "Prioridad_Actividad",
        "Comentarios", "Actividades_Hechas", "Fecha_Ejecucion",
        "Hora_Inicio", "Hora_Fin"
    ]
    for col in columnas_editables:
        if col in df_asig.columns and col in df_base.columns:
            try:
                mapeo = df_asig.set_index("ID OT")[col].to_dict()
                for idx in df_base.index:
                    id_ot = str(df_base.at[idx, "ID OT"])
                    if id_ot in mapeo and pd.notna(mapeo[id_ot]) and str(mapeo[id_ot]) not in ["", "nan"]:
                        df_base.at[idx, col] = mapeo[id_ot]
            except:
                pass
    return df_base

def guardar_asignaciones_github(df):
    """Guarda las asignaciones en la hoja 'Asignaciones' del Excel en GitHub."""
    contenido, sha = leer_archivo_github(RUTA_EXCEL)
    if contenido is None:
        st.error("No se pudo leer el archivo actual de GitHub")
        return False
    try:
        excel_file = pd.ExcelFile(BytesIO(contenido))
        hojas = {}
        for nombre in excel_file.sheet_names:
            if nombre != "Asignaciones":
                hojas[nombre] = pd.read_excel(BytesIO(contenido), sheet_name=nombre)
        columnas_asig = [
            "ID OT", "Tecnico_Asignado", "Estado", "Prioridad_Actividad",
            "Comentarios", "Actividades_Hechas", "Fecha_Ejecucion",
            "Hora_Inicio", "Hora_Fin"
        ]
        columnas_existentes = [c for c in columnas_asig if c in df.columns]
        hojas["Asignaciones"] = df[columnas_existentes].copy()
        mensaje = f"Actualizacion asignaciones - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return guardar_excel_github(RUTA_EXCEL, hojas, mensaje, sha)
    except Exception as e:
        st.error(f"Error guardando asignaciones: {e}")
        return False

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
@st.cache_data(ttl=60)
def cargar_excel_mantenimiento():
    try:
        df, sha = cargar_excel_github(RUTA_EXCEL, sheet_name="Inicial")
        if df.empty:
            st.error("No se encontro el archivo de mantenimiento en GitHub")
            return pd.DataFrame()
        st.session_state["sha_mantenimiento"] = sha
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
        # Cargar asignaciones guardadas (silencioso si no existe)
        try:
            df_asig, _ = cargar_excel_github(RUTA_EXCEL, sheet_name="Asignaciones")
            if not df_asig.empty:
                df = fusionar_asignaciones(df, df_asig)
        except:
            pass
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo de mantenimiento: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def cargar_excel_tecnicos():
    try:
        df, _ = cargar_excel_github(RUTA_TECNICOS, sheet_name="query")
        if df.empty:
            st.error("No se encontro el archivo de tecnicos en GitHub")
            return pd.DataFrame()
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
if "orden_seleccionad
