import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import io

# ==================== CONFIGURACION SUPABASE ====================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://cpazmoebqbsrahviifvp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_KEY:
    st.error("SUPABASE_KEY no configurada. Revisa tu secrets.toml o variables de entorno.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================== DESTINATARIOS POR DEFECTO ====================
DESTINATARIOS_DEFAULT = [
    "mantobogota@gmail.com",
    "supermantobogota@gmail.com"
]

# ==================== FUNCIONES DE CORREO ELECTRONICO ====================
def enviar_correo_preventivo(df, destinatarios, asunto, area_mecanica="INY4 MEC", email_remitente=None):
    if email_remitente == "supermantobogota@gmail.com":
        email_user = st.secrets.get("EMAIL_USER_2", "")
        email_pass = st.secrets.get("EMAIL_PASS_2", "")
    else:
        email_user = st.secrets.get("EMAIL_USER", "")
        email_pass = st.secrets.get("EMAIL_PASS", "")

    if not email_user or not email_pass:
        return False, "Credenciales de correo no configuradas en secrets.toml"

    total = len(df)
    if total == 0:
        ejecutadas_pct = pendientes_pct = verificar_pct = 0.0
    else:
        ejecutadas = len(df[df["Estado"] == "Ejecutado"])
        pendientes = len(df[df["Estado"] == "Pendiente"])
        verificar = len(df[df["Estado"] == "Verificado"])
        ejecutadas_pct = round((ejecutadas / total) * 100, 1)
        pendientes_pct = round((pendientes / total) * 100, 1)
        verificar_pct = round((verificar / total) * 100, 1)

    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Preventivas')
    except Exception as e:
        return False, f"Error creando Excel: {str(e)}"
    output.seek(0)

    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <p style="font-size: 16px; font-weight: bold;">Preventivo</p>
        <p style="font-size: 14px;">{area_mecanica}</p>
        <p style="font-size: 14px;">Ejecutadas {ejecutadas_pct}%</p>
        <p style="font-size: 14px;">Pendientes {pendientes_pct}%</p>
        <p style="font-size: 14px;">Verificar {verificar_pct}%</p>
        <br>
        <p style="font-size: 14px;">Comentario:</p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = ", ".join(destinatarios)
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo_html, 'html'))

    attachment = MIMEBase('application', 'octet-stream')
    attachment.set_payload(output.read())
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', f'attachment; filename="{area_mecanica}.xlsx"')
    msg.attach(attachment)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email_user, email_pass)
        server.sendmail(email_user, destinatarios, msg.as_string())
        server.quit()
        return True, f"Correo enviado desde {email_user}"
    except Exception as e:
        return False, f"Error al enviar: {str(e)}"


# ==================== FUNCIONES SUPABASE ====================
def cargar_ordenes_supabase():
    try:
        response = supabase.table("ordenes_trabajo").select("*").order("id_ot", desc=False).execute()
        data = response.data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        columnas_mapeo = {}
        for col in df.columns:
            if col == "id_ot": columnas_mapeo[col] = "ID OT"
            elif col == "descripcion_procedimiento": columnas_mapeo[col] = "Descripcion de procedimiento"
            elif col == "tecnico_asignado": columnas_mapeo[col] = "Tecnico_Asignado"
            elif col == "prioridad_actividad": columnas_mapeo[col] = "Prioridad_Actividad"
            elif col == "actividades_hechas": columnas_mapeo[col] = "Actividades_Hechas"
            elif col == "fecha_ejecucion": columnas_mapeo[col] = "Fecha_Ejecucion"
            elif col == "hora_inicio": columnas_mapeo[col] = "Hora_Inicio"
            elif col == "hora_fin": columnas_mapeo[col] = "Hora_Fin"
            else: columnas_mapeo[col] = col.capitalize()
        df = df.rename(columns=columnas_mapeo)
        columnas_default = {
            "Estado": "Pendiente", "Comentarios": "", "Tecnico_Asignado": "",
            "Actividades_Hechas": "", "Fecha_Ejecucion": "", "Hora_Inicio": "",
            "Hora_Fin": "", "Prioridad_Actividad": ""
        }
        for col, default in columnas_default.items():
            if col not in df.columns:
                df[col] = default
        return df
    except Exception as e:
        st.error(f"Error cargando ordenes: {e}")
        return pd.DataFrame()

def guardar_orden_supabase(id_ot, datos):
    try:
        datos_supabase = {"id_ot": str(id_ot)}
        for key, value in datos.items():
            key_snake = key.lower().replace(" ", "_").replace(".", "").replace("-", "_")
            if key_snake in ["id_ot", "descripcion_de_procedimiento"]:
                key_snake = key_snake.replace("_de_", "_").replace("__", "_")
            datos_supabase[key_snake] = value if not pd.isna(value) else None
        supabase.table("ordenes_trabajo").upsert(datos_supabase).execute()
        return True
    except Exception as e:
        st.error(f"Error guardando orden: {e}")
        return False

def actualizar_orden_supabase(id_ot, campo, valor):
    try:
        campo_snake = campo.lower().replace(" ", "_").replace(".", "").replace("-", "_")
        supabase.table("ordenes_trabajo").update({campo_snake: valor}).eq("id_ot", id_ot).execute()
        return True
    except Exception as e:
        st.error(f"Error actualizando campo: {e}")
        return False

