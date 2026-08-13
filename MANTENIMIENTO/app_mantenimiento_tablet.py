import streamlit as st
import pandas as pd
from datetime import datetime, time
from supabase import create_client
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import io
import hashlib

# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN SUPABASE
# ═══════════════════════════════════════════════════════════════════════
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://cpazmoebqbsrahviifvp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_KEY:
    st.error("SUPABASE_KEY no configurada.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DESTINATARIOS_DEFAULT = [
    "mantobogota@gmail.com",
    "supermantobogota@gmail.com"
]

# ═══════════════════════════════════════════════════════════════════════
#  INICIALIZAR SESSION STATE
# ═══════════════════════════════════════════════════════════════════════
def init_session_state():
    defaults = {
        "pagina": "login",
        "perfil": None,
        "admin_autenticado": False,
        "mostrar_login_admin": False,
        "orden_seleccionada": None,
        "busqueda": "",
        "tecnico_seleccionado": None,
        "filtro_especialidad": "Todas",
        "filtro_estado": "Todos",
        "filtro_maquina": "Todas",
        "filtro_maquina_nodo": "Todas",
        "filtro_subsistema_nodo": "Todos",
        "filtro_estado_asig": "Todos",
        "df_mantenimientos": pd.DataFrame(),
        "asig_rapida_msg": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# ═══════════════════════════════════════════════════════════════════════
#  FUNCIONES UTILITARIAS
# ═══════════════════════════════════════════════════════════════════════
def limpiar(valor, default=""):
    if valor is None:
        return default
    try:
        if pd.isna(valor):
            return default
    except:
        pass
    s = str(valor).strip()
    if s.lower() in ("nan", "none", "nat", "null"):
        return default
    return s

def gen_key(prefix, suffix=""):
    """Genera una key única para widgets de Streamlit."""
    import time
    return f"{prefix}_{suffix}_{int(time.time()*1000)}" if suffix else f"{prefix}_{int(time.time()*1000)}"

def get_row_by_internal_id(df, internal_id):
    """Busca una fila por su ID interno (columna 'ID')."""
    if df.empty or "ID" not in df.columns:
        return None, None
    mask = df["ID"].astype(str) == str(internal_id)
    if mask.any():
        idx = df[mask].index[0]
        return idx, df.loc[idx]
    return None, None

def extraer_maquina_nodo(nodo):
    """Extrae la máquina principal del código de nodo. Ej: 'M1-SUB1' -> 'M1'"""
    if pd.isna(nodo):
        return "Sin Nodo"
    s = str(nodo).strip()
    if "-" in s:
        return s.split("-")[0]
    return s

def extraer_subsistema_nodo(nodo):
    """Extrae el subsistema del código de nodo. Ej: 'M1-SUB1' -> 'SUB1'"""
    if pd.isna(nodo):
        return "Sin Subsistema"
    s = str(nodo).strip()
    if "-" in s:
        parts = s.split("-")
        return "-".join(parts[1:]) if len(parts) > 1 else s
    return s

def obtener_maquinas_disponibles(df):
    """Devuelve lista de máquinas únicas ordenadas."""
    if df.empty or "Ubicacion" not in df.columns:
        return ["Todas"]
    maqs = df["Ubicacion"].dropna().unique().tolist()
    maqs = sorted([str(m).strip() for m in maqs if str(m).strip()])
    return ["Todas"] + maqs

def obtener_tecnicos_con_carga(df, especialidad="Todas"):
    """Devuelve lista de técnicos con conteo de órdenes asignadas."""
    tecnicos = []
    if especialidad == "ELE" or especialidad == "Todas":
        for t in TECNICOS_ELE:
            tecnicos.append({"nombre": t, "especialidad": "ELE"})
    if especialidad == "MEC" or especialidad == "Todas":
        for t in TECNICOS_MEC:
            tecnicos.append({"nombre": t, "especialidad": "MEC"})
    if not df.empty and "Tecnico_Asignado" in df.columns:
        for t in tecnicos:
            t["carga"] = len(df[df["Tecnico_Asignado"] == t["nombre"]])
    else:
        for t in tecnicos:
            t["carga"] = 0
    return tecnicos

def boton_volver_inicio(origen=""):
    """Muestra un botón para volver a la pantalla de inicio."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("VOLVER AL INICIO", use_container_width=True, type="secondary",
                     key=gen_key("volver_inicio", origen)):
            st.session_state.pagina = "home"
            st.session_state.orden_seleccionada = None
            st.session_state.busqueda = ""
            st.rerun()

def cargar_excel_mantenimiento():
    """Alias: carga las órdenes desde Supabase."""
    return cargar_ordenes_supabase()

def recargar_datos():
    """Alias: recarga las órdenes desde Supabase."""
    return cargar_ordenes_supabase()

# ═══════════════════════════════════════════════════════════════════════
#  FUNCIONES DE EMAIL
# ═══════════════════════════════════════════════════════════════════════
def enviar_correo_preventivo(df, destinatarios, asunto, area_mecanica="INY4 MEC", email_remitente=None):
    if email_remitente == "supermantobogota@gmail.com":
        email_user = st.secrets.get("EMAIL_USER_2", "")
        email_pass = st.secrets.get("EMAIL_PASS_2", "")
    else:
        email_user = st.secrets.get("EMAIL_USER", "")
        email_pass = st.secrets.get("EMAIL_PASS", "")
    if not email_user or not email_pass:
        return False, "Credenciales no configuradas"
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
    cuerpo_html = f"""<html><body style="font-family: Arial, sans-serif; color: #333;">
        <p style="font-size: 16px; font-weight: bold;">Preventivo</p>
        <p style="font-size: 14px;">{area_mecanica}</p>
        <p style="font-size: 14px;">Ejecutadas {ejecutadas_pct}%</p>
        <p style="font-size: 14px;">Pendientes {pendientes_pct}%</p>
        <p style="font-size: 14px;">Verificar {verificar_pct}%</p>
        <br><p style="font-size: 14px;">Comentario:</p></body></html>"""
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

# ═══════════════════════════════════════════════════════════════════════
#  FUNCIONES SUPABASE
# ═══════════════════════════════════════════════════════════════════════
def cargar_ordenes_supabase():
    try:
        response = supabase.table("ordenes_trabajo").select("*").order("id", desc=False).execute()
        data = response.data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        columnas_mapeo = {}
        for col in df.columns:
            if col == "id": columnas_mapeo[col] = "ID"
            elif col == "id_ot": columnas_mapeo[col] = "ID OT"
            elif col == "actividades": columnas_mapeo[col] = "Actividades"
            elif col == "procedimiento": columnas_mapeo[col] = "Procedimiento"
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
            "Hora_Fin": "", "Prioridad_Actividad": "", "ID OT": "", "Procedimiento": ""
        }
        for col, default in columnas_default.items():
            if col not in df.columns:
                df[col] = default
        return df
    except Exception as e:
        st.error(f"Error cargando ordenes: {e}")
        return pd.DataFrame()

def actualizar_campos_supabase(id_interno, datos_nuevos, datos_originales=None):
    try:
        datos_a_enviar = {}
        for key, value in datos_nuevos.items():
            key_snake = mapear_campo_supabase(key)
            if pd.isna(value):
                valor_nuevo_norm = None
            elif isinstance(value, str) and value.strip() == "":
                valor_nuevo_norm = None
            else:
                valor_nuevo_norm = value
            if datos_originales is not None:
                valor_original = datos_originales.get(key, datos_originales.get(key_snake, ""))
                if pd.isna(valor_original) or (isinstance(valor_original, str) and valor_original.strip() == ""):
                    valor_orig_norm = None
                else:
                    valor_orig_norm = valor_original
                if valor_nuevo_norm != valor_orig_norm:
                    datos_a_enviar[key_snake] = valor_nuevo_norm
            else:
                datos_a_enviar[key_snake] = valor_nuevo_norm
        if not datos_a_enviar:
            return True
        supabase.table("ordenes_trabajo").update(datos_a_enviar).eq("id", id_interno).execute()
        return True
    except Exception as e:
        st.error(f"Error actualizando orden: {e}")
        return False

def guardar_orden_supabase(id_interno, datos):
    return actualizar_campos_supabase(id_interno, datos)

def mapear_campo_supabase(campo):
    mapeo = {
        "ID": "id", "ID OT": "id_ot", "Actividades": "actividades", "Procedimiento": "procedimiento",
        "Tecnico_Asignado": "tecnico_asignado", "Prioridad_Actividad": "prioridad_actividad",
        "Actividades_Hechas": "actividades_hechas", "Fecha_Ejecucion": "fecha_ejecucion",
        "Hora_Inicio": "hora_inicio", "Hora_Fin": "hora_fin", "Estado": "estado",
        "Comentarios": "comentarios", "Equipo": "equipo", "Ubicacion": "ubicacion",
        "Especialidad": "especialidad", "Nodo": "nodo"
    }
    if campo in mapeo:
        return mapeo[campo]
    return campo.lower().replace(" ", "_").replace(".", "").replace("-", "_").replace("__", "_")

def actualizar_orden_supabase(id_interno, campo, valor):
    try:
        campo_snake = mapear_campo_supabase(campo)
        if isinstance(valor, str) and valor.strip() == "":
            valor = None
        supabase.table("ordenes_trabajo").update({campo_snake: valor}).eq("id", id_interno).execute()
        return True
    except Exception as e:
        st.error(f"Error actualizando campo '{campo}' -> '{campo_snake}': {e}")
        return False

def guardar_asignaciones_supabase(df):
    try:
        columnas_editables = ["Tecnico_Asignado", "Estado", "Prioridad_Actividad", "Comentarios", "Fecha_Ejecucion", "Hora_Inicio", "Hora_Fin"]
        exitosos = 0
        for idx, row in df.iterrows():
            id_interno = row.get("ID")
            if pd.isna(id_interno):
                continue
            datos = {}
            for col in columnas_editables:
                if col in row.index and pd.notna(row[col]):
                    datos[col] = row[col]
            if datos:
                if guardar_orden_supabase(id_interno, datos):
                    exitosos += 1
        st.success(f"{exitosos} ordenes actualizadas en Supabase")
        return exitosos > 0
    except Exception as e:
        st.error(f"Error guardando asignaciones: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="App Tablet Mtto Preventivo", page_icon="🔧", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    .stApp { background-color: #F1F5F9; max-width: 100vw; overflow-x: hidden; }
    .main .block-container { padding-left: 0.3rem !important; padding-right: 0.3rem !important; max-width: 100% !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
    .tablet-header {
        background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%);
        color: white; padding: 12px 16px; border-radius: 0 0 16px 16px;
        text-align: center; font-size: 18px; font-weight: 700;
        margin: -1rem -1rem 1rem -1rem; box-shadow: 0 4px 15px rgba(26,35,158,0.3);
        position: sticky; top: 0; z-index: 100; width: 100%; box-sizing: border-box; word-wrap: break-word;
    }
    .home-screen { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; min-height: auto; text-align: center; padding: 10px; width: 100%; box-sizing: border-box; color: #0F172A; }
    .big-counter { font-size: 60px; font-weight: 900; color: #60a5fa; line-height: 1; margin: 10px 0; word-wrap: break-word; }
    .counter-label { font-size: 18px; color: #475569; margin-bottom: 30px; }
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
    .equipo-info { background: #F8FAFC; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
    .equipo-info strong { color: #0F172A; }
    .stButton>button { border-radius: 6px; font-weight: 600; font-size: 12px !important; padding: 4px 12px !important; }
    .prioridad-critico { border-left: 4px solid #dc3545 !important; background: linear-gradient(90deg, #fff5f5 0%, #ffffff 100%) !important; }
    .prioridad-secundario { border-left: 4px solid #ffc107 !important; background: linear-gradient(90deg, #fffbea 0%, #ffffff 100%) !important; }
    .prioridad-estandar { border-left: 4px solid #28a745 !important; background: linear-gradient(90deg, #f0fff4 0%, #ffffff 100%) !important; }
    .tabla-header { display: grid; background: #FFFFFF; color: #475569; grid-template-columns: 70px 45px 1fr 90px 110px; gap: 6px; padding: 8px 10px; background: #f8f9fa; border-bottom: 2px solid #dee2e6; font-weight: 700; font-size: 10px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; align-items: center; margin-bottom: 6px; }
    .tabla-fila { display: grid; background: #FFFFFF; border-color: #0EA5E9; grid-template-columns: 70px 45px 1fr 90px 110px; gap: 6px; padding: 8px 10px; background: white; border: 1px solid #e9ecef; border-radius: 6px; align-items: center; font-size: 12px; margin-bottom: 6px; transition: all 0.2s; }
    .tabla-fila:hover { background: #f8f9fa; border-color: #adb5bd; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .tabla-fila .col-id { font-family: monospace; font-size: 11px; color: #495057; }
    .tabla-fila .col-esp { font-weight: 600; font-size: 11px; color: #1a237e; }
    .tabla-fila .col-desc { font-size: 11px; color: #212529; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tabla-fila .col-estado { text-align: center; }
    .tabla-fila .col-tec { font-size: 10px; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tabla-fila-asig { display: grid; background: #FFFFFF; border-color: #0EA5E9; grid-template-columns: 1fr auto; gap: 10px; padding: 8px 10px; background: white; border: 1px solid #e9ecef; border-radius: 6px; align-items: center; margin-bottom: 4px; }
    .asig-info { min-width: 0; overflow: hidden; }
    .asig-ot { font-size: 12px; color: #212529; margin-bottom: 2px; }
    .asig-esp { color: #1a237e; font-weight: 600; font-size: 11px; }
    .asig-equipo { font-size: 10px; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .asig-estado { text-align: right; flex-shrink: 0; }
    .perfil-card { background: #FFFFFF; border-color: #0EA5E9; color: #0F172A; border-radius: 16px; padding: 24px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; border: 3px solid transparent; }
    .perfil-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
    .perfil-admin { border-color: #dc3545; }
    .perfil-tecnico { border-color: #28a745; }
    .perfil-supervisor { border-color: #007bff; }
    .perfil-icon { font-size: 48px; margin-bottom: 12px; }
    .perfil-titulo { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
    .perfil-desc { font-size: 12px; color: #666; }
    .tecnico-card { background: white; border-radius: 12px; padding: 12px 16px; margin-bottom: 8px; border: 2px solid #e9ecef; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: space-between; }
    .tecnico-card:hover { border-color: #1a237e; box-shadow: 0 2px 8px rgba(26,35,158,0.15); }
    .tecnico-card.activa { border-color: #1a237e; background: linear-gradient(135deg, #e8eaf6 0%, #ffffff 100%); }
    .tecnico-nombre { font-size: 14px; font-weight: 700; color: #1a237e; }
    .tecnico-esp { font-size: 11px; color: #666; }
    .tecnico-badge { background: #1a237e; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; min-width: 28px; text-align: center; }
    .tecnico-badge.cero { background: #6c757d; }
    .tecnico-badge.alta { background: #dc3545; }
    .tecnico-badge.media { background: #ffc107; color: #333; }
    .tecnico-badge.baja { background: #28a745; }
    .grupo-ele { border-left: 4px solid #ffc107 !important; }
    .grupo-mec { border-left: 4px solid #28a745 !important; }
    .maquina-card { background: #FFFFFF; border-color: #0EA5E9; color: #0F172A; border-radius: 12px; padding: 14px 16px; margin-bottom: 8px; border: 2px solid #e9ecef; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: space-between; }
    .maquina-card:hover { border-color: #1a237e; box-shadow: 0 2px 8px rgba(26,35,158,0.15); }
    .maquina-card.activa { border-color: #1a237e; background: linear-gradient(135deg, #e8eaf6 0%, #ffffff 100%); }
    .maquina-nombre { font-size: 15px; font-weight: 700; color: #1a237e; }
    .maquina-badge { background: #1a237e; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
    .filtro-nodo-label { font-size: 12px; color: #666; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; }
    .contador-maquinas { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin: 10px 0; }
    .contador-maquina { background: #FFFFFF; border-color: #0EA5E9; color: #0F172A; border-radius: 8px; padding: 8px 12px; text-align: center; border: 1px solid #e9ecef; min-width: 80px; }
    .contador-maquina-valor { font-size: 18px; font-weight: 800; color: #60a5fa; }
    .contador-maquina-label { font-size: 10px; color: #475569; }
    .nodo-badge-mini { background: #e8eaf6; color: #1a237e; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: monospace; }
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
    .stSelectbox label, .stTextInput label { color: #475569 !important; }
    .stMarkdown { margin-bottom: 0 !important; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: 0.2rem !important; }
    .eq-bloque { background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); border-radius: 16px; margin-bottom: 8px; color: #0F172A; border: 1px solid #1E3A5F; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.25); }
    .eq-bloque-header { background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%); padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
    .eq-bloque-titulo { font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 0.3px; line-height: 1.3; }
    .eq-bloque-meta { font-size: 11px; color: #0F172A; margin-top: 4px; }
    .eq-progress-bar { width: 100%; height: 6px; background: #FFFFFF; border-radius: 3px; margin-top: 8px; overflow: hidden; }
    .eq-progress-fill { height: 100%; background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%); border-radius: 3px; transition: width 0.3s ease; }
    .eq-bloque-contenido { padding: 10px 14px; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] { gap: 0rem !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { padding-left: 0px !important; padding-right: 0px !important; margin-left: 0px !important; margin-right: 0px !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child { min-width: 22px !important; max-width: 26px !important; flex: none !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) { padding-left: 2px !important; margin-left: 0px !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] { margin-top: 0px !important; margin-bottom: 0px !important; padding-top: 0px !important; padding-bottom: 0px !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label { min-height: unset !important; margin-bottom: 0px !important; padding-bottom: 0px !important; padding-right: 0px !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div { margin-right: 0px !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] { margin-bottom: 1px !important; }
    .eq-bloque-contenido div[data-testid="stTextInput"] { margin-bottom: 0px !important; }
    .eq-bloque-contenido div[data-testid="stTextInput"] > div > div > input { padding: 2px 6px !important; height: 28px !important; font-size: 11px !important; min-height: 28px !important; }
    .eq-tabla-header { display: grid; grid-template-columns: 36px 45px 1fr 70px 70px 140px; gap: 6px; padding: 6px 10px; background: #FFFFFF; border-radius: 8px; font-weight: 700; font-size: 10px; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; align-items: center; margin-bottom: 4px; }
    .eq-tabla-fila { display: grid; grid-template-columns: 36px 45px 1fr 70px 70px 140px; gap: 6px; padding: 4px 8px; background: #FFFFFF; border-bottom: 1px solid #334155; align-items: center; font-size: 12px; transition: background 0.2s; }
    .eq-tabla-fila:hover { background: #27354f; color: #e2e8f0; }
    .eq-tabla-fila:last-child { border-bottom: none; }
    .eq-esp-ele { background: #60a5fa; color: #0f172a; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-align: center; display: inline-block; }
    .eq-esp-mec { background: #fbbf24; color: #0f172a; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-align: center; display: inline-block; }
    .eq-esp-hid { background: #a78bfa; color: #0f172a; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-align: center; display: inline-block; }
    .eq-desc { color: #0F172A; font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .eq-tec { color: #0F172A; font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .eq-estado-ej { background-color: #059669; color: #ffffff; font-weight: 700; }
    .eq-estado-pd { background-color: #d97706; color: #ffffff; font-weight: 700; }
    .eq-estado-vf { background-color: #2563eb; color: #ffffff; font-weight: 700; }
    .eq-estado-cr { background-color: #0891b2; color: #ffffff; font-weight: 700; }
    .chk-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: #FFFFFF; border-radius: 8px; margin-bottom: 4px; border: 1px solid #E2E8F0; transition: all 0.15s; }
    .chk-item:hover { border-color: #0EA5E9; background: #F0F9FF; }
    .chk-item.ejecutada { opacity: 0.65; background: #F0FDF4; border-color: #86EFAC; }
    .chk-item.ejecutada .chk-desc { text-decoration: line-through; color: #166534; }
    .chk-box { width: 18px; height: 18px; accent-color: #0EA5E9; flex-shrink: 0; cursor: pointer; }
    .chk-desc { font-size: 13px; color: #0F172A; flex: 1; line-height: 1.3; }
    .chk-com-btn { width: 28px; height: 28px; border-radius: 6px; background: #F1F5F9; border: 1px solid #CBD5E1; display: flex; align-items: center; justify-content: center; font-size: 13px; cursor: pointer; flex-shrink: 0; color: #64748B; }
    .chk-com-btn:hover { background: #E0F2FE; border-color: #0EA5E9; }
    .chk-com-btn.tiene { background: #DBEAFE; border-color: #3B82F6; color: #1D4ED8; }
    .chk-expand { padding: 8px 12px 8px 44px; background: #F8FAFC; border-radius: 0 0 8px 8px; margin-top: -2px; margin-bottom: 6px; border: 1px solid #E2E8F0; border-top: none; }
    .chk-expand-row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
    .chk-expand-label { font-size: 10px; color: #64748B; font-weight: 700; text-transform: uppercase; width: 60px; }
    .chk-expand-val { font-size: 12px; color: #0F172A; font-weight: 600; }
    .chk-expand-input { width: 100%; padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 12px; background: white; color: #0F172A; }
    .am-cantidad-box { background: #F0F9FF; border: 2px solid #0EA5E9; border-radius: 12px; padding: 14px; margin-bottom: 16px; }
    .am-fila { display: flex; gap: 8px; align-items: flex-end; background: white; padding: 8px 10px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 6px; }
    .am-resumen { background: #FFF7ED; border: 1px solid #F97316; border-radius: 10px; padding: 10px 14px; margin: 10px 0; font-size: 13px; }
    .asig-rapida-header { display: none !important; grid-template-columns: 1fr 50px 1.5fr 80px 160px; gap: 8px; padding: 8px 12px; background: #F1F5F9; border-radius: 8px; font-weight: 700; font-size: 10px; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; align-items: center; margin-bottom: 6px; }
    .asig-rapida-fila { display: grid; grid-template-columns: 1fr 50px 1.5fr 80px 160px; gap: 8px; padding: 8px 12px; background: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; align-items: center; font-size: 12px; margin-bottom: 4px; transition: all 0.15s; }
    .asig-rapida-fila:hover { border-color: #0EA5E9; box-shadow: 0 2px 6px rgba(14,165,233,0.08); }
    .asig-rapida-fila.asignada { border-left: 3px solid #10B981; background: #F0FDF4; }
    .batch-bar-rapida { background: linear-gradient(135deg, #F0F9FF, #E0F2FE); border: 1px solid #BAE6FD; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px; }
    @media (max-width: 768px) {
        .asig-rapida-header { display: none; }
        .asig-rapida-fila { grid-template-columns: 1fr 1fr; gap: 6px; padding: 10px; }
        .asig-rapida-fila > div:nth-child(1) { grid-column: 1 / -1; }
        .asig-rapida-fila > div:nth-child(2) { grid-column: 1; }
        .asig-rapida-fila > div:nth-child(3) { grid-column: 2; text-align: right; }
        .asig-rapida-fila > div:nth-child(4) { grid-column: 1; }
        .asig-rapida-fila > div:nth-child(5) { grid-column: 2; }
    }
    .eq-bloque-contenido div[data-testid="stVerticalBlock"] > div { margin-bottom: 2px !important; padding-bottom: 2px !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] { gap: 0.3rem !important; margin-bottom: 2px !important; padding-bottom: 2px !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div { padding-left: 0px !important; padding-right: 0px !important; margin-left: 0px !important; margin-right: 0px !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div:first-child { min-width: 24px !important; max-width: 28px !important; flex: none !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div { margin-bottom: 0px !important; padding-bottom: 0px !important; }
    .eq-bloque-contenido .stCheckbox { margin-bottom: 0px !important; padding-bottom: 0px !important; }
    .eq-bloque-contenido .stCheckbox > label { margin-bottom: 0px !important; padding-bottom: 0px !important; min-height: unset !important; }
    .eq-bloque-contenido .stCheckbox > label > div { margin-bottom: 0px !important; padding-bottom: 0px !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] { margin-top: 0px !important; margin-bottom: 0px !important; padding-top: 0px !important; padding-bottom: 0px !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label { min-height: 20px !important; margin-bottom: 0px !important; padding-bottom: 0px !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div[data-testid="stWidgetLabel"] { display: none !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div { margin-top: 0px !important; margin-bottom: 0px !important; padding-top: 0px !important; padding-bottom: 0px !important; }
    .eq-bloque-contenido div[data-testid="element-container"] { margin-bottom: 0px !important; }
    .fila-compacta { display: flex; align-items: center; gap: 2px; padding: 6px 10px 6px 4px; margin-bottom: 4px; border-radius: 6px; border: 1px solid #E2E8F0; background: #FFFFFF; transition: all 0.15s; }
    .fila-compacta:hover { border-color: #0EA5E9; background: #F0F9FF; }
    .fila-compacta.ejecutada { opacity: 0.65; background: #F0FDF4; border-color: #86EFAC; }
    .fila-compacta.ejecutada .fila-desc { text-decoration: line-through; color: #166534; }
    [data-testid="stExpander"] { margin-bottom: 4px !important; }
    [data-testid="stExpander"] > details { border: 1px solid #E2E8F0; border-radius: 8px; background: #FFFFFF; overflow: hidden; }
    [data-testid="stExpander"] > details > summary { padding: 8px 12px !important; font-size: 12px !important; font-weight: 600 !important; color: #0F172A !important; min-height: unset !important; }
    [data-testid="stExpander"] > details > summary:hover { background: #F8FAFC; }
    [data-testid="stExpander"] > details[open] > summary { background: #F0F9FF; border-bottom: 1px solid #E2E8F0; }
    [data-testid="stExpander"] .streamlit-expanderContent { padding: 10px 12px !important; }
    [data-testid="stExpander"] .streamlit-expanderContent p { margin-bottom: 4px !important; font-size: 12px !important; }
    [data-testid="stExpander"] .streamlit-expanderContent .stSelectbox { margin-top: 8px !important; }
</style>
""", unsafe_allow_html=True)

