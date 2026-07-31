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
import plotly.graph_objects as go
import plotly.express as px

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

# ==================== FUNCION LIMPIAR NaN ====================
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
            "Hora_Fin": "", "Prioridad_Actividad": "", "ID OT": ""
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
        "ID": "id", "ID OT": "id_ot", "Descripcion de procedimiento": "descripcion_procedimiento",
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

st.set_page_config(page_title="App Tablet Mtto Preventivo", page_icon="🔧", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #f3f4f6; }
    [data-testid="stSidebar"] { background-color: #111827 !important; min-width: 260px !important; max-width: 260px !important; }
    [data-testid="stSidebar"] .css-1d391kg, [data-testid="stSidebar"] .css-17eq0hr { background-color: #111827; }
    [data-testid="stSidebar"] * { color: #e5e7eb !important; }
    [data-testid="stSidebar"] hr { border-color: #374151 !important; margin: 1rem 0; }
    .sidebar-title { font-size: 20px; font-weight: 800; color: #f9fafb; padding: 1rem 0 0.5rem 0; letter-spacing: -0.5px; }
    .sidebar-sub { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.5rem; font-weight: 600; }
    .nav-item { padding: 10px 14px; border-radius: 8px; margin-bottom: 4px; cursor: pointer; transition: all 0.2s; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 10px; }
    .nav-item:hover { background-color: #1f2937; }
    .nav-item.active { background-color: #dc2626; color: white !important; }
    .nav-item.active * { color: white !important; }
    .top-bar { background: #111827; padding: 12px 24px; border-radius: 0 0 12px 12px; margin: -1rem -1rem 1.5rem -1rem; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .top-bar-title { color: white; font-size: 18px; font-weight: 700; }
    .top-bar-user { color: #9ca3af; font-size: 13px; }
    .kpi-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e5e7eb; transition: transform 0.2s; }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .kpi-value { font-size: 32px; font-weight: 800; color: #111827; line-height: 1; margin-top: 8px; }
    .kpi-label { font-size: 12px; color: #6b7280; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-delta { font-size: 12px; font-weight: 600; margin-top: 6px; }
    .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #e5e7eb; margin-bottom: 16px; }
    .card-header { font-size: 14px; font-weight: 700; color: #374151; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px; }
    .stDataFrame { border-radius: 12px !important; overflow: hidden !important; }
    .stButton>button { border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }
    .badge-ejecutado { background: #d1fae5; color: #065f46; }
    .badge-pendiente { background: #fef3c7; color: #92400e; }
    .badge-verificado { background: #dbeafe; color: #1e40af; }
    .badge-critico { background: #fee2e2; color: #991b1b; }
    .badge-secundario { background: #fef9c3; color: #854d0e; }
    .badge-estandar { background: #dcfce7; color: #166534; }
    @media (max-width: 768px) {
        .kpi-value { font-size: 24px; }
        .top-bar { padding: 10px 14px; }
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 1rem !important; }
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
    .nodo-badge-mini { background: #e8eaf6; color: #1a237e; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: monospace; }
    .detail-panel { background: white; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-top: 10px; }
    .equipo-info { background: #f5f5f5; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }
    .prioridad-critico { border-left: 4px solid #dc3545 !important; background: linear-gradient(90deg, #fff5f5 0%, #ffffff 100%) !important; }
    .prioridad-secundario { border-left: 4px solid #ffc107 !important; background: linear-gradient(90deg, #fffbea 0%, #ffffff 100%) !important; }
    .prioridad-estandar { border-left: 4px solid #28a745 !important; background: linear-gradient(90deg, #f0fff4 0%, #ffffff 100%) !important; }
    .eq-bloque { background: white; border-radius: 16px; margin-bottom: 20px; border: 1px solid #e5e7eb; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .eq-bloque-header { background: linear-gradient(135deg, #1f2937 0%, #374151 100%); padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
    .eq-bloque-titulo { font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 0.3px; }
    .eq-bloque-meta { font-size: 11px; color: #d1d5db; margin-top: 4px; }
    .eq-progress-bar { width: 100%; height: 6px; background: #374151; border-radius: 3px; margin-top: 8px; overflow: hidden; }
    .eq-progress-fill { height: 100%; background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%); border-radius: 3px; transition: width 0.3s ease; }
    .eq-bloque-contenido { padding: 12px 16px; }
    .eq-tabla-header { display: grid; grid-template-columns: 36px 55px 1fr 80px 80px 130px; gap: 8px; padding: 8px 12px; background: #f8f9fa; border-radius: 8px; font-weight: 700; font-size: 10px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; align-items: center; margin-bottom: 6px; }
    .eq-tabla-fila { display: grid; grid-template-columns: 36px 55px 1fr 80px 80px 130px; gap: 8px; padding: 8px 12px; border-bottom: 1px solid #e5e7eb; align-items: center; font-size: 12px; transition: background 0.2s; }
    .eq-tabla-fila:hover { background: #f8f9fa; }
    .eq-tabla-fila:last-child { border-bottom: none; }
    .eq-esp-ele { background: #dbeafe; color: #1e3a8a; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-align: center; display: inline-block; }
    .eq-esp-mec { background: #dcfce7; color: #14532d; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-align: center; display: inline-block; }
    .eq-esp-hid { background: #f3e8ff; color: #581c87; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 800; text-align: center; display: inline-block; }
    .eq-desc { color: #111827; font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .eq-tec { color: #374151; font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
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
    estados = {"Ejecutado": "badge-ejecutado", "Verificado": "badge-verificado", "Pendiente": "badge-pendiente"}
    return estados.get(estado, "badge-pendiente")

def obtener_color_prioridad(prioridad):
    colores = {
        "Rojo": {"label": "CRITICO", "desc": "Si o si se debe realizar"},
        "Amarillo": {"label": "SECUNDARIO", "desc": "Realizar despues de las obligatorias"},
        "Verde": {"label": "ESTANDAR", "desc": "Actividad simple, poco requisito"},
        "": {"label": "SIN CLASIFICAR", "desc": "No definida"}
    }
    return colores.get(prioridad, colores[""])

def obtener_clase_css_prioridad(prioridad):
    clases = {"Rojo": "badge-critico", "Amarillo": "badge-secundario", "Verde": "badge-estandar", "": ""}
    return clases.get(prioridad, "")

def boton_volver_inicio(key_suffix=""):
    if st.button("VOLVER AL INICIO", use_container_width=True, type="secondary", key=gen_key(f"volver_inicio_{key_suffix}")):
        st.session_state.pagina = "home"
        st.session_state.orden_seleccionada = None
        st.session_state.busqueda = ""
        st.rerun()

def boton_cerrar_sesion():
    if st.button("CERRAR SESION", use_container_width=True, type="secondary", key=gen_key("btn_cerrar_sesion")):
        st.session_state.perfil = None
        st.session_state.pagina = "login"
        st.session_state.orden_seleccionada = None
        st.session_state.busqueda = ""
        st.session_state.admin_autenticado = False
        st.rerun()

def obtener_maquinas_disponibles(df):
    if df.empty or "Ubicacion" not in df.columns: return ["Todas"]
    try:
        maquinas = df["Ubicacion"].dropna().unique().tolist()
        maquinas = [m for m in maquinas if str(m).strip()]
        return ["Todas"] + sorted(maquinas)
    except Exception:
        return ["Todas"]

def extraer_maquina_nodo(nodo):
    if pd.isna(nodo) or str(nodo).strip() == "":
        return "SIN_NODO"
    partes = str(nodo).split("-")
    return partes[0] if len(partes) > 0 else str(nodo)

def extraer_subsistema_nodo(nodo):
    if pd.isna(nodo) or str(nodo).strip() == "":
        return "SIN_CODIGO"
    partes = str(nodo).split("-")
    return partes[1] if len(partes) > 1 else "SIN_CODIGO"

def obtener_maquinas_desde_nodo(df):
    if df.empty or "Nodo" not in df.columns:
        return ["Todas"]
    try:
        maquinas = df["Nodo"].dropna().apply(extraer_maquina_nodo).unique().tolist()
        maquinas = [m for m in maquinas if str(m).strip() and str(m).strip() != "SIN_NODO"]
        return ["Todas"] + sorted(maquinas)
    except Exception:
        return ["Todas"]

def obtener_subsistemas_desde_nodo(df, maquina_filtro="Todas"):
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
    if df.empty or "Nodo" not in df.columns:
        return {}
    try:
        maquinas = df["Nodo"].dropna().apply(extraer_maquina_nodo)
        return maquinas.value_counts().to_dict()
    except Exception:
        return {}

def contar_por_subsistema(df, maquina_filtro="Todas"):
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

def calcular_duracion(hora_inicio, hora_fin):
    try:
        if not hora_inicio or not hora_fin:
            return None
        fmt = "%H:%M"
        hi = datetime.strptime(str(hora_inicio).strip(), fmt)
        hf = datetime.strptime(str(hora_fin).strip(), fmt)
        diff = hf - hi
        total_min = int(diff.total_seconds() / 60)
        if total_min < 0:
            total_min += 24 * 60
        horas = total_min // 60
        mins = total_min % 60
        if horas > 0:
            return f"{horas}h {mins}m"
        return f"{mins} min"
    except Exception:
        return None

def obtener_especialidad_tecnico(nombre_tecnico):
    if nombre_tecnico in TECNICOS_ELE:
        return "ELE"
    elif nombre_tecnico in TECNICOS_MEC:
        return "MEC"
    return ""

def contar_ordenes_por_tecnico(df, tecnico_nombre):
    if df.empty or "Tecnico_Asignado" not in df.columns:
        return 0
    try:
        return len(df[df["Tecnico_Asignado"] == tecnico_nombre])
    except Exception:
        return 0

def obtener_tecnicos_con_carga(df, especialidad="Todas"):
    tecnicos = []
    lista_base = []
    if especialidad == "ELE":
        lista_base = TECNICOS_ELE
    elif especialidad == "MEC":
        lista_base = TECNICOS_MEC
    else:
        lista_base = TECNICOS_ELE + TECNICOS_MEC
    for tec in lista_base:
        carga = contar_ordenes_por_tecnico(df, tec)
        esp = obtener_especialidad_tecnico(tec)
        tecnicos.append({"nombre": tec, "especialidad": esp, "carga": carga})
    tecnicos.sort(key=lambda x: x["carga"])
    return tecnicos

def obtener_clase_carga(carga):
    if carga == 0: return "cero"
    elif carga >= 5: return "alta"
    elif carga >= 2: return "media"
    return "baja"

def recargar_datos():
    df = cargar_excel_mantenimiento()
    st.session_state.df_mantenimientos = df
    return df

def toggle_detalle(idx):
    if st.session_state.actividad_expandida == idx:
        st.session_state.actividad_expandida = None
    else:
        st.session_state.actividad_expandida = idx

def gen_key(base, *parts):
    perfil = st.session_state.get("perfil", "none")
    pagina = st.session_state.get("pagina", "none")
    part_str = "_".join(str(p) for p in parts)
    raw = f"{base}_{perfil}_{pagina}_{part_str}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]

def get_row_by_internal_id(df, internal_id):
    if df.empty or "ID" not in df.columns or not internal_id:
        return None, None
    mask = df["ID"].astype(str) == str(internal_id)
    if mask.any():
        idx = df[mask].index[0]
        return idx, df.loc[idx]
    return None, None

# ==================== INICIALIZACION SESSION STATE ====================
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
if "filtro_maquina_nodo" not in st.session_state: st.session_state.filtro_maquina_nodo = "Todas"
if "filtro_subsistema_nodo" not in st.session_state: st.session_state.filtro_subsistema_nodo = "Todos"
if "tecnico_seleccionado" not in st.session_state: st.session_state.tecnico_seleccionado = "Seleccionar tecnico..."
if "tecnico_filtro_especialidad" not in st.session_state: st.session_state.tecnico_filtro_especialidad = "Todas"
if "mostrar_todos_tecnicos" not in st.session_state: st.session_state.mostrar_todos_tecnicos = False
if "asignacion_exitosa" not in st.session_state: st.session_state.asignacion_exitosa = None
if "mostrar_opciones_ordenes" not in st.session_state: st.session_state.mostrar_opciones_ordenes = False
if "actividad_expandida" not in st.session_state: st.session_state.actividad_expandida = None
if "admin_autenticado" not in st.session_state: st.session_state.admin_autenticado = False

# ==================== LOGIN ADMIN (SECRETS) ====================
def autenticar_admin(password):
    admin_pass = st.secrets.get("ADMIN_PASSWORD", "")
    if not admin_pass:
        return False, "ADMIN_PASSWORD no configurado en Secrets"
    if password == admin_pass:
        return True, "OK"
    return False, "Contrasena incorrecta"

def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="sidebar-title">🔧 Mtto Preventivo</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-sub">Navegación</div>', unsafe_allow_html=True)

        nav_items = [
            ("🏠", "Dashboard", "home"),
            ("📋", "Órdenes", "ordenes"),
            ("👷", "Asignación", "asignacion"),
            ("✅", "Verificar", "verificar"),
        ]
        if st.session_state.perfil == "tecnico":
            nav_items = [
                ("🏠", "Dashboard", "home"),
                ("📋", "Mis Órdenes", "mis_ordenes"),
            ]

        for icon, label, page in nav_items:
            btn_type = "primary" if st.session_state.pagina == page else "secondary"
            if st.button(f"{icon} {label}", use_container_width=True, type=btn_type, key=f"nav_{page}"):
                st.session_state.pagina = page
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-sub">Filtros Globales</div>', unsafe_allow_html=True)

        esp_sel = st.selectbox("Especialidad", ["Todas", "ELE", "MEC"], 
                               index=["Todas", "ELE", "MEC"].index(st.session_state.filtro_especialidad),
                               key="sidebar_esp")
        if esp_sel != st.session_state.filtro_especialidad:
            st.session_state.filtro_especialidad = esp_sel
            st.rerun()

        df = st.session_state.df_mantenimientos
        maquinas = obtener_maquinas_desde_nodo(df)
        idx_maq = maquinas.index(st.session_state.filtro_maquina_nodo) if st.session_state.filtro_maquina_nodo in maquinas else 0
        maq_sel = st.selectbox("Máquina", maquinas, index=idx_maq, key="sidebar_maq")
        if maq_sel != st.session_state.filtro_maquina_nodo:
            st.session_state.filtro_maquina_nodo = maq_sel
            st.session_state.filtro_subsistema_nodo = "Todos"
            st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary", key="sidebar_logout"):
            st.session_state.perfil = None
            st.session_state.pagina = "login"
            st.session_state.orden_seleccionada = None
            st.session_state.busqueda = ""
            st.session_state.admin_autenticado = False
            st.rerun()

def render_top_bar(titulo):
    perfil_label = "Administrador" if st.session_state.perfil == "admin" else "Técnico"
    st.markdown(f"""
    <div class="top-bar">
        <div class="top-bar-title">{titulo}</div>
        <div class="top-bar-user">{perfil_label} • {datetime.now().strftime('%d/%m/%Y')}</div>
    </div>
    """, unsafe_allow_html=True)

def pantalla_login():
    st.markdown("""
    <style>
        .login-container { max-width: 420px; margin: 0 auto; padding-top: 80px; }
        .login-card { background: white; border-radius: 16px; padding: 40px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; }
        .login-title { font-size: 24px; font-weight: 800; color: #111827; margin-bottom: 8px; }
        .login-sub { font-size: 14px; color: #6b7280; margin-bottom: 32px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-container">
        <div class="login-card">
            <div style="font-size: 48px; margin-bottom: 16px;">🔧</div>
            <div class="login-title">Mantenimiento Preventivo</div>
            <div class="login-sub">Selecciona tu perfil para acceder al sistema</div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👤 ADMIN", use_container_width=True, type="primary", key=gen_key("login_admin")):
            st.session_state.perfil = "admin"
            st.session_state.admin_autenticado = True
            st.session_state.pagina = "home"
            st.rerun()
    with col2:
        if st.button("🔧 TÉCNICO", use_container_width=True, type="primary", key=gen_key("login_tecnico")):
            st.session_state.perfil = "tecnico"
            st.session_state.pagina = "home"
            st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

def pantalla_home():
    df = recargar_datos()
    perfil = st.session_state.perfil
    render_top_bar("Dashboard")

    if perfil == "admin":
        # ========== KPIs DE ASIGNACIÓN (PRINCIPAL) ==========
        total = len(df)
        con_tecnico = len(df[df["Tecnico_Asignado"].fillna("") != ""]) if "Tecnico_Asignado" in df.columns else 0
        sin_tecnico = total - con_tecnico
        pct_asignado = round((con_tecnico / total) * 100, 1) if total > 0 else 0
        pct_sin = round((sin_tecnico / total) * 100, 1) if total > 0 else 0
        ele_count = len(df[df["Especialidad"] == "ELE"]) if "Especialidad" in df.columns else 0
        mec_count = len(df[df["Especialidad"] == "MEC"]) if "Especialidad" in df.columns else 0
        pendientes = len(df[df["Estado"] == "Pendiente"]) if "Estado" in df.columns else 0
        ejecutadas = len(df[df["Estado"] == "Ejecutado"]) if "Estado" in df.columns else 0
        verificadas = len(df[df["Estado"] == "Verificado"]) if "Estado" in df.columns else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Total Órdenes</div>
                <div class="kpi-value">{total}</div>
                <div class="kpi-delta" style="color:#6b7280">{ele_count} ELE • {mec_count} MEC</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Sin Asignar</div>
                <div class="kpi-value" style="color:#dc2626">{sin_tecnico}</div>
                <div class="kpi-delta" style="color:#dc2626">{pct_sin}% del total</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Asignadas</div>
                <div class="kpi-value" style="color:#22c55e">{con_tecnico}</div>
                <div class="kpi-delta" style="color:#22c55e">{pct_asignado}% del total</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Pendientes</div>
                <div class="kpi-value" style="color:#f59e0b">{pendientes}</div>
                <div class="kpi-delta" style="color:#f59e0b">Por ejecutar</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ========== GRÁFICAS DE ASIGNACIÓN ==========
        g1, g2 = st.columns(2)
        with g1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">Estado de Asignación</div>', unsafe_allow_html=True)
            if total > 0:
                asig_data = pd.DataFrame({
                    "Estado": ["Asignadas", "Sin Asignar"],
                    "Cantidad": [con_tecnico, sin_tecnico]
                })
                fig = px.pie(asig_data, values="Cantidad", names="Estado", hole=0.55,
                             color="Estado", color_discrete_map={"Asignadas": "#22c55e", "Sin Asignar": "#dc2626"})
                fig.update_layout(showlegend=True, margin=dict(t=0,b=0,l=0,r=0), height=260,
                                  paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                  font=dict(family="Inter", size=12))
                st.plotly_chart(fig, use_container_width=True, key="home_chart_asig")
            else:
                st.info("Sin datos")
            st.markdown('</div>', unsafe_allow_html=True)

        with g2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">Órdenes por Estado</div>', unsafe_allow_html=True)
            if "Estado" in df.columns and not df.empty:
                est_counts = df["Estado"].value_counts().reset_index()
                est_counts.columns = ["Estado", "Cantidad"]
                color_map = {"Pendiente": "#f59e0b", "Ejecutado": "#10b981", "Verificado": "#3b82f6"}
                fig2 = px.bar(est_counts, x="Estado", y="Cantidad", color="Estado",
                              color_discrete_map=color_map, text="Cantidad")
                fig2.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), height=260,
                                   paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                   font=dict(family="Inter", size=12),
                                   xaxis=dict(showgrid=False),
                                   yaxis=dict(showgrid=True, gridcolor='#f3f4f6'))
                st.plotly_chart(fig2, use_container_width=True, key="home_chart_est")
            else:
                st.info("Sin datos")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ========== GRID DE UBICACIONES PARA ASIGNAR RÁPIDO ==========
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">📍 Ubicaciones — Click para asignar técnicos</div>', unsafe_allow_html=True)

        df_ubic = df.copy()
        if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_ubic.columns:
            df_ubic = df_ubic[df_ubic["Especialidad"] == st.session_state.filtro_especialidad]
        if st.session_state.filtro_maquina_nodo != "Todas" and "Nodo" in df_ubic.columns:
            df_ubic = df_ubic[df_ubic["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]

        if "Ubicacion" not in df_ubic.columns or df_ubic.empty:
            st.info("No hay ubicaciones disponibles.")
        else:
            ubicaciones = df_ubic["Ubicacion"].dropna().unique()
            if len(ubicaciones) == 0:
                st.info("No hay ubicaciones disponibles.")
            else:
                cols_por_fila = 3
                for i in range(0, len(ubicaciones), cols_por_fila):
                    cols = st.columns(cols_por_fila)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx >= len(ubicaciones):
                            break
                        ubi = ubicaciones[idx]
                        df_u = df_ubic[df_ubic["Ubicacion"] == ubi]
                        total_u = len(df_u)
                        sin_a = len(df_u[df_u["Tecnico_Asignado"].fillna("") == ""]) if "Tecnico_Asignado" in df_u.columns else 0
                        asig_u = total_u - sin_a
                        pct_u = round((asig_u / total_u) * 100, 1) if total_u > 0 else 0
                        ele_u = len(df_u[df_u["Especialidad"] == "ELE"]) if "Especialidad" in df_u.columns else 0
                        mec_u = len(df_u[df_u["Especialidad"] == "MEC"]) if "Especialidad" in df_u.columns else 0
                        pend_u = len(df_u[df_u["Estado"] == "Pendiente"]) if "Estado" in df_u.columns else 0

                        with col:
                            color_barra = "#dc2626" if sin_a > 0 else "#22c55e"
                            badge = f'<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700;">{sin_a} sin asignar</span>' if sin_a > 0 else '<span style="background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700;">✓ Asignado</span>'
                            st.markdown(f"""
                            <div style="background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-bottom: 12px; transition: all 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                                <div style="width: 100%; height: 4px; background: {color_barra}; border-radius: 2px; margin-bottom: 10px;"></div>
                                <div style="font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{ubi}">{ubi}</div>
                                <div style="display: flex; gap: 6px; margin-bottom: 8px;">
                                    {badge}
                                    <span style="background: #f3f4f6; color: #374151; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600;">{total_u} act.</span>
                                </div>
                                <div style="font-size: 11px; color: #6b7280; line-height: 1.5; margin-bottom: 8px;">
                                    {f"🔌 {ele_u} ELE • " if ele_u > 0 else ""}{f"🔧 {mec_u} MEC • " if mec_u > 0 else ""}{f"⏳ {pend_u} pend." if pend_u > 0 else ""}
                                </div>
                                <div style="width: 100%; height: 6px; background: #f3f4f6; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {pct_u}%; height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); border-radius: 3px;"></div>
                                </div>
                                <div style="font-size: 10px; color: #6b7280; text-align: right; margin-top: 4px;">{pct_u}% asignado</div>
                            </div>
                            """, unsafe_allow_html=True)
                            btn_key = gen_key("btn_home_ubi", ubi.replace(" ", "_").replace("-", "_"))
                            if st.button(f"ASIGNAR TÉCNICOS →", use_container_width=True, type="primary", key=btn_key):
                                st.session_state.ubicacion_asig_seleccionada = ubi
                                st.session_state.pagina = "asignacion"
                                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ========== ACCIONES RÁPIDAS ==========
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Acciones Rápidas</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📋 Ver Todas las Órdenes", use_container_width=True, type="primary", key=gen_key("btn_ver_todas_home")):
                st.session_state.pagina = "ordenes"; st.rerun()
        with c2:
            if st.button("👷 Ir a Asignación", use_container_width=True, type="primary", key=gen_key("btn_asignacion_home")):
                st.session_state.ubicacion_asig_seleccionada = None
                st.session_state.pagina = "asignacion"; st.rerun()
        with c3:
            if st.button("📧 Enviar Reporte", use_container_width=True, type="primary", key=gen_key("btn_abrir_correo_home")):
                st.session_state.mostrar_envio_correo = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.mostrar_envio_correo:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<div class="card-header">Enviar Resumen por Correo</div>', unsafe_allow_html=True)
            df_envio = df.copy()
            if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_envio.columns:
                df_envio = df_envio[df_envio["Especialidad"] == st.session_state.filtro_especialidad]
            if st.session_state.filtro_maquina_nodo != "Todas" and "Nodo" in df_envio.columns:
                df_envio = df_envio[df_envio["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]

            pct_ejec, pct_pdte, pct_verif = calcular_progreso(df_envio)
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Ejecutadas", f"{pct_ejec}%")
            with c2: st.metric("Pendientes", f"{pct_pdte}%")
            with c3: st.metric("Verificar", f"{pct_verif}%")

            st.write(f"**Total de ordenes a enviar:** {len(df_envio)}")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                cuenta = st.radio("Cuenta de envio:", [
                    "mantobogota@gmail.com",
                    "supermantobogota@gmail.com"
                ], key=gen_key("radio_cuenta_correo_home"))
            with col_c2:
                area = st.text_input("Area / Proyecto", value="INY4 MEC", key=gen_key("txt_area_correo_home"))
            asunto = st.text_input("Asunto del correo", value=f"Ordenes preventivas {area}", key=gen_key("txt_asunto_correo_home"))
            destinatarios_text = st.text_area(
                "Destinatarios:",
                value="\n".join(DESTINATARIOS_DEFAULT),
                disabled=True,
                key=gen_key("txt_destinatarios_home")
            )
            col_env1, col_env2 = st.columns(2)
            with col_env1:
                if st.button("ENVIAR CORREO AHORA", use_container_width=True, type="primary", key=gen_key("btn_enviar_correo_home")):
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
                if st.button("CANCELAR", use_container_width=True, type="secondary", key=gen_key("btn_cancelar_correo_home")):
                    st.session_state.mostrar_envio_correo = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    elif perfil == "tecnico":
        tecnicos_info = obtener_tecnicos_con_carga(df, "Todas")
        opciones_tec = ["Seleccionar tecnico..."] + [t["nombre"] for t in tecnicos_info]
        idx_tec = 0
        if st.session_state.tecnico_seleccionado != "Seleccionar tecnico...":
            for i, t in enumerate(tecnicos_info):
                if t["nombre"] == st.session_state.tecnico_seleccionado:
                    idx_tec = i + 1
                    break

        tecnico_sel = st.selectbox("Selecciona tu nombre:", opciones_tec, index=idx_tec, key=gen_key("sel_tecnico_home2"))
        if tecnico_sel != "Seleccionar tecnico...":
            st.session_state.tecnico_seleccionado = tecnico_sel
        else:
            st.session_state.tecnico_seleccionado = "Seleccionar tecnico..."

        if st.session_state.tecnico_seleccionado != "Seleccionar tecnico...":
            tecnico_actual = st.session_state.tecnico_seleccionado
            esp_sel = obtener_especialidad_tecnico(tecnico_actual)
            df = recargar_datos()
            df_mias = df.copy()
            if "Tecnico_Asignado" in df_mias.columns:
                df_mias = df_mias[df_mias["Tecnico_Asignado"] == tecnico_actual]

            total_asignadas = len(df_mias)
            pendientes = len(df_mias[df_mias["Estado"] == "Pendiente"]) if "Estado" in df_mias.columns else 0
            ejecutadas = len(df_mias[df_mias["Estado"] == "Ejecutado"]) if "Estado" in df_mias.columns else 0
            verificadas = len(df_mias[df_mias["Estado"] == "Verificado"]) if "Estado" in df_mias.columns else 0

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'''
                <div class="kpi-card">
                    <div class="kpi-label">Total Asignadas</div>
                    <div class="kpi-value">{total_asignadas}</div>
                </div>''', unsafe_allow_html=True)
            with c2:
                st.markdown(f'''
                <div class="kpi-card">
                    <div class="kpi-label">Pendientes</div>
                    <div class="kpi-value" style="color:#f59e0b">{pendientes}</div>
                </div>''', unsafe_allow_html=True)
            with c3:
                st.markdown(f'''
                <div class="kpi-card">
                    <div class="kpi-label">Ejecutadas</div>
                    <div class="kpi-value" style="color:#10b981">{ejecutadas}</div>
                </div>''', unsafe_allow_html=True)
            with c4:
                st.markdown(f'''
                <div class="kpi-card">
                    <div class="kpi-label">Verificadas</div>
                    <div class="kpi-value" style="color:#3b82f6">{verificadas}</div>
                </div>''', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            grupos = df_mias.groupby(["Equipo", "Ubicacion"])
            for (equipo, ubicacion), grupo_df in grupos:
                total_act = len(grupo_df)
                tecnico_bloque = grupo_df["Tecnico_Asignado"].mode()
                tecnico_bloque = tecnico_bloque[0] if len(tecnico_bloque) > 0 else "Sin asignar"
                bloque_key = f"{equipo}_{ubicacion}".replace(" ", "_").replace("-", "_")

                realizadas_chk = 0
                for idx, row in grupo_df.iterrows():
                    internal_id = limpiar(row.get("ID"), "")
                    chk_key = gen_key("chk_eq", internal_id)
                    if st.session_state.get(chk_key, False):
                        realizadas_chk += 1
                pct_realizadas = round((realizadas_chk / total_act) * 100, 1) if total_act > 0 else 0
                estado_bloque = "Completado" if realizadas_chk == total_act and total_act > 0 else "Pendiente"
                clase_est_bloque = "badge-ejecutado" if estado_bloque == "Completado" else "badge-pendiente"

                st.markdown(f"""
                <div class="eq-bloque">
                    <div class="eq-bloque-header">
                        <div style="flex:1; min-width:0;">
                            <div class="eq-bloque-titulo">🔧 {equipo} — {ubicacion}</div>
                            <div class="eq-bloque-meta">
                                👤 {tecnico_bloque} | 📋 {total_act} actividades | ✅ {realizadas_chk} realizadas
                            </div>
                            <div class="eq-progress-bar">
                                <div class="eq-progress-fill" style="width: {pct_realizadas}%;"></div>
                            </div>
                        </div>
                        <span class="badge {clase_est_bloque}" style="margin-left:12px; flex-shrink:0;">{estado_bloque}</span>
                    </div>
                    <div class="eq-bloque-contenido">
                        <div class="eq-tabla-header">
                            <div style="text-align:center">✓</div>
                            <div>ESP</div>
                            <div>DESCRIPCION</div>
                            <div style="text-align:center">ESTADO</div>
                            <div style="text-align:center">TIEMPO</div>
                            <div>TECNICO</div>
                        </div>
                """, unsafe_allow_html=True)

                lista_marcar_key = f"lista_marcar_{bloque_key}"
                ids_a_marcar = set()
                if lista_marcar_key in st.session_state:
                    ids_a_marcar = set(st.session_state[lista_marcar_key])
                    for internal_id in ids_a_marcar:
                        chk_key = gen_key("chk_eq", internal_id)
                        if chk_key in st.session_state:
                            del st.session_state[chk_key]
                        prev_key = f"prev_{chk_key}"
                        if prev_key in st.session_state:
                            del st.session_state[prev_key]
                        hora_auto_key = f"hora_ini_auto_{internal_id}"
                        if hora_auto_key in st.session_state:
                            del st.session_state[hora_auto_key]
                    del st.session_state[lista_marcar_key]

                for idx, row in grupo_df.iterrows():
                    internal_id = limpiar(row.get("ID"), "")
                    esp = limpiar(row.get("Especialidad"), "")
                    desc = limpiar(row.get("Descripcion de procedimiento"), "Sin descripcion")
                    estado = limpiar(row.get("Estado"), "Pendiente")
                    tecnico = limpiar(row.get("Tecnico_Asignado"), "Sin asignar")

                    chk_key = gen_key("chk_eq", internal_id)
                    ya_ejecutado = estado == "Ejecutado"
                    valor_inicial = ya_ejecutado or (internal_id in ids_a_marcar)
                    if chk_key not in st.session_state:
                        st.session_state[chk_key] = valor_inicial

                    clase_esp = "eq-esp-ele" if esp == "ELE" else "eq-esp-mec" if esp == "MEC" else "eq-esp-hid" if esp == "HID" else ""
                    clase_est = "badge-ejecutado" if estado == "Ejecutado" else "badge-verificado" if estado == "Verificado" else "badge-pendiente"

                    h_ini = limpiar(row.get("Hora_Inicio"), "")
                    h_fin = limpiar(row.get("Hora_Fin"), "")
                    duracion = calcular_duracion(h_ini, h_fin)

                    cols = st.columns([0.4, 0.6, 2.6, 0.8, 1.1, 1.2])
                    with cols[0]:
                        chk_val = st.checkbox("", value=valor_inicial, key=chk_key, label_visibility="collapsed")
                        prev_key = f"prev_{chk_key}"
                        prev_val = st.session_state.get(prev_key, False)
                        if chk_val and not prev_val and estado not in ["Ejecutado", "Verificado"]:
                            st.session_state[f"hora_ini_auto_{internal_id}"] = datetime.now().strftime("%H:%M")
                        st.session_state[prev_key] = chk_val
                    with cols[1]:
                        st.markdown(f'<span class="{clase_esp}">{esp}</span>', unsafe_allow_html=True)
                    with cols[2]:
                        st.markdown(f'<span class="eq-desc" title="{desc}">{desc}</span>', unsafe_allow_html=True)
                    with cols[3]:
                        st.markdown(f'<span class="badge {clase_est}">{estado}</span>', unsafe_allow_html=True)
                    with cols[4]:
                        hora_ini_auto = st.session_state.get(f"hora_ini_auto_{internal_id}", "")
                        if estado == "Ejecutado" and duracion:
                            st.markdown(f'<div style="text-align:center; background:#d1fae5; color:#065f46; padding:3px 6px; border-radius:6px; font-size:11px; font-weight:700;">✅ {duracion}</div>', unsafe_allow_html=True)
                        elif hora_ini_auto and estado not in ["Ejecutado", "Verificado"]:
                            st.markdown(f'<div style="text-align:center; background:#dbeafe; color:#1e40af; padding:3px 6px; border-radius:6px; font-size:10px; font-weight:600;">⏱ {hora_ini_auto}</div>', unsafe_allow_html=True)
                        elif h_ini and not h_fin:
                            st.markdown(f'<div style="text-align:center; background:#dbeafe; color:#1e40af; padding:3px 6px; border-radius:6px; font-size:10px; font-weight:600;">⏱ {h_ini}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div style="text-align:center; color:#9ca3af; font-size:11px;">—</div>', unsafe_allow_html=True)
                    with cols[5]:
                        st.markdown(f'<span class="eq-tec">{tecnico}</span>', unsafe_allow_html=True)

                st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
                col_marcar, col_guardar = st.columns(2)
                with col_marcar:
                    if st.button("✅ Marcar todas realizadas", use_container_width=True, type="primary", key=gen_key("btn_marcar_todas", bloque_key)):
                        ids_lista = []
                        for idx, row in grupo_df.iterrows():
                            internal_id = limpiar(row.get("ID"), "")
                            ids_lista.append(internal_id)
                        st.session_state[lista_marcar_key] = ids_lista
                        st.rerun()
                with col_guardar:
                    if st.button("💾 Guardar cambios", use_container_width=True, type="primary", key=gen_key("btn_guardar_bloque", bloque_key)):
                        guardados = 0
                        for idx, row in grupo_df.iterrows():
                            internal_id = limpiar(row.get("ID"), "")
                            chk_key = gen_key("chk_eq", internal_id)
                            chk_val = st.session_state.get(chk_key, False)
                            estado_actual = limpiar(row.get("Estado"), "Pendiente")
                            h_ini_bd = limpiar(row.get("Hora_Inicio"), "")
                            h_fin_bd = limpiar(row.get("Hora_Fin"), "")
                            hora_ini_auto = st.session_state.get(f"hora_ini_auto_{internal_id}", "")

                            if chk_val and estado_actual not in ["Ejecutado", "Verificado"]:
                                hora_fin = datetime.now().strftime("%H:%M")
                                hora_ini = hora_ini_auto if hora_ini_auto else (h_ini_bd if h_ini_bd else hora_fin)
                                datos = {
                                    "Estado": "Ejecutado",
                                    "Hora_Inicio": hora_ini,
                                    "Hora_Fin": hora_fin,
                                    "Fecha_Ejecucion": datetime.now().strftime("%Y-%m-%d")
                                }
                                if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
                                    guardados += 1
                                    if f"hora_ini_auto_{internal_id}" in st.session_state:
                                        del st.session_state[f"hora_ini_auto_{internal_id}"]
                            elif not chk_val and estado_actual == "Ejecutado":
                                if actualizar_orden_supabase(internal_id, "Estado", "Pendiente"):
                                    guardados += 1

                        if guardados > 0:
                            st.success(f"{guardados} cambios guardados en Supabase")
                            st.rerun()
                        else:
                            st.info("No hay cambios para guardar")

                st.markdown("</div></div>", unsafe_allow_html=True)
def pantalla_ordenes():
    df = recargar_datos()
    perfil = st.session_state.perfil
    render_top_bar("Órdenes Preventivas")
    boton_volver_inicio("ordenes")
    busqueda = st.text_input("Buscar ID OT, equipo o descripcion...", value=st.session_state.busqueda, placeholder="Escribe para buscar...", key=gen_key("txt_busqueda_ordenes"))
    st.session_state.busqueda = busqueda
    pct_ejec, pct_pdte, pct_verif = calcular_progreso(df)
    st.markdown(f"""
    <div style="display:flex; gap:15px; justify-content:center; margin:15px 0; padding:12px; background:white; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <div style="text-align:center;"><div style="font-size:22px; font-weight:800; color:#10b981">{pct_ejec}%</div><div style="font-size:11px; color:#666;">Ejecutado</div></div>
        <div style="text-align:center;"><div style="font-size:22px; font-weight:800; color:#f59e0b">{pct_pdte}%</div><div style="font-size:11px; color:#666;">Pendiente</div></div>
        <div style="text-align:center;"><div style="font-size:22px; font-weight:800; color:#3b82f6">{pct_verif}%</div><div style="font-size:11px; color:#666;">Verificado</div></div>
    </div>
    """, unsafe_allow_html=True)
    df_filtrado = df.copy()
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Especialidad"] == st.session_state.filtro_especialidad]
    if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Ubicacion"] == st.session_state.filtro_maquina]
    if "Nodo" in df_filtrado.columns and st.session_state.filtro_maquina_nodo != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
    if "Nodo" in df_filtrado.columns and st.session_state.filtro_subsistema_nodo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]
    if busqueda:
        busqueda_lower = busqueda.lower()
        mask = pd.Series([False] * len(df_filtrado), index=df_filtrado.index)
        if "Equipo" in df_filtrado.columns: mask |= df_filtrado["Equipo"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "Ubicacion" in df_filtrado.columns: mask |= df_filtrado["Ubicacion"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "ID OT" in df_filtrado.columns: mask |= df_filtrado["ID OT"].astype(str).str.contains(busqueda, na=False)
        if "Descripcion de procedimiento" in df_filtrado.columns: mask |= df_filtrado["Descripcion de procedimiento"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "Nodo" in df_filtrado.columns: mask |= df_filtrado["Nodo"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        df_filtrado = df_filtrado[mask]
    st.subheader(f"Ordenes ({len(df_filtrado)})")
    st.markdown("""
    <div style="display: grid; background: #f8f9fa; color: #6c757d; grid-template-columns: 70px 45px 1fr 90px 110px; gap: 6px; padding: 8px 10px; border-bottom: 2px solid #dee2e6; font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; align-items: center; margin-bottom: 6px;">
        <div class="col-id">ID OT</div><div class="col-esp">ESP</div><div class="col-desc">DESCRIPCION</div>
        <div class="col-estado">ESTADO</div><div class="col-tec">TECNICO</div>
    </div>
    """, unsafe_allow_html=True)
    for idx, row in df_filtrado.iterrows():
        id_ot = limpiar(row.get("ID OT"), "SIN ID")
        internal_id = limpiar(row.get("ID"), "")
        tipo = limpiar(row.get("Especialidad"), "SIN ESP")
        descripcion = limpiar(row.get("Descripcion de procedimiento"), "Sin descripcion")
        estado = limpiar(row.get("Estado"), "Pendiente")
        tecnico = limpiar(row.get("Tecnico_Asignado"), "Sin asignar")
        estado_clase = obtener_estado_visual(estado)
        desc_corta = descripcion[:35] + "..." if len(descripcion) > 35 else descripcion
        prioridad = limpiar(row.get("Prioridad_Actividad"), "")
        clase_prioridad = obtener_clase_css_prioridad(prioridad)
        nodo = limpiar(row.get("Nodo"), "")
        nodo_html = f"<span class='nodo-badge-mini' style='margin-left:4px;'>{nodo}</span>" if nodo else ""
        st.markdown(f"""
        <div class="tabla-fila {clase_prioridad}">
            <div class="col-id"><strong>{id_ot}</strong>{nodo_html}</div>
            <div class="col-esp">{tipo}</div>
            <div class="col-desc" title="{descripcion}">{desc_corta}</div>
            <div class="col-estado"><span class="badge {estado_clase}">{estado}</span></div>
            <div class="col-tec">{tecnico}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Ver detalle", key=gen_key("btn_ver", internal_id), use_container_width=True):
            st.session_state.orden_seleccionada = internal_id
            st.session_state.pagina = "detalle"
            st.rerun()


def pantalla_mis_ordenes():
    df = recargar_datos()
    render_top_bar("Mis Órdenes Asignadas")
    boton_volver_inicio("mis_ordenes")
    tecnico_sel = st.session_state.get("tecnico_seleccionado", "Seleccionar tecnico...")
    if tecnico_sel == "Seleccionar tecnico...":
        st.warning("Por favor selecciona tu nombre en la pantalla principal.")
        if st.button("VOLVER AL INICIO", use_container_width=True, key=gen_key("btn_volver_sel_tec")):
            st.session_state.pagina = "home"; st.rerun()
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_estado_tec = st.selectbox("Filtrar por estado", ["Todos", "Pendiente", "Ejecutado", "Verificado"], 
                                          index=0, key=gen_key("filtro_estado_tec"))
    with col_f2:
        busq_tec = st.text_input("Buscar...", placeholder="ID OT o equipo", key=gen_key("busq_tec"))

    df_mias = df.copy()
    if "Tecnico_Asignado" in df_mias.columns:
        df_mias = df_mias[df_mias["Tecnico_Asignado"] == tecnico_sel]
    else:
        df_mias = pd.DataFrame()

    if filtro_estado_tec != "Todos" and "Estado" in df_mias.columns:
        df_mias = df_mias[df_mias["Estado"] == filtro_estado_tec]

    if busq_tec:
        busq_lower = busq_tec.lower()
        mask = pd.Series([False] * len(df_mias), index=df_mias.index)
        if "ID OT" in df_mias.columns: mask |= df_mias["ID OT"].astype(str).str.contains(busq_tec, na=False)
        if "Equipo" in df_mias.columns: mask |= df_mias["Equipo"].astype(str).str.lower().str.contains(busq_lower, na=False)
        df_mias = df_mias[mask]

    esp_tec = obtener_especialidad_tecnico(tecnico_sel)

    total_asignadas = len(df[df["Tecnico_Asignado"] == tecnico_sel]) if "Tecnico_Asignado" in df.columns else 0
    pendientes = len(df[(df["Tecnico_Asignado"] == tecnico_sel) & (df["Estado"] == "Pendiente")]) if "Tecnico_Asignado" in df.columns else 0
    ejecutadas = len(df[(df["Tecnico_Asignado"] == tecnico_sel) & (df["Estado"] == "Ejecutado")]) if "Tecnico_Asignado" in df.columns else 0

    st.markdown(f"""
    <div style="display: flex; gap: 10px; justify-content: center; margin: 10px 0;">
        <div style="background: white; padding: 8px 15px; border-radius: 8px; text-align: center; border: 2px solid #1a237e;">
            <div style="font-size: 20px; font-weight: 800; color: #1a237e;">{total_asignadas}</div>
            <div style="font-size: 10px; color: #666;">Total Asignadas</div>
        </div>
        <div style="background: white; padding: 8px 15px; border-radius: 8px; text-align: center; border: 2px solid #ffc107;">
            <div style="font-size: 20px; font-weight: 800; color: #ffc107;">{pendientes}</div>
            <div style="font-size: 10px; color: #666;">Pendientes</div>
        </div>
        <div style="background: white; padding: 8px 15px; border-radius: 8px; text-align: center; border: 2px solid #28a745;">
            <div style="font-size: 20px; font-weight: 800; color: #28a745;">{ejecutadas}</div>
            <div style="font-size: 10px; color: #666;">Ejecutadas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader(f"Mostrando {len(df_mias)} orden(es)")

    if df_mias.empty:
        st.info("No tienes ordenes con los filtros seleccionados.")
        return

    for idx, row in df_mias.iterrows():
        id_ot = limpiar(row.get("ID OT"), "SIN ID")
        internal_id = limpiar(row.get("ID"), "")
        tipo = limpiar(row.get("Especialidad"), "SIN ESP")
        descripcion = limpiar(row.get("Descripcion de procedimiento"), "Sin descripcion")
        estado = limpiar(row.get("Estado"), "Pendiente")
        tecnico = limpiar(row.get("Tecnico_Asignado"), "Sin asignar")
        estado_clase = obtener_estado_visual(estado)
        desc_corta = descripcion[:35] + "..." if len(descripcion) > 35 else descripcion
        prioridad = limpiar(row.get("Prioridad_Actividad"), "")
        clase_prioridad = obtener_clase_css_prioridad(prioridad)
        nodo = limpiar(row.get("Nodo"), "")
        nodo_html = f"<span class='nodo-badge-mini' style='margin-left:4px;'>{nodo}</span>" if nodo else ""
        st.markdown(f"""
        <div class="tabla-fila {clase_prioridad}">
            <div class="col-id"><strong>{id_ot}</strong>{nodo_html}</div>
            <div class="col-esp">{tipo}</div>
            <div class="col-desc" title="{descripcion}">{desc_corta}</div>
            <div class="col-estado"><span class="badge {estado_clase}">{estado}</span></div>
            <div class="col-tec">{tecnico[:15]}...</div>
        </div>
        """, unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Ver detalle", key=gen_key("btn_ver_tec", internal_id), use_container_width=True):
                st.session_state.orden_seleccionada = internal_id
                st.session_state.pagina = "detalle_tecnico"
                st.rerun()
        with col2:
            if estado == "Pendiente" and st.button(f"Ejecutar", key=gen_key("btn_ejec", internal_id), use_container_width=True, type="primary"):
                st.session_state.orden_seleccionada = internal_id
                st.session_state.pagina = "ejecutar"
                st.rerun()


def pantalla_ejecutar():
    df = recargar_datos()
    internal_id = st.session_state.orden_seleccionada
    idx, row = get_row_by_internal_id(df, internal_id)
    if idx is None:
        st.error("Orden no encontrada.")
        if st.button("Volver a Mis Ordenes", use_container_width=True, key=gen_key("ejec_volver_error")):
            st.session_state.pagina = "mis_ordenes"
            st.session_state.orden_seleccionada = None
            st.rerun()
        return

    id_ot = limpiar(row.get("ID OT"), "SIN ID")
    render_top_bar(f"Ejecutar OT {id_ot}")
    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("Volver", use_container_width=True, type="secondary", key=gen_key("ejec_volver")):
            st.session_state.pagina = "mis_ordenes"; st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key=gen_key("ejec_inicio")):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()
    nodo_info = f"<strong>Nodo:</strong> {limpiar(row.get('Nodo'), 'N/A')}<br>" if 'Nodo' in row else ""
    st.markdown(f"""
    <div class="detail-panel" style="background: white; border: 1px solid #e5e7eb;">
        <div class="equipo-info">
            {nodo_info}
            <strong>Equipo:</strong> {limpiar(row.get('Equipo'), 'N/A')}<br>
            <strong>Ubicacion:</strong> {limpiar(row.get('Ubicacion'), 'N/A')}<br>
            <strong>Especialidad:</strong> {limpiar(row.get('Especialidad'), 'N/A')}<br>
            <strong>Estado actual:</strong> {limpiar(row.get('Estado'), 'Pendiente')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.subheader("Descripcion del Procedimiento")
    st.write(limpiar(row.get("Descripcion de procedimiento"), "Sin descripcion"))
    st.subheader("Registro de Ejecucion")

    h_ini_str = limpiar(row.get("Hora_Inicio"), "")
    h_fin_str = limpiar(row.get("Hora_Fin"), "")
    try:
        h_ini_default = datetime.strptime(h_ini_str, "%H:%M").time() if h_ini_str else datetime.now().time()
    except:
        h_ini_default = datetime.now().time()
    try:
        h_fin_default = datetime.strptime(h_fin_str, "%H:%M").time() if h_fin_str else datetime.now().time()
    except:
        h_fin_default = datetime.now().time()

    col1, col2 = st.columns(2)
    with col1:
        hora_inicio = st.time_input("Hora Inicio", value=h_ini_default, key=gen_key("hora_inicio_ejec"))
    with col2:
        hora_fin = st.time_input("Hora Fin", value=h_fin_default, key=gen_key("hora_fin_ejec"))
    st.subheader("Comentarios de Ejecucion")
    comentarios = limpiar(row.get("Comentarios"), "")
    nuevo_comentario = st.text_area("Describa lo realizado...", value=comentarios, key=gen_key("comentario_ejecucion"))
    hora_valida = True
    if hora_fin < hora_inicio:
        st.warning("⚠️ La hora de fin es anterior a la hora de inicio. Por favor verifica.")
        hora_valida = False

    if st.button("MARCAR COMO EJECUTADO", use_container_width=True, type="primary", key=gen_key("btn_marcar_ejecutado"), disabled=not hora_valida):
        datos = {
            "Estado": "Ejecutado",
            "Comentarios": nuevo_comentario,
            "Fecha_Ejecucion": datetime.now().strftime("%Y-%m-%d"),
            "Hora_Inicio": hora_inicio.strftime("%H:%M"),
            "Hora_Fin": hora_fin.strftime("%H:%M")
        }
        if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
            df.at[idx, "Estado"] = "Ejecutado"
            df.at[idx, "Comentarios"] = nuevo_comentario
            df.at[idx, "Fecha_Ejecucion"] = datos["Fecha_Ejecucion"]
            df.at[idx, "Hora_Inicio"] = datos["Hora_Inicio"]
            df.at[idx, "Hora_Fin"] = datos["Hora_Fin"]
            st.markdown("""
            <div style="background: #d1fae5; color: #065f46; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; border: 1px solid #059669; margin: 12px 0;">
                ✅ Orden marcada como EJECUTADA y guardada en Supabase
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
            st.session_state.pagina = "mis_ordenes"
            st.session_state.orden_seleccionada = None
            st.rerun()
        else:
            st.error("Error al guardar en Supabase. Intenta de nuevo.")


def pantalla_detalle_tecnico():
    df = recargar_datos()
    internal_id = st.session_state.orden_seleccionada
    idx, row = get_row_by_internal_id(df, internal_id)
    if idx is None:
        st.error("Orden no encontrada.")
        if st.button("Volver", use_container_width=True, key=gen_key("dettec_volver_err")):
            st.session_state.pagina = "mis_ordenes"; st.session_state.orden_seleccionada = None; st.rerun()
        return

    id_ot = limpiar(row.get("ID OT"), "SIN ID")
    render_top_bar(f"Detalle OT {id_ot}")
    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("Volver", use_container_width=True, type="secondary", key=gen_key("dettec_volver")):
            st.session_state.pagina = "mis_ordenes"; st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key=gen_key("dettec_inicio")):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()
    prioridad = limpiar(row.get("Prioridad_Actividad"), "")
    info_prioridad = obtener_color_prioridad(prioridad)
    if prioridad:
        st.markdown(f"""
        <div style="background: #f8f9fa; color: #374151; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #dc2626; margin-bottom: 16px; font-size: 13px;">
            <strong>Prioridad: {info_prioridad['label']}</strong> — {info_prioridad['desc']}
        </div>
        """, unsafe_allow_html=True)
    nodo_info = f"<strong>Nodo:</strong> {limpiar(row.get('Nodo'), 'N/A')}<br>" if 'Nodo' in row else ""
    st.markdown(f"""
    <div class="detail-panel" style="background: white; border: 1px solid #e5e7eb;">
        <div class="equipo-info">
            {nodo_info}
            <strong>Equipo:</strong> {limpiar(row.get('Equipo'), 'N/A')}<br>
            <strong>Ubicacion:</strong> {limpiar(row.get('Ubicacion'), 'N/A')}<br>
            <strong>Especialidad:</strong> {limpiar(row.get('Especialidad'), 'N/A')}<br>
            <strong>Estado:</strong> {limpiar(row.get('Estado'), 'Pendiente')}<br>
            <strong>Tecnico Asignado:</strong> {limpiar(row.get('Tecnico_Asignado'), 'Sin asignar')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.subheader("Descripcion del Procedimiento")
    st.write(limpiar(row.get("Descripcion de procedimiento"), "Sin descripcion"))

    if row.get("Comentarios"):
        st.subheader("Comentarios")
        st.info(limpiar(row.get("Comentarios"), ""))
    if row.get("Fecha_Ejecucion"):
        st.success(f"Ejecutado el: {limpiar(row.get('Fecha_Ejecucion'), 'N/A')} | Inicio: {limpiar(row.get('Hora_Inicio'), 'N/A')} | Fin: {limpiar(row.get('Hora_Fin'), 'N/A')}")

    if limpiar(row.get("Estado"), "Pendiente") == "Pendiente":
        if st.button("EJECUTAR ESTA ORDEN", use_container_width=True, type="primary", key=gen_key("dettec_ejecutar")):
            st.session_state.pagina = "ejecutar"
            st.rerun()

def pantalla_detalle():
    df = recargar_datos()
    internal_id = st.session_state.orden_seleccionada
    idx, row = get_row_by_internal_id(df, internal_id)
    if idx is None:
        st.error("Orden no encontrada.")
        if st.button("Volver", use_container_width=True, key=gen_key("det_volver_err")):
            st.session_state.pagina = "ordenes"; st.session_state.orden_seleccionada = None; st.rerun()
        return

    id_ot = limpiar(row.get("ID OT"), "SIN ID")
    perfil = st.session_state.perfil
    render_top_bar(f"Detalle OT {id_ot}")
    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("Volver", use_container_width=True, type="secondary", key=gen_key("det_volver")):
            st.session_state.pagina = "ordenes"; st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key=gen_key("det_inicio")):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()
    prioridad = limpiar(row.get("Prioridad_Actividad"), "")
    info_prioridad = obtener_color_prioridad(prioridad)
    if prioridad:
        st.markdown(f"""
        <div style="background: #f8f9fa; color: #374151; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #dc2626; margin-bottom: 16px; font-size: 13px;">
            <strong>Prioridad: {info_prioridad['label']}</strong> — {info_prioridad['desc']}
        </div>
        """, unsafe_allow_html=True)
    nodo_info = f"<strong>Nodo:</strong> {limpiar(row.get('Nodo'), 'N/A')}<br>" if 'Nodo' in row else ""
    st.markdown(f"""
    <div class="detail-panel" style="background: white; border: 1px solid #e5e7eb;">
        <div class="equipo-info">
            {nodo_info}
            <strong>Equipo:</strong> {limpiar(row.get('Equipo'), 'N/A')}<br>
            <strong>Ubicacion:</strong> {limpiar(row.get('Ubicacion'), 'N/A')}<br>
            <strong>Especialidad:</strong> {limpiar(row.get('Especialidad'), 'N/A')}<br>
            <strong>Estado:</strong> {limpiar(row.get('Estado'), 'Pendiente')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.subheader("Descripcion del Procedimiento")
    st.write(limpiar(row.get("Descripcion de procedimiento"), "Sin descripcion"))
    st.divider()
    st.subheader("📋 Informacion de la Orden")

    estado_actual = limpiar(row.get("Estado"), "Pendiente")
    tecnico_actual = limpiar(row.get("Tecnico_Asignado"), "Sin asignar")
    fecha_ejec = limpiar(row.get("Fecha_Ejecucion"), "—")
    h_ini = limpiar(row.get("Hora_Inicio"), "—")
    h_fin = limpiar(row.get("Hora_Fin"), "—")
    duracion = calcular_duracion(h_ini, h_fin) if h_ini != "—" and h_fin != "—" else None

    pri_color = {"Rojo": "#ef4444", "Amarillo": "#f59e0b", "Verde": "#22c55e", "": "#64748b"}.get(prioridad, "#64748b")
    pri_label = obtener_color_prioridad(prioridad)["label"] if prioridad else "SIN CLASIFICAR"
    est_color = {"Pendiente": "#f59e0b", "Ejecutado": "#22c55e", "Verificado": "#3b82f6"}.get(estado_actual, "#64748b")

    duracion_html = ""
    if duracion:
        duracion_html = f"""<div style="background: #d1fae5; color: #065f46; text-align: center; padding: 8px; border-radius: 8px; margin-top: 12px; font-size: 14px; font-weight: 700; border: 1px solid #059669;">✅ Duracion: {duracion}</div>"""

    st.markdown(f"""
    <div style="background: #f9fafb; border-radius: 12px; padding: 16px; border: 1px solid #e5e7eb; margin-bottom: 12px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div style="background: white; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #3b82f6;">
                <div style="color:#6b7280; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">👤 Tecnico</div>
                <div style="color:#111827; font-size:13px; font-weight:600; margin-top:4px;">{tecnico_actual}</div>
            </div>
            <div style="background: white; padding: 10px 12px; border-radius: 8px; border-left: 3px solid {est_color};">
                <div style="color:#6b7280; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">🔴 Estado</div>
                <div style="color:{est_color}; font-size:13px; font-weight:700; margin-top:4px;">{estado_actual}</div>
            </div>
            <div style="background: white; padding: 10px 12px; border-radius: 8px; border-left: 3px solid {pri_color};">
                <div style="color:#6b7280; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">⚠️ Prioridad</div>
                <div style="color:{pri_color}; font-size:13px; font-weight:700; margin-top:4px;">{pri_label}</div>
            </div>
            <div style="background: white; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #a78bfa;">
                <div style="color:#6b7280; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">📅 Fecha Ejecucion</div>
                <div style="color:#111827; font-size:13px; font-weight:600; margin-top:4px;">{fecha_ejec}</div>
            </div>
            <div style="background: white; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #60a5fa;">
                <div style="color:#6b7280; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">⏰ Hora Inicio</div>
                <div style="color:#111827; font-size:13px; font-weight:600; margin-top:4px;">{h_ini}</div>
            </div>
            <div style="background: white; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #f472b6;">
                <div style="color:#6b7280; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">⏱ Hora Fin</div>
                <div style="color:#111827; font-size:13px; font-weight:600; margin-top:4px;">{h_fin}</div>
            </div>
        </div>
        {duracion_html}
    </div>
    """, unsafe_allow_html=True)

    if st.button("✏️ EDITAR EN ASIGNACIONES", use_container_width=True, type="secondary", key=gen_key("det_ir_asignar")):
        st.session_state.pagina = "asignacion"
        st.rerun()
    if perfil in ["admin", "supervisor"] and estado_actual == "Ejecutado":
        if st.button("VERIFICAR ORDEN", use_container_width=True, type="primary", key=gen_key("det_verificar")):
            if actualizar_orden_supabase(internal_id, "Estado", "Verificado"):
                df.at[idx, "Estado"] = "Verificado"
                st.success("Orden VERIFICADA")
                st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                st.rerun()
            else:
                st.error("Error al verificar")


def pantalla_asignacion():
    df = recargar_datos()
    render_top_bar("Asignación de Técnicos")
    boton_volver_inicio("asignacion")

    if "ubicacion_asig_seleccionada" not in st.session_state:
        st.session_state.ubicacion_asig_seleccionada = None

    # ========== VISTA DETALLE DE UNA UBICACIÓN ==========
    if st.session_state.ubicacion_asig_seleccionada is not None:
        ubic_sel = st.session_state.ubicacion_asig_seleccionada
        df_ubi = df[df["Ubicacion"] == ubic_sel].copy() if "Ubicacion" in df.columns else pd.DataFrame()

        if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_ubi.columns:
            df_ubi = df_ubi[df_ubi["Especialidad"] == st.session_state.filtro_especialidad]

        total_ubi = len(df_ubi)
        sin_asig = len(df_ubi[df_ubi["Tecnico_Asignado"].fillna("") == ""]) if "Tecnico_Asignado" in df_ubi.columns else 0
        asig_ubi = total_ubi - sin_asig
        pendientes = len(df_ubi[df_ubi["Estado"] == "Pendiente"]) if "Estado" in df_ubi.columns else 0
        pct_asig = round((asig_ubi / total_ubi) * 100, 1) if total_ubi > 0 else 0

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1f2937 0%, #374151 100%); border-radius: 16px; padding: 20px 24px; margin-bottom: 20px; color: white;">
            <div style="font-size: 20px; font-weight: 800; margin-bottom: 4px;">📍 {ubic_sel}</div>
            <div style="font-size: 13px; color: #d1d5db;">
                {total_ubi} actividades • {asig_ubi} asignadas ({pct_asig}%) • {sin_asig} sin asignar • {pendientes} pendientes
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_back, _ = st.columns([1, 3])
        with col_back:
            if st.button("← VOLVER A UBICACIONES", use_container_width=True, type="secondary", key=gen_key("btn_volver_ubic2")):
                st.session_state.ubicacion_asig_seleccionada = None
                st.rerun()

        if df_ubi.empty:
            st.info("No hay actividades en esta ubicación con los filtros actuales.")
            return

        st.markdown("""
        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; margin: 12px 0;">
            <div style="font-size: 11px; color: #6b7280; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                ⚡ Asignar técnico a todas las actividades de esta ubicación
            </div>
        """, unsafe_allow_html=True)
        col_m1, col_m2, col_m3 = st.columns([2, 1.2, 1.2])
        with col_m1:
            tecnicos_todos = obtener_tecnicos_con_carga(df, "Todas")
            opciones_tec = ["Seleccionar técnico..."] + [t["nombre"] for t in tecnicos_todos]
            tec_masivo = st.selectbox("Técnico", opciones_tec, index=0, key=gen_key("tec_masivo_ubi2"), label_visibility="collapsed")
        with col_m2:
            pri_masivo = st.selectbox("Prioridad", ["Mantener actual", "Rojo", "Amarillo", "Verde"], key=gen_key("pri_masivo_ubi2"), label_visibility="collapsed")
        with col_m3:
            st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
            if st.button("APLICAR A TODAS", use_container_width=True, type="primary", key=gen_key("btn_aplicar_ubi2")):
                aplicados = 0
                for idx, row in df_ubi.iterrows():
                    internal_id = limpiar(row.get("ID"), "")
                    datos = {}
                    if tec_masivo != "Seleccionar técnico...":
                        datos["Tecnico_Asignado"] = tec_masivo
                    if pri_masivo != "Mantener actual":
                        datos["Prioridad_Actividad"] = pri_masivo
                    if datos:
                        if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
                            aplicados += 1
                if aplicados > 0:
                    st.success(f"✅ {aplicados} actividades actualizadas.")
                    st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div style="display: grid; grid-template-columns: 70px 50px 1fr 90px 100px 180px; gap: 8px; padding: 10px 14px; background: #f3f4f6; border-radius: 8px 8px 0 0; border-bottom: 2px solid #e5e7eb; font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; align-items: center;">
            <div>ID OT</div>
            <div style="text-align:center">ESP</div>
            <div>DESCRIPCIÓN</div>
            <div style="text-align:center">ESTADO</div>
            <div style="text-align:center">PRIORIDAD</div>
            <div>TÉCNICO</div>
        </div>
        """, unsafe_allow_html=True)

        cambios_ubi = []
        for idx, row in df_ubi.iterrows():
            internal_id = limpiar(row.get("ID"), "")
            id_ot = limpiar(row.get("ID OT"), "SIN ID")
            tipo = limpiar(row.get("Especialidad"), "SIN")
            desc = limpiar(row.get("Descripcion de procedimiento"), "Sin descripción")
            estado = limpiar(row.get("Estado"), "Pendiente")
            tecnico_actual = limpiar(row.get("Tecnico_Asignado"), "")
            prioridad_actual = limpiar(row.get("Prioridad_Actividad"), "")

            clase_esp = "eq-esp-ele" if tipo == "ELE" else "eq-esp-mec" if tipo == "MEC" else "eq-esp-hid" if tipo == "HID" else ""
            estado_clase = obtener_estado_visual(estado)
            clase_pri = obtener_clase_css_prioridad(prioridad_actual)
            pri_info = obtener_color_prioridad(prioridad_actual)
            pri_label = pri_info["label"] if prioridad_actual else "—"

            tec_key = gen_key("tec_act2", internal_id)
            pri_key = gen_key("pri_act2", internal_id)

            if tec_key not in st.session_state:
                st.session_state[tec_key] = tecnico_actual if tecnico_actual else "Sin asignar"
            if pri_key not in st.session_state:
                st.session_state[pri_key] = prioridad_actual if prioridad_actual else ""

            tec_sel = st.session_state.get(tec_key, "Sin asignar")
            pri_sel = st.session_state.get(pri_key, "")
            tec_valor = "" if tec_sel == "Sin asignar" else tec_sel
            hay_cambio = (tec_valor != tecnico_actual) or (pri_sel != prioridad_actual)
            if hay_cambio:
                cambios_ubi.append({
                    "internal_id": internal_id,
                    "tec_nuevo": tec_valor,
                    "pri_nueva": pri_sel,
                    "tec_actual": tecnico_actual,
                    "pri_actual": prioridad_actual,
                    "row": row
                })

            bg = "#fefce8" if hay_cambio else "#ffffff"
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: 70px 50px 1fr 90px 100px 180px; gap: 8px; padding: 10px 14px; background: {bg}; border-bottom: 1px solid #f3f4f6; align-items: center; font-size: 12px;">
                <div style="font-family: monospace; font-weight: 700; color: #374151; font-size: 11px;">{id_ot}</div>
                <div style="text-align:center"><span class="{clase_esp}">{tipo}</span></div>
                <div style="font-weight: 500; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{desc}">{desc}</div>
                <div style="text-align:center"><span class="badge {estado_clase}">{estado}</span></div>
                <div style="text-align:center"><span class="badge {clase_pri}">{pri_label}</span></div>
                <div id="tec_slot_{internal_id}"></div>
            </div>
            """, unsafe_allow_html=True)

            cols = st.columns([3.5, 1.5])
            with cols[1]:
                tecnicos_info = obtener_tecnicos_con_carga(df, tipo if tipo in ["ELE", "MEC", "HID"] else "Todas")
                opciones_tec = ["Sin asignar"] + [t["nombre"] for t in tecnicos_info]
                idx_tec = opciones_tec.index(st.session_state.get(tec_key, "Sin asignar")) if st.session_state.get(tec_key, "Sin asignar") in opciones_tec else 0
                st.selectbox("", opciones_tec, index=idx_tec, key=tec_key, label_visibility="collapsed")

        st.markdown("<div style='height: 4px; background: #f3f4f6; border-radius: 0 0 8px 8px; margin-bottom: 16px;'></div>", unsafe_allow_html=True)

        if cambios_ubi:
            col_c1, col_c2 = st.columns([1, 2])
            with col_c1:
                st.markdown(f"""
                <div style="background: #fefce8; border: 1px solid #facc15; border-radius: 8px; padding: 10px 14px; text-align: center;">
                    <div style="font-size: 20px; font-weight: 800; color: #a16207;">{len(cambios_ubi)}</div>
                    <div style="font-size: 10px; color: #6b7280; font-weight: 600;">Cambios pendientes</div>
                </div>
                """, unsafe_allow_html=True)
            with col_c2:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑️ DESCARTAR", use_container_width=True, type="secondary", key=gen_key("btn_descartar_ubi2")):
                        for c in cambios_ubi:
                            iid = c["internal_id"]
                            st.session_state[gen_key("tec_act2", iid)] = c["tec_actual"] if c["tec_actual"] else "Sin asignar"
                            st.session_state[gen_key("pri_act2", iid)] = c["pri_actual"]
                        st.rerun()
                with c2:
                    if st.button(f"💾 GUARDAR {len(cambios_ubi)} CAMBIOS", use_container_width=True, type="primary", key=gen_key("btn_guardar_ubi2")):
                        exitosos = 0
                        with st.spinner("Guardando..."):
                            for c in cambios_ubi:
                                datos = {}
                                if c["tec_nuevo"] != c["tec_actual"]:
                                    datos["Tecnico_Asignado"] = c["tec_nuevo"]
                                if c["pri_nueva"] != c["pri_actual"]:
                                    datos["Prioridad_Actividad"] = c["pri_nueva"]
                                if datos:
                                    if actualizar_campos_supabase(c["internal_id"], datos, c["row"].to_dict()):
                                        exitosos += 1
                        if exitosos > 0:
                            st.success(f"✅ {exitosos} cambios guardados.")
                            st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                            st.rerun()
        return

    # ========== VISTA PRINCIPAL: DASHBOARD DE ASIGNACIÓN + UBICACIONES ==========
    df_asig = df.copy()
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_asig.columns:
        df_asig = df_asig[df_asig["Especialidad"] == st.session_state.filtro_especialidad]
    if "Nodo" in df_asig.columns and st.session_state.filtro_maquina_nodo != "Todas":
        df_asig = df_asig[df_asig["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
    if "Nodo" in df_asig.columns and st.session_state.filtro_subsistema_nodo != "Todos":
        df_asig = df_asig[df_asig["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]

    col_f1, col_f2 = st.columns([1, 3])
    with col_f1:
        estados_filtro = ["Todos", "Pendiente", "Ejecutado", "Verificado"]
        idx_est = estados_filtro.index(st.session_state.filtro_estado_asig) if st.session_state.filtro_estado_asig in estados_filtro else 0
        estado_sel = st.selectbox("Estado", estados_filtro, index=idx_est, key=gen_key("sel_estado_asig5"))
        st.session_state.filtro_estado_asig = estado_sel
    with col_f2:
        busq_asig = st.text_input("Buscar ubicación o equipo...", placeholder="Escribe para filtrar...", key=gen_key("txt_busq_asig5"))

    if estado_sel != "Todos" and "Estado" in df_asig.columns:
        df_asig = df_asig[df_asig["Estado"] == estado_sel]
    if busq_asig:
        busq_lower = busq_asig.lower()
        mask = pd.Series([False] * len(df_asig), index=df_asig.index)
        if "Ubicacion" in df_asig.columns: mask |= df_asig["Ubicacion"].astype(str).str.lower().str.contains(busq_lower, na=False)
        if "Equipo" in df_asig.columns: mask |= df_asig["Equipo"].astype(str).str.lower().str.contains(busq_lower, na=False)
        if "Descripcion de procedimiento" in df_asig.columns: mask |= df_asig["Descripcion de procedimiento"].astype(str).str.lower().str.contains(busq_lower, na=False)
        df_asig = df_asig[mask]

    # ===== KPIs DE ASIGNACIÓN =====
    total_asig = len(df_asig)
    con_tecnico = len(df_asig[df_asig["Tecnico_Asignado"].fillna("") != ""]) if "Tecnico_Asignado" in df_asig.columns else 0
    sin_tecnico = total_asig - con_tecnico
    pct_asignado = round((con_tecnico / total_asig) * 100, 1) if total_asig > 0 else 0
    pct_sin = round((sin_tecnico / total_asig) * 100, 1) if total_asig > 0 else 0
    ele_asig = len(df_asig[df_asig["Especialidad"] == "ELE"]) if "Especialidad" in df_asig.columns else 0
    mec_asig = len(df_asig[df_asig["Especialidad"] == "MEC"]) if "Especialidad" in df_asig.columns else 0
    pend_asig = len(df_asig[df_asig["Estado"] == "Pendiente"]) if "Estado" in df_asig.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Órdenes</div>
            <div class="kpi-value">{total_asig}</div>
            <div class="kpi-delta" style="color:#6b7280">{ele_asig} ELE • {mec_asig} MEC</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Sin Asignar</div>
            <div class="kpi-value" style="color:#dc2626">{sin_tecnico}</div>
            <div class="kpi-delta" style="color:#dc2626">{pct_sin}% del total</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Asignadas</div>
            <div class="kpi-value" style="color:#22c55e">{con_tecnico}</div>
            <div class="kpi-delta" style="color:#22c55e">{pct_asignado}% del total</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Pendientes</div>
            <div class="kpi-value" style="color:#f59e0b">{pend_asig}</div>
            <div class="kpi-delta" style="color:#f59e0b">Por asignar técnico</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ===== GRÁFICAS DE ASIGNACIÓN =====
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Estado de Asignación</div>', unsafe_allow_html=True)
        if total_asig > 0:
            asig_data = pd.DataFrame({
                "Estado": ["Asignadas", "Sin Asignar"],
                "Cantidad": [con_tecnico, sin_tecnico]
            })
            fig = px.pie(asig_data, values="Cantidad", names="Estado", hole=0.55,
                         color="Estado", color_discrete_map={"Asignadas": "#22c55e", "Sin Asignar": "#dc2626"})
            fig.update_layout(showlegend=True, margin=dict(t=0,b=0,l=0,r=0), height=260,
                              paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(family="Inter", size=12))
            st.plotly_chart(fig, use_container_width=True, key="chart_asig_estado")
        else:
            st.info("Sin datos")
        st.markdown('</div>', unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Asignación por Especialidad</div>', unsafe_allow_html=True)
        if "Especialidad" in df_asig.columns and not df_asig.empty:
            esp_asig = df_asig.groupby("Especialidad").apply(
                lambda x: pd.Series({
                    "Asignadas": len(x[x["Tecnico_Asignado"].fillna("") != ""]),
                    "Sin Asignar": len(x[x["Tecnico_Asignado"].fillna("") == ""])
                })
            ).reset_index()
            esp_melt = esp_asig.melt(id_vars=["Especialidad"], var_name="Estado", value_name="Cantidad")
            fig2 = px.bar(esp_melt, x="Especialidad", y="Cantidad", color="Estado",
                          barmode="group",
                          color_discrete_map={"Asignadas": "#22c55e", "Sin Asignar": "#dc2626"},
                          text="Cantidad")
            fig2.update_layout(showlegend=True, margin=dict(t=0,b=0,l=0,r=0), height=260,
                               paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               font=dict(family="Inter", size=12),
                               xaxis=dict(showgrid=False),
                               yaxis=dict(showgrid=True, gridcolor='#f3f4f6'))
            st.plotly_chart(fig2, use_container_width=True, key="chart_asig_esp")
        else:
            st.info("Sin datos")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ===== GRID DE UBICACIONES =====
    if "Ubicacion" not in df_asig.columns or df_asig.empty:
        st.info("No hay órdenes con los filtros seleccionados.")
        return

    ubicaciones = df_asig["Ubicacion"].dropna().unique()
    if len(ubicaciones) == 0:
        st.info("No hay ubicaciones disponibles.")
        return

    st.markdown(f"""
    <div style="margin: 8px 0 16px 0;">
        <span style="font-size: 13px; color: #6b7280; font-weight: 600;">
            📍 <strong style="color: #111827;">{len(ubicaciones)}</strong> ubicación(es) • <strong style="color: #111827;">{total_asig}</strong> actividades
        </span>
    </div>
    """, unsafe_allow_html=True)

    cols_por_fila = 3
    for i in range(0, len(ubicaciones), cols_por_fila):
        cols = st.columns(cols_por_fila)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(ubicaciones):
                break
            ubi = ubicaciones[idx]
            df_ubi = df_asig[df_asig["Ubicacion"] == ubi]
            total = len(df_ubi)
            sin_asig = len(df_ubi[df_ubi["Tecnico_Asignado"].fillna("") == ""]) if "Tecnico_Asignado" in df_ubi.columns else 0
            asig = total - sin_asig
            pct = round((asig / total) * 100, 1) if total > 0 else 0
            ele = len(df_ubi[df_ubi["Especialidad"] == "ELE"]) if "Especialidad" in df_ubi.columns else 0
            mec = len(df_ubi[df_ubi["Especialidad"] == "MEC"]) if "Especialidad" in df_ubi.columns else 0
            pend = len(df_ubi[df_ubi["Estado"] == "Pendiente"]) if "Estado" in df_ubi.columns else 0

            with col:
                color_barra = "#dc2626" if sin_asig > 0 else "#22c55e"
                badge = f'<span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700;">{sin_asig} sin asignar</span>' if sin_asig > 0 else '<span style="background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700;">✓ Asignado</span>'

                st.markdown(f"""
                <div style="background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-bottom: 12px; cursor: pointer; transition: all 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
                    <div style="width: 100%; height: 4px; background: {color_barra}; border-radius: 2px; margin-bottom: 10px;"></div>
                    <div style="font-size: 14px; font-weight: 700; color: #111827; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{ubi}">{ubi}</div>
                    <div style="display: flex; gap: 6px; margin-bottom: 8px;">
                        {badge}
                        <span style="background: #f3f4f6; color: #374151; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 600;">{total} act.</span>
                    </div>
                    <div style="font-size: 11px; color: #6b7280; line-height: 1.5; margin-bottom: 8px;">
                        {f"🔌 {ele} ELE • " if ele > 0 else ""}{f"🔧 {mec} MEC • " if mec > 0 else ""}{f"⏳ {pend} pend." if pend > 0 else ""}
                    </div>
                    <div style="width: 100%; height: 6px; background: #f3f4f6; border-radius: 3px; overflow: hidden;">
                        <div style="width: {pct}%; height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); border-radius: 3px;"></div>
                    </div>
                    <div style="font-size: 10px; color: #6b7280; text-align: right; margin-top: 4px;">{pct}% asignado</div>
                </div>
                """, unsafe_allow_html=True)

                btn_key = gen_key("btn_ubi2", ubi.replace(" ", "_").replace("-", "_"))
                if st.button(f"VER ACTIVIDADES →", use_container_width=True, type="primary", key=btn_key):
                    st.session_state.ubicacion_asig_seleccionada = ubi
                    st.rerun()
def pantalla_verificar():
    df = recargar_datos()
    render_top_bar("Verificar Órdenes Ejecutadas")
    boton_volver_inicio("verificar")
    df_ejecutadas = df[df["Estado"] == "Ejecutado"] if not df.empty and "Estado" in df.columns else pd.DataFrame()
    st.subheader(f"Ordenes ejecutadas pendientes de verificacion ({len(df_ejecutadas)})")
    if df_ejecutadas.empty:
        st.info("No hay ordenes ejecutadas pendientes de verificacion.")
        return
    for idx, row in df_ejecutadas.iterrows():
        internal_id = limpiar(row.get("ID"), "")
        id_ot = limpiar(row.get("ID OT"), "SIN ID")
        tipo = limpiar(row.get("Especialidad"), "SIN ESP")
        equipo = limpiar(row.get("Equipo"), "Sin equipo")
        ubicacion = limpiar(row.get("Ubicacion"), "Sin ubicacion")
        tecnico = limpiar(row.get("Tecnico_Asignado"), "Sin asignar")
        descripcion = limpiar(row.get("Descripcion de procedimiento"), "Sin descripcion")
        desc_corta = descripcion[:40] + "..." if len(descripcion) > 40 else descripcion
        fecha_ejec = limpiar(row.get("Fecha_Ejecucion"), "N/A")
        hora_ini = limpiar(row.get("Hora_Inicio"), "N/A")
        hora_fin = limpiar(row.get("Hora_Fin"), "N/A")
        nodo = limpiar(row.get("Nodo"), "")
        nodo_badge = f"<span class='nodo-badge-mini'>{nodo}</span>" if nodo else ""
        st.markdown(f"""
        <div class="detail-panel" style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong>OT {id_ot}</strong> {nodo_badge}
                <span class="badge badge-ejecutado">Ejecutado</span>
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
            st.write(f"**Comentarios:** {limpiar(row.get('Comentarios'), 'Sin comentarios')}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Verificado", use_container_width=True, type="primary", key=gen_key("verif_btn", internal_id)):
                    if actualizar_orden_supabase(internal_id, "Estado", "Verificado"):
                        st.success(f"OT {id_ot} verificada correctamente")
                        st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                        st.rerun()
                    else:
                        st.error("Error al verificar")
            with col2:
                if st.button(f"RECHAZAR", use_container_width=True, type="secondary", key=gen_key("rech_btn", internal_id)):
                    if actualizar_orden_supabase(internal_id, "Estado", "Pendiente"):
                        st.warning(f"OT {id_ot} devuelta a Pendiente")
                        st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                        st.rerun()
                    else:
                        st.error("Error al rechazar")


# ==================== FLUJO PRINCIPAL ====================
if st.session_state.pagina != "login":
    render_sidebar()

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