def guardar_asignaciones_supabase(df):
    try:
        columnas_editables = [
            "Tecnico_Asignado", "Estado", "Prioridad_Actividad",
            "Comentarios", "Actividades_Hechas", "Fecha_Ejecucion",
            "Hora_Inicio", "Hora_Fin"
        ]
        exitosos = 0
        for idx, row in df.iterrows():
            id_ot = str(row.get("ID OT", ""))
            if not id_ot:
                continue
            datos = {}
            for col in columnas_editables:
                if col in row.index and pd.notna(row[col]):
                    datos[col] = row[col]
            if datos:
                if guardar_orden_supabase(id_ot, datos):
                    exitosos += 1
        st.success(f"{exitosos} ordenes actualizadas en Supabase")
        return exitosos > 0
    except Exception as e:
        st.error(f"Error guardando asignaciones: {e}")
        return False


# Configuracion de la pagina
st.set_page_config(
    page_title="App Tablet Mtto Preventivo",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== ESTILOS CSS ====================
st.markdown("""
<style>
    .stApp { background-color: #f0f2f5; max-width: 100vw; overflow-x: hidden; }
    .main .block-container { padding-left: 0.8rem !important; padding-right: 0.8rem !important; max-width: 100% !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
    .tablet-header {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white; padding: 12px 16px; border-radius: 0 0 16px 16px;
        text-align: center; font-size: 18px; font-weight: 700;
        margin: -1rem -1rem 1rem -1rem; box-shadow: 0 4px 15px rgba(26,35,158,0.3);
        position: sticky; top: 0; z-index: 100; width: 100%; box-sizing: border-box; word-wrap: break-word;
    }
    .home-screen { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; min-height: auto; text-align: center; padding: 10px; width: 100%; box-sizing: border-box; }
    .big-counter { font-size: 60px; font-weight: 900; color: #1a237e; line-height: 1; margin: 10px 0; word-wrap: break-word; }
    .counter-label { font-size: 18px; color: #666; margin-bottom: 30px; }
    .estado-badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-align: center; white-space: nowrap; }
    .estado-ejecutado { background-color: #d4edda; color: #155724; }
    .estado-pendiente { background-color: #fff3cd; color: #856404; }
    .estado-verificado { background-color: #cce5ff; color: #004085; }
    .estado-cerrada { background-color: #d1ecf1; color: #0c5460; }
    .progress-bar-container { display: flex; gap: 15px; justify-content: center; margin: 15px 0; padding: 12px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .progress-item { text-align: center; }
    .progress-value { font-size: 22px; font-weight: 800; }
    .progress-label { font-size: 11px; color: #666; }
    .detail-panel { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-top: 10px; }
    .equipo-info { background: #f5f5f5; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
    .equipo-info strong { color: #1a237e; }
    .stButton>button { border-radius: 6px; font-weight: 600; font-size: 12px !important; padding: 4px 12px !important; }
    .prioridad-critico { border-left: 4px solid #dc3545 !important; background: linear-gradient(90deg, #fff5f5 0%, #ffffff 100%) !important; }
    .prioridad-secundario { border-left: 4px solid #ffc107 !important; background: linear-gradient(90deg, #fffbea 0%, #ffffff 100%) !important; }
    .prioridad-estandar { border-left: 4px solid #28a745 !important; background: linear-gradient(90deg, #f0fff4 0%, #ffffff 100%) !important; }
    .tabla-header { display: grid; grid-template-columns: 70px 45px 1fr 90px 110px; gap: 6px; padding: 8px 10px; background: #f8f9fa; border-bottom: 2px solid #dee2e6; font-weight: 700; font-size: 10px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; align-items: center; margin-bottom: 6px; }
    .tabla-fila { display: grid; grid-template-columns: 70px 45px 1fr 90px 110px; gap: 6px; padding: 8px 10px; background: white; border: 1px solid #e9ecef; border-radius: 6px; align-items: center; font-size: 12px; margin-bottom: 6px; transition: all 0.2s; }
    .tabla-fila:hover { background: #f8f9fa; border-color: #adb5bd; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .tabla-fila .col-id { font-family: monospace; font-size: 11px; color: #495057; }
    .tabla-fila .col-esp { font-weight: 600; font-size: 11px; color: #1a237e; }
    .tabla-fila .col-desc { font-size: 11px; color: #212529; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tabla-fila .col-estado { text-align: center; }
    .tabla-fila .col-tec { font-size: 10px; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tabla-fila-asig { display: grid; grid-template-columns: 1fr auto; gap: 10px; padding: 8px 10px; background: white; border: 1px solid #e9ecef; border-radius: 6px; align-items: center; margin-bottom: 4px; }
    .asig-info { min-width: 0; overflow: hidden; }
    .asig-ot { font-size: 12px; color: #212529; margin-bottom: 2px; }
    .asig-esp { color: #1a237e; font-weight: 600; font-size: 11px; }
    .asig-equipo { font-size: 10px; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .asig-estado { text-align: right; flex-shrink: 0; }
    .perfil-card { background: white; border-radius: 16px; padding: 24px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; border: 3px solid transparent; }
    .perfil-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
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
    /* === ESTILOS NUEVOS PARA FILTRO POR MAQUINA (NODO) === */
    .maquina-card { background: white; border-radius: 12px; padding: 14px 16px; margin-bottom: 8px; border: 2px solid #e9ecef; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: space-between; }
    .maquina-card:hover { border-color: #1a237e; box-shadow: 0 2px 8px rgba(26,35,158,0.15); }
    .maquina-card.activa { border-color: #1a237e; background: linear-gradient(135deg, #e8eaf6 0%, #ffffff 100%); }
    .maquina-nombre { font-size: 15px; font-weight: 700; color: #1a237e; }
    .maquina-badge { background: #1a237e; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
    .filtro-nodo-label { font-size: 12px; color: #666; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; }
    .contador-maquinas { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin: 10px 0; }
    .contador-maquina { background: white; border-radius: 8px; padding: 8px 12px; text-align: center; border: 1px solid #e9ecef; min-width: 80px; }
    .contador-maquina-valor { font-size: 18px; font-weight: 800; color: #1a237e; }
    .contador-maquina-label { font-size: 10px; color: #666; }
    .nodo-badge-mini { background: #e8eaf6; color: #1a237e; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: monospace; }
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
def cargar_excel_mantenimiento():
    try:
        df = cargar_ordenes_supabase()
        return df
    except Exception as e:
        st.error(f"Error al cargar ordenes: {e}")
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
    if st.button("CERRAR SESION", use_container_width=True, type="secondary", key="btn_cerrar_sesion"):
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

# ==================== FUNCIONES NUEVAS PARA FILTRO POR NODO/MAQUINA ====================
def extraer_maquina_nodo(nodo):
    """Extrae el codigo de maquina del nodo (ej: PRETF45-DE01 -> PRETF45)"""
    if pd.isna(nodo) or str(nodo).strip() == "":
        return "SIN_NODO"
    partes = str(nodo).split("-")
    return partes[0] if len(partes) > 0 else str(nodo)

def extraer_subsistema_nodo(nodo):
    """Extrae el subsistema del nodo (ej: PRETF45-DE01 -> DE01)"""
    if pd.isna(nodo) or str(nodo).strip() == "":
        return "SIN_CODIGO"
    partes = str(nodo).split("-")
    return partes[1] if len(partes) > 1 else "SIN_CODIGO"

def obtener_maquinas_desde_nodo(df):
    """Obtiene lista unica de maquinas extraidas de la columna Nodo"""
    if df.empty or "Nodo" not in df.columns:
        return ["Todas"]
    try:
        maquinas = df["Nodo"].dropna().apply(extraer_maquina_nodo).unique().tolist()
        maquinas = [m for m in maquinas if str(m).strip() and str(m).strip() != "SIN_NODO"]
        return ["Todas"] + sorted(maquinas)
    except Exception:
        return ["Todas"]

def obtener_subsistemas_desde_nodo(df, maquina_filtro="Todas"):
    """Obtiene lista de subsistemas filtrados por maquina"""
    if df.empty or "Nodo" not in df.columns:
        return ["Todos"]
    try:
        df_temp = df.copy()
        if maquina_filtro != "Todas":
            df_temp = df_temp[df_temp["Nodo"].apply(extraer_maquina_nodo) == maquina_filtro]
        subsistemas = df_temp["Nodo"].dropna().apply(extraer_subsistema_nodo).unique().tolist()
        subsistemas = [s for s in subsistemas if str(s).strip() and str(s).strip() != "SIN_CODIGO"]
        return ["Todos"] + sorted(subsistemas)
    except Exception:
        return ["Todos"]

def contar_por_maquina(df):
    """Cuenta ordenes por maquina para mostrar en tarjetas"""
    if df.empty or "Nodo" not in df.columns:
        return {}
    try:
        maquinas = df["Nodo"].dropna().apply(extraer_maquina_nodo)
        return maquinas.value_counts().to_dict()
    except Exception:
        return {}

def contar_por_subsistema(df, maquina_filtro="Todas"):
    """Cuenta ordenes por subsistema"""
    if df.empty or "Nodo" not in df.columns:
        return {}
    try:
        df_temp = df.copy()
        if maquina_filtro != "Todas":
            df_temp = df_temp[df_temp["Nodo"].apply(extraer_maquina_nodo) == maquina_filtro]
        subsistemas = df_temp["Nodo"].dropna().apply(extraer_subsistema_nodo)
        return subsistemas.value_counts().to_dict()
    except Exception:
        return {}


# ==================== INICIALIZAR ESTADO ====================
if "perfil" not in st.session_state: st.session_state.perfil = None
if "pagina" not in st.session_state: st.session_state.pagina = "login"
if "orden_seleccionada" not in st.session_state: st.session_state.orden_seleccionada = None
if "df_mantenimientos" not in st.session_state: st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
if "filtro_especialidad" not in st.session_state: st.session_state.filtro_especialidad = "Todas"
if "filtro_maquina" not in st.session_state: st.session_state.filtro_maquina = "Todas"
if "filtro_esp_asig" not in st.session_state: st.session_state.filtro_esp_asig = "Todas"
if "filtro_maq_asig" not in st.session_state: st.session_state.filtro_maq_asig = "Todas"
if "filtro_estado_asig" not in st.session_state: st.session_state.filtro_estado_asig = "Todos"
if "busqueda" not in st.session_state: st.session_state.busqueda = ""
if "mostrar_envio_correo" not in st.session_state: st.session_state.mostrar_envio_correo = False
# === NUEVOS ESTADOS PARA FILTRO POR NODO ===
if "filtro_maquina_nodo" not in st.session_state: st.session_state.filtro_maquina_nodo = "Todas"
if "filtro_subsistema_nodo" not in st.session_state: st.session_state.filtro_subsistema_nodo = "Todos"


# ==================== PANTALLA DE LOGIN ====================
def pantalla_login():
    st.markdown('<div class="tablet-header">App Tablet Mtto Preventivo</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <div style="font-size: 14px; color: #666; margin-bottom: 20px;">Selecciona tu perfil para continuar</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="perfil-card perfil-admin" style="text-align: center; padding: 20px;">
            <div class="perfil-icon">&#128100;</div>
            <div class="perfil-titulo" style="color: #dc3545;">ADMIN</div>
            <div class="perfil-desc">Asigna tecnicos<br>Cambia prioridades<br>Verifica ejecuciones<br>Ve todo el sistema</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("ENTRAR COMO ADMIN", use_container_width=True, type="primary", key="login_admin"):
            st.session_state.perfil = "admin"
            st.session_state.pagina = "home"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="perfil-card perfil-tecnico" style="text-align: center; padding: 20px;">
            <div class="perfil-icon">&#128295;</div>
            <div class="perfil-titulo" style="color: #28a745;">TECNICO</div>
            <div class="perfil-desc">Ve sus ordenes<br>Ejecuta actividades<br>Comenta y reporta</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("ENTRAR COMO TECNICO", use_container_width=True, type="primary", key="login_tecnico"):
            st.session_state.perfil = "tecnico"
            st.session_state.pagina = "home"
            st.rerun()

# ==================== PANTALLA DE INICIO (HOME) ====================
def pantalla_home():
    perfil = st.session_state.perfil
    df = st.session_state.df_mantenimientos

    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>App Tablet Mtto</span>
        <span style="font-size: 12px; opacity: 0.8;">{'&#128100; Admin' if perfil == 'admin' else '&#128295; Tecnico' if perfil == 'tecnico' else '&#10003; Supervisor'}</span>
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

    # === NUEVO: CONTADORES POR MAQUINA (NODO) ===
    if "Nodo" in df.columns:
        conteo_maquinas = contar_por_maquina(df)
        if conteo_maquinas:
            st.markdown("<div style='text-align: center; margin: 10px 0 6px 0; font-weight: 600; color: #666; font-size: 13px;'>Ordenes por Maquina</div>", unsafe_allow_html=True)
            cols = st.columns(min(len(conteo_maquinas), 4))
            for i, (maq, cant) in enumerate(conteo_maquinas.items()):
                with cols[i % 4]:
                    st.markdown(f"""
                    <div class="contador-maquina">
                        <div class="contador-maquina-valor">{cant}</div>
                        <div class="contador-maquina-label">{maq}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; margin: 15px 0 10px 0; font-weight: 600; color: #666;'>Filtrar por Especialidad</div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1,1,1,1])
    with col1:
        if st.button("TODAS", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "Todas" else "secondary", key="btn_filtro_todas"):
            st.session_state.filtro_especialidad = "Todas"; st.rerun()
    with col2:
        if st.button("ELE", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "ELE" else "secondary", key="btn_filtro_ele"):
            st.session_state.filtro_especialidad = "ELE"; st.rerun()
    with col3:
        if st.button("MEC", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "MEC" else "secondary", key="btn_filtro_mec"):
            st.session_state.filtro_especialidad = "MEC"; st.rerun()
    with col4:
        if st.button("LIMPIAR", use_container_width=True, key="btn_filtro_limpiar"):
            st.session_state.filtro_especialidad = "Todas"
            st.session_state.filtro_maquina = "Todas"
            st.session_state.filtro_maquina_nodo = "Todas"
            st.session_state.filtro_subsistema_nodo = "Todos"
            st.session_state.busqueda = ""
            st.rerun()

    # === FILTRO POR UBICACION (EXISTENTE) ===
    maquinas = obtener_maquinas_disponibles(df)
    index_sel = 0
    if st.session_state.filtro_maquina in maquinas: index_sel = maquinas.index(st.session_state.filtro_maquina)
    maquina_sel = st.selectbox("Maquina / Ubicacion", maquinas, index=index_sel, key="sel_maquina_home")
    st.session_state.filtro_maquina = maquina_sel

    # === NUEVO: FILTRO POR NODO/MAQUINA ===
    if "Nodo" in df.columns:
        st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid #dee2e6;'>", unsafe_allow_html=True)

        col_nodo1, col_nodo2 = st.columns(2)
        with col_nodo1:
            maquinas_nodo = obtener_maquinas_desde_nodo(df)
            idx_maq_nodo = maquinas_nodo.index(st.session_state.filtro_maquina_nodo) if st.session_state.filtro_maquina_nodo in maquinas_nodo else 0
            maquina_nodo_sel = st.selectbox("Filtrar por Maquina (Nodo)", maquinas_nodo, index=idx_maq_nodo, key="sel_maquina_nodo")
            if maquina_nodo_sel != st.session_state.filtro_maquina_nodo:
                st.session_state.filtro_maquina_nodo = maquina_nodo_sel
                st.session_state.filtro_subsistema_nodo = "Todos"
                st.rerun()
        with col_nodo2:
            subsistemas = obtener_subsistemas_desde_nodo(df, st.session_state.filtro_maquina_nodo)
            idx_sub = subsistemas.index(st.session_state.filtro_subsistema_nodo) if st.session_state.filtro_subsistema_nodo in subsistemas else 0
            subsistema_sel = st.selectbox("Subsistema (Codigo)", subsistemas, index=idx_sub, key="sel_subsistema_nodo")
            st.session_state.filtro_subsistema_nodo = subsistema_sel

        # Mostrar contadores de subsistemas si hay maquina seleccionada
        if st.session_state.filtro_maquina_nodo != "Todas":
            conteo_subs = contar_por_subsistema(df, st.session_state.filtro_maquina_nodo)
            if conteo_subs:
                st.markdown("<div style='font-size: 11px; color: #666; margin-bottom: 6px;'>Distribucion por subsistema:</div>", unsafe_allow_html=True)
                sub_cols = st.columns(min(len(conteo_subs), 6))
                for i, (sub, cant) in enumerate(conteo_subs.items()):
                    with sub_cols[i % 6]:
                        st.markdown(f"<div style='text-align: center;'><span class='nodo-badge-mini'>{sub}</span><br><span style='font-size: 11px; font-weight: 700; color: #1a237e;'>{cant}</span></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if perfil == "admin":
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        with col_btn1:
            if st.button("VER ORDENES PREVENTIVAS", use_container_width=True, type="primary", key="btn_ver_ordenes"):
                st.session_state.pagina = "ordenes"; st.rerun()
        with col_btn2:
            if st.button("ASIGNACION DE TECNICOS", use_container_width=True, type="primary", key="btn_asignacion"):
                st.session_state.pagina = "asignacion"; st.rerun()
        with col_btn3:
            if st.button("VER ORDENES EJECUTADAS", use_container_width=True, type="primary", key="btn_ver_ejecutadas"):
                st.session_state.pagina = "verificar"; st.rerun()
        with col_btn4:
            if st.button("ENVIAR CORREO", use_container_width=True, type="primary", key="btn_abrir_correo"):
                st.session_state.mostrar_envio_correo = True
                st.rerun()
    elif perfil == "tecnico":
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("MIS ORDENES ASIGNADAS", use_container_width=True, type="primary", key="btn_mis_ordenes"):
                st.session_state.pagina = "mis_ordenes"; st.rerun()
        with col_btn2:
            if st.button("VER TODAS LAS ORDENES", use_container_width=True, type="secondary", key="btn_ver_todas"):
                st.session_state.pagina = "ordenes"; st.rerun()

    # PANEL DE ENVIO DE CORREO
    if perfil == "admin" and st.session_state.mostrar_envio_correo:
        st.divider()
        st.subheader("Enviar Resumen por Correo")

        df_envio = df.copy()
        if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_envio.columns:
            df_envio = df_envio[df_envio["Especialidad"] == st.session_state.filtro_especialidad]
        if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_envio.columns:
            df_envio = df_envio[df_envio["Ubicacion"] == st.session_state.filtro_maquina]
        # Aplicar filtro por nodo al envio de correo
        if "Nodo" in df_envio.columns and st.session_state.filtro_maquina_nodo != "Todas":
            df_envio = df_envio[df_envio["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
        if "Nodo" in df_envio.columns and st.session_state.filtro_subsistema_nodo != "Todos":
            df_envio = df_envio[df_envio["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]

        pct_ejec, pct_pdte, pct_verif = calcular_progreso(df_envio)

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1: st.metric("Ejecutadas", f"{pct_ejec}%")
        with col_stat2: st.metric("Pendientes", f"{pct_pdte}%")
        with col_stat3: st.metric("Verificar", f"{pct_verif}%")

        st.write(f"**Total de ordenes a enviar:** {len(df_envio)}")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cuenta = st.radio("Cuenta de envio:", [
                "mantobogota@gmail.com",
                "supermantobogota@gmail.com"
            ], key="radio_cuenta_correo")


        with col_c2:
            area = st.text_input("Area / Proyecto", value="INY4 MEC", key="txt_area_correo")

        asunto = st.text_input("Asunto del correo", value=f"Ordenes preventivas {area}", key="txt_asunto_correo")

        destinatarios_text = st.text_area(
            "Destinatarios:",
            value="\n".join(DESTINATARIOS_DEFAULT),
            disabled=True,
            key="txt_destinatarios"
        )

        col_env1, col_env2 = st.columns(2)
        with col_env1:
            if st.button("ENVIAR CORREO AHORA", use_container_width=True, type="primary", key="btn_enviar_correo"):
                if len(df_envio) == 0:
                    st.error("No hay ordenes para enviar con el filtro actual")
                else:
                    with st.spinner("Enviando correo..."):
                        exito, mensaje = enviar_correo_preventivo(
                            df=df_envio,
                            destinatarios=DESTINATARIOS_DEFAULT,
                            asunto=asunto,
                            area_mecanica=area,
                            email_remitente=cuenta
                        )
                    if exito:
                        st.success(mensaje)
                        st.session_state.mostrar_envio_correo = False
                    else:
                        st.error(mensaje)

        with col_env2:
            if st.button("CANCELAR", use_container_width=True, type="secondary", key="btn_cancelar_correo"):
                st.session_state.mostrar_envio_correo = False
                st.rerun()

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

    busqueda = st.text_input("Buscar ID OT, equipo o descripcion...", value=st.session_state.busqueda, placeholder="Escribe para buscar...", key="txt_busqueda_ordenes")
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
    # === NUEVO: Aplicar filtro por Nodo/Maquina ===
    if "Nodo" in df_filtrado.columns and st.session_state.filtro_maquina_nodo != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
    if "Nodo" in df_filtrado.columns and st.session_state.filtro_subsistema_nodo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]
    if busqueda:
        busqueda_lower = busqueda.lower()
        mask = pd.Series([False] * len(df_filtrado), index=df_filtrado.index)
        if "Equipo" in df_filtrado.columns: mask |= df_filtrado["Equipo"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "Ubicacion" in df_filtrado.columns: mask |= df_filtrado["Ubicacion"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "ID OT" in df_filtrado.columns: mask |= df_filtrado["ID OT"].astype(str).str.contains(busqueda_lower, na=False)
        if "Descripcion de procedimiento" in df_filtrado.columns: mask |= df_filtrado["Descripcion de procedimiento"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "Nodo" in df_filtrado.columns: mask |= df_filtrado["Nodo"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
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
        # === NUEVO: Mostrar nodo si existe ===
        nodo = str(row.get("Nodo", ""))
        nodo_html = f"<span class='nodo-badge-mini' style='margin-left:4px;'>{nodo}</span>" if nodo and nodo != "nan" else ""

        st.markdown(f"""
        <div class="tabla-fila {clase_prioridad}">
            <div class="col-id"><strong>{id_ot}</strong>{nodo_html}</div>
            <div class="col-esp">{tipo}</div>
            <div class="col-desc" title="{descripcion}">{desc_corta}</div>
            <div class="col-estado"><span class="estado-badge {estado_clase}">{estado}</span></div>
            <div class="col-tec">{tecnico}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button(f"Ver detalle", key=f"btn_ver_{idx}", use_container_width=True):
            st.session_state.orden_seleccionada = idx; st.session_state.pagina = "detalle"; st.rerun()

# ==================== PANTALLA MIS ORDENES (TECNICO) ====================
def pantalla_mis_ordenes():
    df = st.session_state.df_mantenimientos
    perfil = st.session_state.perfil
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Mis Ordenes Asignadas</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("mis_ordenes_top")

    df_mias = df.copy()
    if "Tecnico_Asignado" in df_mias.columns:
        df_mias = df_mias[df_mias["Tecnico_Asignado"].notna() & (df_mias["Tecnico_Asignado"] != "")]
        if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_mias.columns:
            df_mias = df_mias[df_mias["Especialidad"] == st.session_state.filtro_especialidad]
        if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_mias.columns:
            df_mias = df_mias[df_mias["Ubicacion"] == st.session_state.filtro_maquina]
        # === NUEVO: Aplicar filtro por Nodo ===
        if "Nodo" in df_mias.columns and st.session_state.filtro_maquina_nodo != "Todas":
            df_mias = df_mias[df_mias["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
        if "Nodo" in df_mias.columns and st.session_state.filtro_subsistema_nodo != "Todos":
            df_mias = df_mias[df_mias["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]
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
        nodo = str(row.get("Nodo", ""))
        nodo_html = f"<span class='nodo-badge-mini' style='margin-left:4px;'>{nodo}</span>" if nodo and nodo != "nan" else ""

        st.markdown(f"""
        <div class="tabla-fila {clase_prioridad}">
            <div class="col-id"><strong>{id_ot}</strong>{nodo_html}</div>
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
            if estado == "Pendiente" and st.button(f"Ejecutar", key=f"btn_ejec_{idx}", use_container_width=True, type="primary"):
                st.session_state.orden_seleccionada = idx; st.session_state.pagina = "ejecutar"; st.rerun()

# ==================== PANTALLA EJECUTAR ORDEN (TECNICO) ====================
def pantalla_ejecutar():
    df = st.session_state.df_mantenimientos
    idx = st.session_state.orden_seleccionada
    if idx is None or idx not in df.index:
        st.session_state.pagina = "mis_ordenes"; st.rerun(); return

    row = df.loc[idx]
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Ejecutar OT {row.get('ID OT', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("Volver", use_container_width=True, type="secondary", key="ejec_volver"):
            st.session_state.pagina = "mis_ordenes"; st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key="ejec_inicio"):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()

    # === NUEVO: Mostrar Nodo en detalle ===
    nodo_info = f"<strong>Nodo:</strong> {row.get('Nodo', 'N/A')}<br>" if 'Nodo' in row else ""

    st.markdown(f"""
    <div class="detail-panel">
        <div class="equipo-info">
            {nodo_info}
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

    if st.button("MARCAR COMO EJECUTADO", use_container_width=True, type="primary", key="btn_marcar_ejecutado"):
        df.at[idx, "Estado"] = "Ejecutado"
        df.at[idx, "Comentarios"] = nuevo_comentario
        df.at[idx, "Actividades_Hechas"] = actividades
        df.at[idx, "Fecha_Ejecucion"] = datetime.now().strftime("%Y-%m-%d")
        df.at[idx, "Hora_Inicio"] = hora_inicio.strftime("%H:%M")
        df.at[idx, "Hora_Fin"] = hora_fin.strftime("%H:%M")
        if guardar_asignaciones_supabase(df):
            st.success("Orden marcada como EJECUTADA y guardada en Supabase")
            st.balloons()
            st.session_state.pagina = "mis_ordenes"
            st.rerun()
        else:
            st.error("Error al guardar en Supabase. Intenta de nuevo.")

# ==================== PANTALLA DETALLE TECNICO ====================
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
        if st.button("Volver", use_container_width=True, type="secondary", key="dettec_volver"):
            st.session_state.pagina = "mis_ordenes"; st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key="dettec_inicio"):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()

    prioridad = str(row.get("Prioridad_Actividad", ""))
    info_prioridad = obtener_color_prioridad(prioridad)
    if prioridad:
        st.info(f"**Prioridad: {info_prioridad['label']}** — {info_prioridad['desc']}")

    # === NUEVO: Mostrar Nodo ===
    nodo_info = f"<strong>Nodo:</strong> {row.get('Nodo', 'N/A')}<br>" if 'Nodo' in row else ""

    st.markdown(f"""
    <div class="detail-panel">
        <div class="equipo-info">
            {nodo_info}
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


# ==================== PANTALLA DETALLE (ADMIN / SUPERVISOR) ====================
def pantalla_detalle():
    df = st.session_state.df_mantenimientos
    idx = st.session_state.orden_seleccionada
    if idx is None or idx not in df.index:
        st.session_state.pagina = "ordenes"; st.rerun(); return

    row = df.loc[idx]
    perfil = st.session_state.perfil
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Detalle OT {row.get('ID OT', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("Volver", use_container_width=True, type="secondary", key="det_volver"):
            st.session_state.pagina = "ordenes"; st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key="det_inicio"):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()

    prioridad = str(row.get("Prioridad_Actividad", ""))
    info_prioridad = obtener_color_prioridad(prioridad)
    if prioridad:
        st.info(f"**Prioridad: {info_prioridad['label']}** — {info_prioridad['desc']}")

    # === NUEVO: Mostrar Nodo en panel de detalle ===
    nodo_info = f"<strong>Nodo:</strong> {row.get('Nodo', 'N/A')}<br>" if 'Nodo' in row else ""

    st.markdown(f"""
    <div class="detail-panel">
        <div class="equipo-info">
            {nodo_info}
            <strong>Equipo:</strong> {row.get('Equipo', '')}<br>
            <strong>Ubicacion:</strong> {row.get('Ubicacion', '')}<br>
            <strong>Especialidad:</strong> {row.get('Especialidad', '')}<br>
            <strong>Estado:</strong> {row.get('Estado', 'Pendiente')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Descripcion del Procedimiento")
    st.write(row.get("Descripcion de procedimiento", "Sin descripcion"))

    st.divider()
    st.subheader("Editar Orden")

    especialidad = str(row.get("Especialidad", ""))
    tecnicos = obtener_tecnicos_por_especialidad(especialidad)
    tecnicos = [""] + tecnicos

    tecnico_actual = str(row.get("Tecnico_Asignado", ""))
    try:
        idx_tec = tecnicos.index(tecnico_actual) if tecnico_actual in tecnicos else 0
    except:
        idx_tec = 0

    col1, col2 = st.columns(2)
    with col1:
        nuevo_tecnico = st.selectbox("Tecnico Asignado", tecnicos, index=idx_tec, key="det_tecnico")
    with col2:
        estados = ["Pendiente", "Ejecutado", "Verificado", "Cerrada"]
        estado_actual = str(row.get("Estado", "Pendiente"))
        idx_est = estados.index(estado_actual) if estado_actual in estados else 0
        nuevo_estado = st.selectbox("Estado", estados, index=idx_est, key="det_estado")

    col3, col4 = st.columns(2)
    with col3:
        prioridades = ["", "Rojo", "Amarillo", "Verde"]
        idx_pri = prioridades.index(prioridad) if prioridad in prioridades else 0
        nueva_prioridad = st.selectbox("Prioridad", prioridades, index=idx_pri, key="det_prioridad")
    with col4:
        fecha_ejec = st.date_input("Fecha Ejecucion", value=datetime.now(), key="det_fecha")

    col5, col6 = st.columns(2)
    with col5:
        hora_inicio = st.time_input("Hora Inicio", value=datetime.strptime("08:00", "%H:%M").time(), key="det_hini")
    with col6:
        hora_fin = st.time_input("Hora Fin", value=datetime.strptime("17:00", "%H:%M").time(), key="det_hfin")

    comentarios = st.text_area("Comentarios", value=str(row.get("Comentarios", "")), key="det_comentarios")
    actividades = st.text_area("Actividades Hechas", value=str(row.get("Actividades_Hechas", "")), key="det_actividades")

    if st.button("GUARDAR CAMBIOS", use_container_width=True, type="primary", key="det_guardar"):
        id_ot = str(row.get("ID OT", ""))
        df.at[idx, "Tecnico_Asignado"] = nuevo_tecnico
        df.at[idx, "Estado"] = nuevo_estado
        df.at[idx, "Prioridad_Actividad"] = nueva_prioridad
        df.at[idx, "Comentarios"] = comentarios
        df.at[idx, "Actividades_Hechas"] = actividades
        df.at[idx, "Fecha_Ejecucion"] = fecha_ejec.strftime("%Y-%m-%d")
        df.at[idx, "Hora_Inicio"] = hora_inicio.strftime("%H:%M")
        df.at[idx, "Hora_Fin"] = hora_fin.strftime("%H:%M")

        datos = {
            "Tecnico_Asignado": nuevo_tecnico,
            "Estado": nuevo_estado,
            "Prioridad_Actividad": nueva_prioridad,
            "Comentarios": comentarios,
            "Actividades_Hechas": actividades,
            "Fecha_Ejecucion": fecha_ejec.strftime("%Y-%m-%d"),
            "Hora_Inicio": hora_inicio.strftime("%H:%M"),
            "Hora_Fin": hora_fin.strftime("%H:%M")
        }
        if guardar_orden_supabase(id_ot, datos):
            st.success("Cambios guardados exitosamente en Supabase")
            st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
            st.rerun()
        else:
            st.error("Error al guardar en Supabase")

    if perfil in ["admin", "supervisor"] and nuevo_estado == "Ejecutado":
        if st.button("VERIFICAR ORDEN", use_container_width=True, type="primary", key="det_verificar"):
            id_ot = str(row.get("ID OT", ""))
            df.at[idx, "Estado"] = "Verificado"
            if actualizar_orden_supabase(id_ot, "Estado", "Verificado"):
                st.success("Orden VERIFICADA")
                st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                st.rerun()
            else:
                st.error("Error al verificar")

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

    # === NUEVO: Filtro por Nodo en asignacion ===
    if "Nodo" in df.columns:
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            maquinas_nodo = obtener_maquinas_desde_nodo(df)
            idx_mn = maquinas_nodo.index(st.session_state.filtro_maquina_nodo) if st.session_state.filtro_maquina_nodo in maquinas_nodo else 0
            filtro_maq_nodo = st.selectbox("Maquina (Nodo)", maquinas_nodo, index=idx_mn, key="asig_maq_nodo")
            st.session_state.filtro_maquina_nodo = filtro_maq_nodo
        with col_n2:
            subsistemas = obtener_subsistemas_desde_nodo(df, st.session_state.filtro_maquina_nodo)
            idx_sn = subsistemas.index(st.session_state.filtro_subsistema_nodo) if st.session_state.filtro_subsistema_nodo in subsistemas else 0
            filtro_sub_nodo = st.selectbox("Subsistema", subsistemas, index=idx_sn, key="asig_sub_nodo")
            st.session_state.filtro_subsistema_nodo = filtro_sub_nodo

    df_asig = df.copy()
    if filtro_esp != "Todas" and "Especialidad" in df_asig.columns:
        df_asig = df_asig[df_asig["Especialidad"] == filtro_esp]
    if filtro_maq != "Todas" and "Ubicacion" in df_asig.columns:
        df_asig = df_asig[df_asig["Ubicacion"] == filtro_maq]
    # === NUEVO: Aplicar filtro nodo en asignacion ===
    if "Nodo" in df_asig.columns and st.session_state.filtro_maquina_nodo != "Todas":
        df_asig = df_asig[df_asig["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
    if "Nodo" in df_asig.columns and st.session_state.filtro_subsistema_nodo != "Todos":
        df_asig = df_asig[df_asig["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]

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
        # === NUEVO: Mostrar nodo en asignacion ===
        nodo = str(row.get("Nodo", ""))
        nodo_badge = f"<span class='nodo-badge-mini'>{nodo}</span>" if nodo and nodo != "nan" else ""

        with st.container():
            st.markdown(f"""
            <div class="tabla-fila-asig {clase_prioridad}">
                <div class="asig-info">
                    <div class="asig-ot"><strong>OT {id_ot}</strong> {nodo_badge} | <span class="asig-esp">{tipo}</span></div>
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
        # === NUEVO: Mostrar nodo en verificar ===
        nodo = str(row.get("Nodo", ""))
        nodo_badge = f"<span class='nodo-badge-mini'>{nodo}</span>" if nodo and nodo != "nan" else ""

        st.markdown(f"""
        <div class="detail-panel" style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong>OT {id_ot}</strong> {nodo_badge}
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