TECNICOS_ELE = [
    "RIVERA SANTOS LUIS ALVARO", "NESTOR LEONARDO CORTES TORRES", "JAVIER FELIPE ROZO CALDERON",
    "JHON FREDY BERNAL AVILA", "YUPER YAIL CASTILLO", "ERIK SANTIAGO MARTINEZ HERRERA",
    "QUECANO ANGARITA CARLOS", "PULIDO RIOS JAHIR", "GARCIA CASAS JEFFERSSON DAVID",
    "CASTAÑEDA ORTIZ EDISON ORACIO", "DIAZ SEGURA DANIEL STEVEN", "FRANCO SIERRA JOSE ALEJANDRO",
    "MOJICA GARCES JEAN CARLOS", "CAROLOINA RINCON", "PINILLA ARIAS JHONATAN FERNANDO",
    "JUAN DAVID CHACON VELANDIA"
]
TECNICOS_MEC = [
    "WILSON ABDON QUEVEDO PASTOR", "LUIS FERNANDO DELGADO CARMONA", "SAENZ SAENZ CARLOS EFREN",
    "PABLO ENRRIQUE TORRES BARON", "FELIPE LATORRE DIAZ", "MOLINA GONZALEZ MICHAEL ANDRES",
    "MURILLO MURILLO WILLIAM OBER", "MOLANO ALFONSO LUIS", "MARTINEZ TORRES FREDY ALEXANDER",
    "VARGAS VARGAS JHON ALEJANDER", "MERIÑO GIL JOSE MANUEL", "DILAN MEDINA",
    "RODRIGUEZ CAMACHO LUIS ALVEIRO", "MENDIVIELSO CANTOR JUAN CARLOS", "ARIAS  PERDOMO JUAN ESTEBAN",
    "VELASQUEZ OSPINA CRISTIAN JAIR"
]

# ═══════════════════════════════════════════════════════════════════════
#  SINCRONIZACIÓN EXCEL ↔ SUPABASE
# ═══════════════════════════════════════════════════════════════════════
def sincronizar_excel_a_supabase(df_excel, modo="reemplazar"):
    try:
        df = df_excel.copy()
        cols_originales = {c.strip().lower(): c for c in df.columns}
        mapeo_columnas = {
            "id_ot": ["id ot", "id_ot", "ot", "numero ot", "no. ot", "orden", "no ot"],
            "equipo": ["equipo", "descripción", "descripcion", "id activo", "id_activo", "activo", "maquina", "máquina"],
            "ubicacion": ["ubicacion", "ubicación", "lugar", "area", "área", "un", "unidad", "localizacion", "sala"],
            "especialidad": ["especialidad", "esp", "tipo de ot", "tipo_ot", "tipo", "area tecnica", "disciplina"],
            "actividades": ["actividades", "actividad", "descr", "descripcion", "descripción", "tarea", "trabajo", "falla", "problema"],
            "procedimiento": ["procedimiento", "proc", "proceso", "tipo procedimiento"],
            "nodo": ["nodo", "codigo", "código", "referencia", "id nodo", "tag"],
            "prioridad_actividad": ["prioridad", "prioridad_actividad", "prioridad actividad", "nivel", "color", "urgencia"]
        }
        columnas_renombrar = {}
        for supabase_col, posibles_nombres in mapeo_columnas.items():
            for posible in posibles_nombres:
                if posible in cols_originales:
                    columnas_renombrar[cols_originales[posible]] = supabase_col
                    break
        df = df.rename(columns=columnas_renombrar)
        detectadas = list(columnas_renombrar.values())
        faltantes = [c for c in mapeo_columnas.keys() if c not in detectadas]
        st.markdown(f"""
        <div style="background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 10px; margin: 8px 0;">
            <div style="font-size: 12px; color: #166534;">
                ✅ <b>Columnas detectadas:</b> {', '.join(detectadas) if detectadas else 'Ninguna'}<br>
                {'⚠️ <b>Sin detectar:</b> ' + ', '.join(faltantes) if faltantes else '✅ Todas las columnas principales encontradas'}
            </div>
        </div>
        """, unsafe_allow_html=True)
        campos_base = ["id_ot", "equipo", "ubicacion", "especialidad", "actividades", "procedimiento", "nodo", "prioridad_actividad"]
        cols_validas = [c for c in campos_base if c in df.columns]
        if not cols_validas:
            st.error(f"❌ No se detectaron columnas válidas. Columnas en tu Excel: {list(df_excel.columns)}")
            return False, "No se detectaron columnas válidas"
        df = df[cols_validas]
        df = df.where(pd.notnull(df), None)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(lambda x: None if isinstance(x, str) and x.strip() == "" else x)
        def generar_id_unico(row):
            partes = [str(row.get("id_ot", "")), str(row.get("equipo", "")), str(row.get("ubicacion", "")), str(row.get("actividades", "")), str(row.get("nodo", ""))]
            raw = "|".join(partes)
            return hashlib.md5(raw.encode()).hexdigest()[:20]
        df["id_unico"] = df.apply(generar_id_unico, axis=1)
        if "id_ot" in df.columns:
            df["id_ot"] = pd.to_numeric(df["id_ot"], errors="coerce")
            df["id_ot"] = df["id_ot"].apply(lambda x: int(x) if pd.notna(x) else None)
        registros = df.to_dict(orient="records")
        total = len(registros)
        if total == 0:
            return False, "❌ No hay registros válidos para sincronizar"
        if modo == "reemplazar":
            with st.spinner("🗑️ Borrando datos antiguos..."):
                supabase.table("ordenes_trabajo").delete().neq("id", 0).execute()
            insertados = 0
            batch_size = 500
            progress_bar = st.progress(0)
            for i in range(0, total, batch_size):
                lote = registros[i:i+batch_size]
                supabase.table("ordenes_trabajo").insert(lote).execute()
                insertados += len(lote)
                progress_bar.progress(min((i + batch_size) / total, 1.0))
            progress_bar.empty()
            return True, f"✅ Sincronización completa: {insertados} registros insertados con ID único."
        elif modo == "upsert":
            upsertados = 0
            batch_size = 500
            progress_bar = st.progress(0)
            for i in range(0, total, batch_size):
                lote = registros[i:i+batch_size]
                supabase.table("ordenes_trabajo").upsert(lote, on_conflict="id_unico").execute()
                upsertados += len(lote)
                progress_bar.progress(min((i + batch_size) / total, 1.0))
            progress_bar.empty()
            return True, f"✅ Sincronización completa: {upsertados} registros actualizados/insertados. Las asignaciones de técnicos se mantuvieron."
        else:
            return False, "Modo no válido"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ═══════════════════════════════════════════════════════════════════════
#  CALLBACKS AUTO-GUARDAR
# ═══════════════════════════════════════════════════════════════════════
def auto_guardar_fila(internal_id, key_widget):
    nuevo_tec = st.session_state.get(key_widget, "")
    if nuevo_tec == "Sin asignar":
        nuevo_tec = ""
    df = st.session_state.df_mantenimientos
    idx, row = get_row_by_internal_id(df, internal_id)
    if idx is None:
        return
    tec_bd = limpiar(row.get("Tecnico_Asignado"), "")
    if nuevo_tec == tec_bd:
        return
    datos = {"Tecnico_Asignado": nuevo_tec}
    estado_bd = limpiar(row.get("Estado"), "Pendiente")
    if estado_bd in ["Ejecutado", "Verificado"]:
        datos["Estado"] = "Pendiente"
        datos["Hora_Inicio"] = None
        datos["Hora_Fin"] = None
        datos["Fecha_Ejecucion"] = None
        datos["Comentarios"] = None
    elif nuevo_tec == "" and estado_bd != "Pendiente":
        datos["Estado"] = "Pendiente"
    if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
        st.session_state.df_mantenimientos.loc[idx, "Tecnico_Asignado"] = nuevo_tec
        if "Estado" in datos:
            st.session_state.df_mantenimientos.loc[idx, "Estado"] = datos["Estado"]
        msg = f"✅ Guardado: OT {limpiar(row.get('ID OT'), 'SIN ID')}"
        st.session_state.asig_rapida_msg = msg
        st.toast(msg, icon="💾")

def auto_guardar_masivo(maquina_sel, tecnico_masivo, desasignar=False):
    if not desasignar and not tecnico_masivo:
        return
    df = st.session_state.df_mantenimientos
    df_asig = df.copy()
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_asig.columns:
        df_asig = df_asig[df_asig["Especialidad"] == st.session_state.filtro_especialidad]
    if maquina_sel != "Todas" and "Ubicacion" in df_asig.columns:
        df_asig = df_asig[df_asig["Ubicacion"] == maquina_sel]
    if "Nodo" in df_asig.columns and st.session_state.filtro_maquina_nodo != "Todas":
        df_asig = df_asig[df_asig["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
    if "Nodo" in df_asig.columns and st.session_state.filtro_subsistema_nodo != "Todos":
        df_asig = df_asig[df_asig["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]
    estado_sel = st.session_state.filtro_estado_asig
    if estado_sel != "Todos" and "Estado" in df_asig.columns:
        def estado_efectivo_asig(row):
            estado_bd = limpiar(row.get("Estado"), "Pendiente")
            tecnico_bd = limpiar(row.get("Tecnico_Asignado"), "")
            if not tecnico_bd and estado_bd in ["Ejecutado", "Verificado"]:
                return "Pendiente"
            return estado_bd
        df_asig = df_asig[df_asig.apply(estado_efectivo_asig, axis=1) == estado_sel]
    guardados = 0
    valor_nuevo = "" if desasignar else tecnico_masivo
    for _, row_a in df_asig.iterrows():
        internal_id = limpiar(row_a.get("ID"), "")
        if not internal_id:
            continue
        tec_bd = limpiar(row_a.get("Tecnico_Asignado"), "")
        if valor_nuevo == tec_bd:
            continue
        datos = {"Tecnico_Asignado": valor_nuevo}
        estado_bd = limpiar(row_a.get("Estado"), "Pendiente")
        if estado_bd in ["Ejecutado", "Verificado"]:
            datos["Estado"] = "Pendiente"
            datos["Hora_Inicio"] = None
            datos["Hora_Fin"] = None
            datos["Fecha_Ejecucion"] = None
            datos["Comentarios"] = None
        elif valor_nuevo == "" and estado_bd != "Pendiente":
            datos["Estado"] = "Pendiente"
        if actualizar_campos_supabase(internal_id, datos, row_a.to_dict()):
            idx_local, _ = get_row_by_internal_id(st.session_state.df_mantenimientos, internal_id)
            if idx_local is not None:
                st.session_state.df_mantenimientos.loc[idx_local, "Tecnico_Asignado"] = valor_nuevo
                if "Estado" in datos:
                    st.session_state.df_mantenimientos.loc[idx_local, "Estado"] = datos["Estado"]
            guardados += 1
    if guardados > 0:
        if desasignar:
            st.success(f"✅ {guardados} actividades desasignadas de **{maquina_sel}**")
        else:
            st.success(f"✅ {tecnico_masivo} asignado a {guardados} actividades de **{maquina_sel}**")
        st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════
#  PANTALLA: SINCRONIZAR
# ═══════════════════════════════════════════════════════════════════════
def pantalla_sincronizar():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>🔄 Sincronizar desde Excel</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("sincronizar")

    st.markdown("""
    <div style="background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 12px; padding: 16px; margin: 12px 0;">
        <div style="font-size: 14px; font-weight: 700; color: #0369a1; margin-bottom: 6px;">📋 ¿Cómo funciona el ID Único?</div>
        <div style="font-size: 12px; color: #475569; line-height: 1.6;">
            Como tu <b>id_ot</b> es el mismo en todas las filas (392368), la app genera automáticamente 
            un <b>ID único</b> para cada actividad basado en: <code>equipo + ubicación + actividades + nodo</code>.<br><br>
            ✅ <b>Reemplazar Todo:</b> Borra todo e inserta el Excel (usa la primera vez).<br>
            🔄 <b>Actualizar/Insertar:</b> Solo cambia lo que cambió, mantiene técnicos y estados.
        </div>
    </div>
    """, unsafe_allow_html=True)

    archivo = st.file_uploader("📁 Arrastra tu Excel aquí", type=["xlsx", "xls"], key=gen_key("upload_excel"))

    if archivo is None:
        st.info("⬆️ Sube un archivo Excel para comenzar")
        return

    try:
        nombre_archivo = archivo.name.lower()
        if nombre_archivo.endswith('.xls'):
            df_excel = pd.read_excel(archivo, engine='xlrd')
        else:
            df_excel = pd.read_excel(archivo, engine='openpyxl')
        st.success(f"📊 Excel leído: **{len(df_excel)} filas** × **{len(df_excel.columns)} columnas**")
    except ImportError as e:
        if 'xlrd' in str(e):
            st.error("❌ Falta la librería 'xlrd' para leer archivos .xls. Agrega `xlrd>=2.0.1` a tu requirements.txt y vuelve a desplegar.")
        else:
            st.error(f"❌ Error de importación: {e}")
        return
    except Exception as e:
        st.error(f"❌ Error leyendo Excel: {e}")
        return

    with st.expander("👁️ Vista previa (primeras 10 filas)", expanded=True):
        st.dataframe(df_excel.head(10), use_container_width=True)

    cols_norm = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df_excel.columns]
    esperadas = ["id_ot", "equipo", "ubicacion", "especialidad", "actividades", "procedimiento", "nodo", "prioridad_actividad"]
    faltantes = [c for c in esperadas if c not in cols_norm]

    if faltantes:
        st.warning(f"⚠️ Columnas no detectadas: **{', '.join(faltantes)}**")
    else:
        st.success("✅ Todas las columnas principales detectadas.")

    st.subheader("🔑 IDs Únicos generados")
    st.caption("La app crea estos IDs automáticamente para cada fila. Si el contenido no cambia, el ID se mantiene.")

    df_preview = df_excel.head(5).copy()
    df_preview.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df_preview.columns]

    def preview_id_unico(row):
        partes = [
            str(row.get("id_ot", "")),
            str(row.get("equipo", "")),
            str(row.get("ubicacion", "")),
            str(row.get("actividades", "")),
            str(row.get("nodo", ""))
        ]
        raw = "|".join(partes)
        return hashlib.md5(raw.encode()).hexdigest()[:20]

    if "equipo" in df_preview.columns and "actividades" in df_preview.columns:
        df_preview["id_unico_generado"] = df_preview.apply(preview_id_unico, axis=1)
        cols_show = [c for c in ["id_ot", "equipo", "actividades", "id_unico_generado"] if c in df_preview.columns]
        st.dataframe(df_preview[cols_show], use_container_width=True)

    st.subheader("⚙️ Modo de Sincronización")
    modo = st.radio(
        "Elige qué hacer:",
        [
            "🗑️ REEMPLAZAR TODO — Borra todo en Supabase e inserta el Excel nuevo (usa la primera vez)",
            "🔄 ACTUALIZAR/INSERTAR — Mantiene lo existente, actualiza por ID único (usa todos los días)"
        ],
        key=gen_key("modo_sync")
    )
    modo_valor = "reemplazar" if "REEMPLAZAR" in modo else "upsert"

    if modo_valor == "reemplazar":
        st.error("⚠️ **ATENCIÓN:** Esto borrará TODOS los datos actuales. Úsalo solo la primera vez o si quieres empezar de cero.")
    else:
        st.info("ℹ️ Este modo usa el ID único generado automáticamente. Actualiza lo que cambió, crea lo nuevo, y respeta asignaciones de técnicos.")
        st.markdown("""
        <div style="font-size: 11px; color: #64748B; background: #F8FAFC; padding: 8px; border-radius: 6px;">
            💡 <b>Requisito para Actualizar/Insertar:</b><br>
            Debes haber usado "Reemplazar Todo" al menos una vez con esta versión de la app,<br>
            o ejecutar en SQL Editor:<br>
            <code>ALTER TABLE ordenes_trabajo ADD CONSTRAINT unique_id_unico UNIQUE (id_unico);</code>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        btn_text = "🚀 REEMPLAZAR Y SINCRONIZAR" if modo_valor == "reemplazar" else "🚀 ACTUALIZAR Y SINCRONIZAR"
        if st.button(btn_text, use_container_width=True, type="primary", key=gen_key("btn_sync")):
            with st.spinner("Sincronizando, por favor espera..."):
                exito, mensaje = sincronizar_excel_a_supabase(df_excel, modo=modo_valor)

            if exito:
                st.success(mensaje)
                st.balloons()
                st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                st.info("🔄 Datos actualizados. Puedes volver al inicio.")
            else:
                st.error(mensaje)

# ═══════════════════════════════════════════════════════════════════════
#  PANTALLA: ASIGNACIÓN RÁPIDA
# ═══════════════════════════════════════════════════════════════════════
def pantalla_asignacion():
    df = recargar_datos()
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Asignacion de Tecnicos</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("asignacion")

    if st.session_state.get("asig_rapida_msg"):
        st.toast(st.session_state.asig_rapida_msg, icon="💾")
        st.session_state.asig_rapida_msg = None

    df_asig_base = df.copy()
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_asig_base.columns:
        df_asig_base = df_asig_base[df_asig_base["Especialidad"] == st.session_state.filtro_especialidad]
    if "Nodo" in df_asig_base.columns and st.session_state.filtro_maquina_nodo != "Todas":
        df_asig_base = df_asig_base[df_asig_base["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
    if "Nodo" in df_asig_base.columns and st.session_state.filtro_subsistema_nodo != "Todos":
        df_asig_base = df_asig_base[df_asig_base["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]

    df_asig = df_asig_base.copy()
    if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_asig.columns:
        df_asig = df_asig[df_asig["Ubicacion"] == st.session_state.filtro_maquina]

    col_izq, col_der = st.columns([1, 3])

    with col_izq:
        st.markdown("<div style='font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:8px;'>📍 Máquina</div>", unsafe_allow_html=True)
        maquinas_asig = obtener_maquinas_disponibles(df_asig_base)
        for maq in maquinas_asig:
            is_active = st.session_state.filtro_maquina == maq
            btn_type = "primary" if is_active else "secondary"
            if st.button(maq, key=gen_key("btn_maq", maq), type=btn_type, use_container_width=True):
                st.session_state.filtro_maquina = maq
                st.rerun()

    with col_der:
        maq_sel = st.session_state.filtro_maquina
        total_ordenes = len(df_asig)

        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <div style="font-size: 16px; font-weight: 700; color: #0F172A;">
                {maq_sel if maq_sel != "Todas" else "Todas las máquinas"}
            </div>
            <div style="font-size: 13px; color: #64748B;">
                {total_ordenes} actividades encontradas
            </div>
        </div>
        """, unsafe_allow_html=True)

        if total_ordenes > 0 and maq_sel != "Todas":
            esp_filtro = st.session_state.filtro_especialidad
            if esp_filtro == "Todas" and "Especialidad" in df_asig.columns:
                esps_unicas = df_asig["Especialidad"].dropna().unique()
                if len(esps_unicas) == 1:
                    esp_filtro = esps_unicas[0]
            tecnicos_info = obtener_tecnicos_con_carga(df, esp_filtro)
            lista_tecnicos = [""] + [t["nombre"] for t in tecnicos_info]

            st.markdown("<div class='batch-bar-rapida'>", unsafe_allow_html=True)
            cols_batch = st.columns([2, 2, 1])
            with cols_batch[0]:
                st.markdown("<div style='font-weight:600; color:#0369a1; font-size:13px; padding-top:6px;'>👤 Asignar técnico a todas:</div>", unsafe_allow_html=True)
            with cols_batch[1]:
                tecnico_masivo = st.selectbox("Técnico masivo", lista_tecnicos, key=gen_key("batch_tec"), label_visibility="collapsed")
            with cols_batch[2]:
                if st.button("✓ Asignar", type="primary", use_container_width=True, key=gen_key("btn_batch_asig")):
                    if tecnico_masivo:
                        auto_guardar_masivo(maq_sel, tecnico_masivo)
                    else:
                        st.warning("Selecciona un técnico primero")
            st.markdown("</div>", unsafe_allow_html=True)

        if df_asig.empty:
            st.info("📭 No hay ordenes con los filtros seleccionados.")
            st.stop()

        df_pagina = df_asig
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if df_pagina.empty:
            st.info("📭 No hay actividades con los filtros seleccionados.")
        else:
            st.success(f"✅ {len(df_pagina)} actividades listas para asignar. Usa la barra de arriba.")

        for idx, row in df_pagina.iterrows():
            internal_id = limpiar(row.get("ID"), "")
            id_ot       = limpiar(row.get("ID OT"), "SIN ID")
            desc        = limpiar(row.get("Actividades"), "Sin descripción")
            estado      = limpiar(row.get("Estado"), "Pendiente")
            tec_asig    = limpiar(row.get("Tecnico_Asignado"), "")
            proc        = limpiar(row.get("Procedimiento"), "")
            nodo        = limpiar(row.get("Nodo"), "")
            nodo_badge  = f"<span class='nodo-badge-mini'>{nodo}</span>" if nodo else ""

            estado_cls = "eq-estado-pd"
            if estado == "Ejecutado": estado_cls = "eq-estado-ej"
            if estado == "Verificado": estado_cls = "eq-estado-vf"

            clase_asignada = "asignada" if tec_asig else ""
            st.markdown(f"""
            <div class="asig-rapida-fila {clase_asignada}">
                <div>
                    <div class="asig-ot"><strong>OT {id_ot}</strong> {nodo_badge}</div>
                    <div style="font-size:11px;color:#64748B;">{proc}</div>
                    <div style="font-size:12px;color:#0F172A;margin-top:2px;">{desc}</div>
                </div>
                <div style="text-align:right;">
                    <span class="estado-badge {estado_cls}">{estado}</span>
                    <div style="font-size:10px;color:#64748B;margin-top:4px;">
                        {tec_asig if tec_asig else "Sin asignar"}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
#  PANTALLAS STUB (mínimas para que la app no falle)
#  Reemplaza estas con tus implementaciones reales cuando las tengas
# ═══════════════════════════════════════════════════════════════════════
def pantalla_login():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>🔧 App Tablet Mtto Preventivo</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='home-screen'><h2>Iniciar Sesión</h2></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        perfil = st.selectbox("Perfil", ["", "Admin", "Técnico"], key=gen_key("sel_perfil"))
        if perfil == "Admin":
            pwd = st.text_input("Contraseña Admin", type="password", key=gen_key("pwd_admin"))
            if st.button("Entrar como Admin", use_container_width=True, type="primary"):
                # Reemplaza con tu lógica real de autenticación
                if pwd == "admin123":  # Cambia esto
                    st.session_state.perfil = "admin"
                    st.session_state.admin_autenticado = True
                    st.session_state.pagina = "home"
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")
        elif perfil == "Técnico":
            tecnicos = TECNICOS_ELE + TECNICOS_MEC
            tec = st.selectbox("Selecciona tu nombre", [""] + tecnicos, key=gen_key("sel_tec"))
            if st.button("Entrar como Técnico", use_container_width=True, type="primary"):
                if tec:
                    st.session_state.perfil = "tecnico"
                    st.session_state.tecnico_seleccionado = tec
                    st.session_state.pagina = "mis_ordenes"
                    st.rerun()
                else:
                    st.warning("Selecciona un técnico")

def pantalla_home():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>🏠 Inicio</span>
    </div>
    """, unsafe_allow_html=True)

    df = cargar_ordenes_supabase()
    st.session_state.df_mantenimientos = df

    total = len(df)
    ejecutadas = len(df[df["Estado"] == "Ejecutado"]) if not df.empty else 0
    pendientes = len(df[df["Estado"] == "Pendiente"]) if not df.empty else 0
    verificar = len(df[df["Estado"] == "Verificado"]) if not df.empty else 0

    st.markdown(f"""
    <div class="home-screen">
        <div style="margin: 20px 0;">
            <div class="big-counter">{total}</div>
            <div class="counter-label">Órdenes Totales</div>
        </div>
        <div class="progress-bar-container">
            <div class="progress-item">
                <div class="progress-value" style="color: #28a745;">{ejecutadas}</div>
                <div class="progress-label">Ejecutadas</div>
            </div>
            <div class="progress-item">
                <div class="progress-value" style="color: #ffc107;">{pendientes}</div>
                <div class="progress-label">Pendientes</div>
            </div>
            <div class="progress-item">
                <div class="progress-value" style="color: #007bff;">{verificar}</div>
                <div class="progress-label">Verificar</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 Ver Órdenes", use_container_width=True, type="primary"):
            st.session_state.pagina = "ordenes"
            st.rerun()
        if st.button("⚙️ Sincronizar Excel", use_container_width=True):
            st.session_state.pagina = "sincronizar"
            st.rerun()
    with col2:
        if st.button("👥 Asignar Técnicos", use_container_width=True):
            st.session_state.pagina = "asignacion"
            st.rerun()
        if st.button("✅ Verificar", use_container_width=True):
            st.session_state.pagina = "verificar"
            st.rerun()

    if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def pantalla_ordenes():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>📋 Órdenes de Trabajo</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("ordenes")
    df = cargar_ordenes_supabase()
    if df.empty:
        st.info("No hay órdenes cargadas.")
        return
    st.dataframe(df, use_container_width=True)

def pantalla_mis_ordenes():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>🔧 Mis Órdenes</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("mis_ordenes")
    df = cargar_ordenes_supabase()
    tec = st.session_state.get("tecnico_seleccionado", "")
    if tec and not df.empty:
        df_mias = df[df["Tecnico_Asignado"] == tec]
        st.dataframe(df_mias, use_container_width=True)
    else:
        st.info("No tienes órdenes asignadas.")

def pantalla_ejecutar():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>▶️ Ejecutar OT</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("ejecutar")
    st.info("Pantalla de ejecución. Implementa tu lógica aquí.")

def pantalla_detalle_tecnico():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>👤 Detalle Técnico</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("detalle_tecnico")
    st.info("Pantalla de detalle técnico. Implementa tu lógica aquí.")

def pantalla_detalle():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>📄 Detalle OT</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("detalle")
    st.info("Pantalla de detalle. Implementa tu lógica aquí.")

def pantalla_verificar():
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>✅ Verificar Órdenes</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("verificar")
    df = cargar_ordenes_supabase()
    if not df.empty:
        df_ver = df[df["Estado"] == "Ejecutado"]
        st.dataframe(df_ver, use_container_width=True)
    else:
        st.info("No hay órdenes para verificar.")

# ═══════════════════════════════════════════════════════════════════════
#  PROTECCIÓN DE RUTAS
# ═══════════════════════════════════════════════════════════════════════
paginas_admin = ["home", "ordenes", "asignacion", "verificar", "detalle", "sincronizar"]
if st.session_state.perfil == "admin" and not st.session_state.get("admin_autenticado", False):
    st.session_state.pagina = "login"
    st.session_state.perfil = None
    st.session_state.mostrar_login_admin = False
elif st.session_state.perfil != "admin" and st.session_state.pagina in ["asignacion", "verificar", "sincronizar", "ordenes"]:
    st.session_state.pagina = "login"
    st.session_state.perfil = None

# ═══════════════════════════════════════════════════════════════════════
#  EJECUCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════
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
elif st.session_state.pagina == "sincronizar":
    pantalla_sincronizar()
else:
    st.session_state.pagina = "login"
    st.rerun()
