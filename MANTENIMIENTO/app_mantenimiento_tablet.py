
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
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] {
        gap: 0rem !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        padding-left: 0px !important;
        padding-right: 0px !important;
        margin-left: 0px !important;
        margin-right: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
        min-width: 22px !important;
        max-width: 26px !important;
        flex: none !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
        padding-left: 2px !important;
        margin-left: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stCheckbox"] {
        margin-top: 0px !important;
        margin-bottom: 0px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label {
        min-height: unset !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        padding-right: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div {
        margin-right: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] { margin-bottom: 1px !important; }
    .eq-bloque-contenido div[data-testid="stTextInput"] { margin-bottom: 0px !important; }
    .eq-bloque-contenido div[data-testid="stTextInput"] > div > div > input {
        padding: 2px 6px !important;
        height: 28px !important;
        font-size: 11px !important;
        min-height: 28px !important;
    }
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
    .chk-item {
        display: flex; align-items: center; gap: 10px;
        padding: 8px 12px; background: #FFFFFF;
        border-radius: 8px; margin-bottom: 4px;
        border: 1px solid #E2E8F0;
        transition: all 0.15s;
    }
    .chk-item:hover { border-color: #0EA5E9; background: #F0F9FF; }
    .chk-item.ejecutada { opacity: 0.65; background: #F0FDF4; border-color: #86EFAC; }
    .chk-item.ejecutada .chk-desc { text-decoration: line-through; color: #166534; }
    .chk-box { width: 18px; height: 18px; accent-color: #0EA5E9; flex-shrink: 0; cursor: pointer; }
    .chk-desc { font-size: 13px; color: #0F172A; flex: 1; line-height: 1.3; }
    .chk-com-btn {
        width: 28px; height: 28px; border-radius: 6px; background: #F1F5F9;
        border: 1px solid #CBD5E1; display: flex; align-items: center; justify-content: center;
        font-size: 13px; cursor: pointer; flex-shrink: 0; color: #64748B;
    }
    .chk-com-btn:hover { background: #E0F2FE; border-color: #0EA5E9; }
    .chk-com-btn.tiene { background: #DBEAFE; border-color: #3B82F6; color: #1D4ED8; }
    .chk-expand {
        padding: 8px 12px 8px 44px; background: #F8FAFC;
        border-radius: 0 0 8px 8px; margin-top: -2px; margin-bottom: 6px;
        border: 1px solid #E2E8F0; border-top: none;
    }
    .chk-expand-row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
    .chk-expand-label { font-size: 10px; color: #64748B; font-weight: 700; text-transform: uppercase; width: 60px; }
    .chk-expand-val { font-size: 12px; color: #0F172A; font-weight: 600; }
    .chk-expand-input {
        width: 100%; padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px;
        font-size: 12px; background: white; color: #0F172A;
    }
    .am-cantidad-box {
        background: #F0F9FF; border: 2px solid #0EA5E9; border-radius: 12px;
        padding: 14px; margin-bottom: 16px;
    }
    .am-fila {
        display: flex; gap: 8px; align-items: flex-end;
        background: white; padding: 8px 10px; border-radius: 8px;
        border: 1px solid #E2E8F0; margin-bottom: 6px;
    }
    .am-resumen {
        background: #FFF7ED; border: 1px solid #F97316; border-radius: 10px;
        padding: 10px 14px; margin: 10px 0; font-size: 13px;
    }
    /* === NUEVO: LISTA RÁPIDA DE ASIGNACIÓN === */
    .asig-rapida-header {
        display: none !important;
        grid-template-columns: 1fr 50px 1.5fr 80px 160px;
        gap: 8px;
        padding: 8px 12px;
        background: #F1F5F9;
        border-radius: 8px;
        font-weight: 700;
        font-size: 10px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        align-items: center;
        margin-bottom: 6px;
    }
    .asig-rapida-fila {
        display: grid;
        grid-template-columns: 1fr 50px 1.5fr 80px 160px;
        gap: 8px;
        padding: 8px 12px;
        background: #FFFFFF;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        align-items: center;
        font-size: 12px;
        margin-bottom: 4px;
        transition: all 0.15s;
    }
    .asig-rapida-fila:hover {
        border-color: #0EA5E9;
        box-shadow: 0 2px 6px rgba(14,165,233,0.08);
    }
    .asig-rapida-fila.asignada {
        border-left: 3px solid #10B981;
        background: #F0FDF4;
    }
    .batch-bar-rapida {
        background: linear-gradient(135deg, #F0F9FF, #E0F2FE);
        border: 1px solid #BAE6FD;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 14px;
    }
    @media (max-width: 768px) {
        .asig-rapida-header { display: none; }
        .asig-rapida-fila {
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            padding: 10px;
        }
        .asig-rapida-fila > div:nth-child(1) { grid-column: 1 / -1; }
        .asig-rapida-fila > div:nth-child(2) { grid-column: 1; }
        .asig-rapida-fila > div:nth-child(3) { grid-column: 2; text-align: right; }
        .asig-rapida-fila > div:nth-child(4) { grid-column: 1; }
        .asig-rapida-fila > div:nth-child(5) { grid-column: 2; }
    }

    /* === COMPACTAR FILAS DE ACTIVIDADES TÉCNICO === */
    .eq-bloque-contenido div[data-testid="stVerticalBlock"] > div {
        margin-bottom: 2px !important;
        padding-bottom: 2px !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] {
        gap: 0.3rem !important;
        margin-bottom: 2px !important;
        padding-bottom: 2px !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div {
        padding-left: 0px !important;
        padding-right: 0px !important;
        margin-left: 0px !important;
        margin-right: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div:first-child {
        min-width: 24px !important;
        max-width: 28px !important;
        flex: none !important;
    }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    .eq-bloque-contenido .stCheckbox {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    .eq-bloque-contenido .stCheckbox > label {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        min-height: unset !important;
    }
    .eq-bloque-contenido .stCheckbox > label > div {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stCheckbox"] {
        margin-top: 0px !important;
        margin-bottom: 0px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label {
        min-height: 20px !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div[data-testid="stWidgetLabel"] {
        display: none !important;
    }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div {
        margin-top: 0px !important;
        margin-bottom: 0px !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    .eq-bloque-contenido div[data-testid="element-container"] {
        margin-bottom: 0px !important;
    }
    .fila-compacta {
        display: flex;
        align-items: center;
        gap: 2px;
        padding: 6px 10px 6px 4px;
        margin-bottom: 4px;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
        background: #FFFFFF;
        transition: all 0.15s;
    }
    .fila-compacta:hover {
        border-color: #0EA5E9;
        background: #F0F9FF;
    }
    .fila-compacta.ejecutada {
        opacity: 0.65;
        background: #F0FDF4;
        border-color: #86EFAC;
    }
    .fila-compacta.ejecutada .fila-desc {
        text-decoration: line-through;
        color: #166534;
    }

    /* === EXPANDERS COMPACTOS Y ORDENADOS === */
    [data-testid="stExpander"] {
        margin-bottom: 4px !important;
    }
    [data-testid="stExpander"] > details {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        background: #FFFFFF;
        overflow: hidden;
    }
    [data-testid="stExpander"] > details > summary {
        padding: 8px 12px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        color: #0F172A !important;
        min-height: unset !important;
    }
    [data-testid="stExpander"] > details > summary:hover {
        background: #F8FAFC;
    }
    [data-testid="stExpander"] > details[open] > summary {
        background: #F0F9FF;
        border-bottom: 1px solid #E2E8F0;
    }
    [data-testid="stExpander"] .streamlit-expanderContent {
        padding: 10px 12px !important;
    }
    [data-testid="stExpander"] .streamlit-expanderContent p {
        margin-bottom: 4px !important;
        font-size: 12px !important;
    }
    [data-testid="stExpander"] .streamlit-expanderContent .stSelectbox {
        margin-top: 8px !important;
    }

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
    pct_pdte = round(100 - pct_ejec - (round((verificado/total)*100,1) if total>0 else 0), 1)
    pct_verif = round((verificado / total) * 100, 1)
    return pct_ejec, pct_pdte, pct_verif

def obtener_estado_visual(estado):
    estados = {"Ejecutado": "estado-ejecutado", "Verificado": "estado-verificado", "Pendiente": "estado-pendiente"}
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


def obtener_icono_actividad(desc):
    desc_lower = str(desc).lower()
    if any(p in desc_lower for p in ["limpieza", "limpia", "filtro"]):
        return "🧹"
    if any(p in desc_lower for p in ["conexiones", "cable", "bornera", "acometida", "sensor"]):
        return "⚡"
    if any(p in desc_lower for p in ["tornillo", "fijación", "motor", "mecanico", "mecánico"]):
        return "🔧"
    if any(p in desc_lower for p in ["verificar", "estado", "revisar", "revisión", "inspeccionar", "inspección"]):
        return "👁️"
    if any(p in desc_lower for p in ["reportar", "ruido", "anormal", "supervisor"]):
        return "📢"
    if any(p in desc_lower for p in ["sct", "corrección", "correctivo", "orden"]):
        return "📋"
    if any(p in desc_lower for p in ["válvula", "neumático", "neumatico", "presión"]):
        return "🚰"
    if any(p in desc_lower for p in ["ventilador", "ventaniola", "ventilación", "refrigeración"]):
        return "🌬️"
    if any(p in desc_lower for p in ["pintura", "pintar", "óxido", "oxido", "corrosión"]):
        return "🎨"
    if any(p in desc_lower for p in ["lubricar", "grasa", "aceite", "lubricación"]):
        return "🛢️"
    return "🔧"


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
if "mostrar_login_admin" not in st.session_state: st.session_state.mostrar_login_admin = False

# ===== Session state para asignacion rapida =====
if "asignaciones_temp" not in st.session_state:
    st.session_state.asignaciones_temp = {}
if "asig_rapida_msg" not in st.session_state:
    st.session_state.asig_rapida_msg = None

# ==================== LOGIN ADMIN (SECRETS) ====================
def autenticar_admin(password):
    admin_pass = st.secrets.get("ADMIN_PASSWORD", "")
    if not admin_pass:
        return False, "ADMIN_PASSWORD no configurado en Secrets"
    if password == admin_pass:
        return True, "OK"
    return False, "Contrasena incorrecta"

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
            <div class="perfil-desc">
                <div>Asigna tecnicos</div>
                <div>Verifica ejecuciones</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not st.session_state.mostrar_login_admin:
            if st.button("ENTRAR COMO ADMIN", use_container_width=True, type="primary", key=gen_key("login_admin")):
                st.session_state.mostrar_login_admin = True
                st.rerun()
        else:
            st.markdown("<div style='font-size:12px; color:#64748B; margin-bottom:4px;'>🔐 Contraseña de administrador</div>", unsafe_allow_html=True)
            pwd_admin = st.text_input("", type="password", placeholder="Escribe la contraseña...", key=gen_key("pwd_admin"), label_visibility="collapsed")
            col_ing, col_vol = st.columns(2)
            with col_ing:
                if st.button("INGRESAR", use_container_width=True, type="primary", key=gen_key("btn_ingresar_admin")):
                    ok, msg = autenticar_admin(pwd_admin)
                    if ok:
                        st.session_state.perfil = "admin"
                        st.session_state.admin_autenticado = True
                        st.session_state.pagina = "home"
                        st.session_state.mostrar_login_admin = False
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
            with col_vol:
                if st.button("Cancelar", use_container_width=True, type="secondary", key=gen_key("btn_cancelar_admin")):
                    st.session_state.mostrar_login_admin = False
                    st.rerun()

    with col2:
        st.markdown("""
        <div class="perfil-card perfil-tecnico" style="text-align: center; padding: 20px;">
            <div class="perfil-icon">&#128295;</div>
            <div class="perfil-titulo" style="color: #28a745;">TECNICO</div>
            <div class="perfil-desc">
                <div>Ve sus ordenes</div>
                <div>Ejecuta actividades</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("ENTRAR COMO TECNICO", use_container_width=True, type="primary", key=gen_key("login_tecnico")):
            st.session_state.perfil = "tecnico"
            st.session_state.pagina = "home"
            st.rerun()


def pantalla_home():
    perfil = st.session_state.perfil
    df = recargar_datos()
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>App Tablet Mtto</span>
        <span style="font-size: 12px; opacity: 0.8;">{'&#128100; Admin' if perfil == 'admin' else '&#128295; Tecnico'}</span>
    </div>
    """, unsafe_allow_html=True)

    if perfil == "admin" and not df.empty:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            total_ord = len(df)
            asignadas = len(df[(df["Tecnico_Asignado"].notna()) & (df["Tecnico_Asignado"] != "")]) if "Tecnico_Asignado" in df.columns else 0
            sin_asignar = total_ord - asignadas
            pct_asig = round((asignadas / total_ord) * 100, 1) if total_ord > 0 else 0
            arc_total = 251.33
            dash_green = round(arc_total * (pct_asig / 100), 2)
            dash_red = round(arc_total - dash_green, 2)
            st.markdown(f"""
            <div style="background:#FFFFFF; border-radius:16px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,.08); border:1px solid #E2E8F0;">
                <div style="font-size:13px; font-weight:700; color:#0F172A; margin-bottom:6px; text-align:center;">⏱️ Progreso de Asignación</div>
                <div style="display:flex; justify-content:center;">
                    <svg width="180" height="105" viewBox="0 0 220 125">
                        <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#E2E8F0" stroke-width="22" stroke-linecap="round"/>
                        <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#22c55e" stroke-width="22" stroke-linecap="round" 
                            stroke-dasharray="{dash_green} {dash_red}" stroke-dashoffset="0"/>
                        <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#ef4444" stroke-width="22" stroke-linecap="round" 
                            stroke-dasharray="{dash_red} {dash_green}" stroke-dashoffset="-{dash_green}"/>
                        <text x="110" y="100" text-anchor="middle" font-size="10" fill="#64748B" font-family="system-ui,sans-serif">Completado</text>
                        <text x="110" y="80" text-anchor="middle" font-size="28" font-weight="900" fill="#0F172A" font-family="system-ui,sans-serif">{pct_asig}%</text>
                    </svg>
                </div>
                <div style="display:flex; justify-content:center; gap:20px; margin-top:2px;">
                    <div style="text-align:center;">
                        <div style="font-size:16px; font-weight:800; color:#166534;">{asignadas}</div>
                        <div style="font-size:9px; color:#64748B; font-weight:600;">Asignadas</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:16px; font-weight:800; color:#991B1B;">{sin_asignar}</div>
                        <div style="font-size:9px; color:#64748B; font-weight:600;">Pendientes</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_g2:
            if "Estado" in df.columns:
                total_ejec = len(df[df["Estado"].isin(["Ejecutado", "Verificado"])])
                verif_count = len(df[df["Estado"] == "Verificado"])
                pend_verif = total_ejec - verif_count
                pct_verif = round((verif_count / total_ejec) * 100, 1) if total_ejec > 0 else 0
                arc_total2 = 251.33
                dash_green2 = round(arc_total2 * (pct_verif / 100), 2)
                dash_red2 = round(arc_total2 - dash_green2, 2)
                st.markdown(f"""
                <div style="background:#FFFFFF; border-radius:16px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,.08); border:1px solid #E2E8F0;">
                    <div style="font-size:13px; font-weight:700; color:#0F172A; margin-bottom:6px; text-align:center;">✅ Progreso de Verificación</div>
                    <div style="display:flex; justify-content:center;">
                        <svg width="180" height="105" viewBox="0 0 220 125">
                            <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#E2E8F0" stroke-width="22" stroke-linecap="round"/>
                            <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#22c55e" stroke-width="22" stroke-linecap="round" 
                                stroke-dasharray="{dash_green2} {dash_red2}" stroke-dashoffset="0"/>
                            <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#f59e0b" stroke-width="22" stroke-linecap="round" 
                                stroke-dasharray="{dash_red2} {dash_green2}" stroke-dashoffset="-{dash_green2}"/>
                            <text x="110" y="100" text-anchor="middle" font-size="10" fill="#64748B" font-family="system-ui,sans-serif">Verificadas</text>
                            <text x="110" y="80" text-anchor="middle" font-size="28" font-weight="900" fill="#0F172A" font-family="system-ui,sans-serif">{pct_verif}%</text>
                        </svg>
                    </div>
                    <div style="display:flex; justify-content:center; gap:20px; margin-top:2px;">
                        <div style="text-align:center;">
                            <div style="font-size:16px; font-weight:800; color:#166534;">{verif_count}</div>
                            <div style="font-size:9px; color:#64748B; font-weight:600;">Verificadas</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="font-size:16px; font-weight:800; color:#B45309;">{pend_verif}</div>
                            <div style="font-size:9px; color:#64748B; font-weight:600;">Ejecutadas</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    if perfil == "admin":
        st.markdown("<div style='text-align: center; margin: 15px 0 10px 0; font-weight: 600; color: #666;'>Filtrar por Especialidad</div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button("TODAS", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "Todas" else "secondary", key=gen_key("btn_filtro_todas")):
                st.session_state.filtro_especialidad = "Todas"; st.rerun()
        with col2:
            if st.button("ELE", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "ELE" else "secondary", key=gen_key("btn_filtro_ele")):
                st.session_state.filtro_especialidad = "ELE"
                st.session_state.pagina = "asignacion"
                st.rerun()
        with col3:
            if st.button("MEC", use_container_width=True, type="primary" if st.session_state.filtro_especialidad == "MEC" else "secondary", key=gen_key("btn_filtro_mec")):
                st.session_state.filtro_especialidad = "MEC"
                st.session_state.pagina = "asignacion"
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn3 = st.columns(2)
        with col_btn1:
            if st.button("VER ORDENES ▼", use_container_width=True, type="primary", key=gen_key("btn_ver_ordenes_toggle")):
                st.session_state.mostrar_opciones_ordenes = not st.session_state.get("mostrar_opciones_ordenes", False)
                st.rerun()
        with col_btn3:
            if st.button("ENVIAR REPORTE POR CORREO", use_container_width=True, type="primary", key=gen_key("btn_abrir_correo")):
                st.session_state.mostrar_envio_correo = True
                st.rerun()
        if st.session_state.get("mostrar_opciones_ordenes", False):
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            col_op1, col_op2 = st.columns(2)
            with col_op1:
                if st.button("PREVENTIVAS", use_container_width=True, type="secondary", key=gen_key("btn_ver_preventivas")):
                    st.session_state.mostrar_opciones_ordenes = False
                    st.session_state.pagina = "ordenes"; st.rerun()
            with col_op2:
                if st.button("EJECUTADAS", use_container_width=True, type="secondary", key=gen_key("btn_ver_ejecutadas")):
                    st.session_state.mostrar_opciones_ordenes = False
                    st.session_state.pagina = "verificar"; st.rerun()
    elif perfil == "tecnico":
        tecnicos_info = obtener_tecnicos_con_carga(df, "Todas")
        opciones_tec = ["Seleccionar tecnico..."] + [t["nombre"] for t in tecnicos_info]
        idx_tec = 0
        if st.session_state.tecnico_seleccionado != "Seleccionar tecnico...":
            for i, t in enumerate(tecnicos_info):
                if t["nombre"] == st.session_state.tecnico_seleccionado:
                    idx_tec = i + 1
                    break
        tecnico_sel = st.selectbox("Selecciona tu nombre:", opciones_tec, index=idx_tec, key=gen_key("sel_tecnico_home"))
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

            st.markdown(f"""
            <div style="text-align: center; margin: 15px 0 8px 0;">
                <div style="font-size: 14px; font-weight: 700; color: #1a237e;">{tecnico_actual}</div>
                <div style="font-size: 11px; color: #666;">Especialidad: {esp_sel}</div>
            </div>
            <div style="display: flex; gap: 8px; justify-content: center; margin: 10px 0; flex-wrap: wrap;">
                <div style="background: white; padding: 6px 12px; border-radius: 8px; text-align: center; border: 2px solid #1a237e; min-width: 70px;">
                    <div style="font-size: 18px; font-weight: 800; color: #1a237e;">{total_asignadas}</div>
                    <div style="font-size: 9px; color: #666;">Total</div>
                </div>
                <div style="background: white; padding: 6px 12px; border-radius: 8px; text-align: center; border: 2px solid #ffc107; min-width: 70px;">
                    <div style="font-size: 18px; font-weight: 800; color: #ffc107;">{pendientes}</div>
                    <div style="font-size: 9px; color: #666;">Pendientes</div>
                </div>
                <div style="background: white; padding: 6px 12px; border-radius: 8px; text-align: center; border: 2px solid #28a745; min-width: 70px;">
                    <div style="font-size: 18px; font-weight: 800; color: #28a745;">{ejecutadas}</div>
                    <div style="font-size: 9px; color: #666;">Ejecutadas</div>
                </div>
                <div style="background: white; padding: 6px 12px; border-radius: 8px; text-align: center; border: 2px solid #007bff; min-width: 70px;">
                    <div style="font-size: 18px; font-weight: 800; color: #007bff;">{verificadas}</div>
                    <div style="font-size: 9px; color: #666;">Verificadas</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.subheader(f"Mostrando {len(df_mias)} de {total_asignadas} ordenes")

            # --- SOLO MOSTRAR PENDIENTES ---
            df_pendientes = df_mias[df_mias["Estado"].isin(["Pendiente", "", None, "NaN"])]
            if df_pendientes.empty and not df_mias.empty:
                st.success("🎉 ¡Todas las actividades están completadas! No quedan tareas pendientes.")
                st.balloons()
            elif df_mias.empty:
                st.info("No tienes ordenes con los filtros seleccionados.")
            else:
                # === NUEVA ESTRUCTURA: Ubicación → Equipo → Actividades ===
                grupos_ubicacion = df_pendientes.groupby(["Ubicacion"])
                for ubicacion_raw, grupo_ubi_df in grupos_ubicacion:
                    ubicacion = ubicacion_raw[0] if isinstance(ubicacion_raw, tuple) else ubicacion_raw
                    grupo_ubi_df = grupo_ubi_df.copy()
                    if grupo_ubi_df.empty:
                        continue

                    ubi_key = str(ubicacion).replace(" ", "_").replace("-", "_").replace(".", "")

                    # Contenedor principal de la ubicación
                    st.markdown(f"""
                    <div style="background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); border-radius: 16px; margin-bottom: 12px; color: #0F172A; border: 1px solid #1E3A5F; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.25);">
                        <div style="background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%); padding: 12px 16px; text-align: center;">
                            <div style="font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;">📍 {ubicacion}</div>
                        </div>
                        <div style="padding: 10px 14px;">
                    """, unsafe_allow_html=True)

                    # Dentro de la ubicación, agrupar por Equipo
                    grupos_equipo = grupo_ubi_df.groupby(["Equipo"])
                    for equipo_raw, grupo_eq_df in grupos_equipo:
                        equipo = equipo_raw[0] if isinstance(equipo_raw, tuple) else equipo_raw
                        equipo_limpio = limpiar(equipo, "Sin equipo")
                        grupo_eq_df = grupo_eq_df.copy()
                        if grupo_eq_df.empty:
                            continue

                        total_act = len(grupo_eq_df)
                        tecnico_bloque = grupo_eq_df["Tecnico_Asignado"].mode()
                        tecnico_bloque = tecnico_bloque[0] if len(tecnico_bloque) > 0 else "Sin asignar"

                        # Calcular progreso visual (lee de session_state)
                        realizadas_chk = 0
                        for _, r in grupo_eq_df.iterrows():
                            iid = limpiar(r.get("ID"), "")
                            chk_k = gen_key("chk_eq", iid)
                            if st.session_state.get(chk_k, False):
                                realizadas_chk += 1
                        pct_realizadas = round((realizadas_chk / total_act) * 100, 1) if total_act > 0 else 0
                        estado_bloque = "Completado" if realizadas_chk == total_act and total_act > 0 else "Pendiente"
                        clase_est_bloque = "eq-estado-ej" if estado_bloque == "Completado" else "eq-estado-pd"

                        st.markdown(f"""
                        <div class="eq-bloque" style="margin-bottom: 10px; border-radius: 12px; overflow: hidden; border: 1px solid #1E3A5F;">
                            <div class="eq-bloque-header" style="padding: 10px 14px;">
                                <div style="flex:1; min-width:0;">
                                    <div class="eq-bloque-titulo">🔧 {equipo_limpio}</div>
                                    <div class="eq-bloque-meta">
                                        👤 {tecnico_bloque} | 📋 {total_act} actividades | ✅ {realizadas_chk} realizadas
                                    </div>
                                    <div class="eq-progress-bar">
                                        <div class="eq-progress-fill" style="width: {pct_realizadas}%;"></div>
                                    </div>
                                </div>
                                <span class="estado-badge {clase_est_bloque}" style="margin-left:12px; flex-shrink:0;">{estado_bloque}</span>
                            </div>
                            <div class="eq-bloque-contenido">
                        """, unsafe_allow_html=True)

                        # ========== RENDERIZAR CADA ACTIVIDAD DEL EQUIPO ==========
                        for idx, row in grupo_eq_df.iterrows():
                            internal_id = limpiar(row.get("ID"), "")
                            if not internal_id:
                                continue

                            desc = limpiar(row.get("Actividades"), "Sin descripcion")
                            estado = limpiar(row.get("Estado"), "Pendiente")
                            ya_ejecutado = estado == "Ejecutado"
                            chk_key = gen_key("chk_eq", internal_id)

                            # Inicializar en session_state si no existe (solo la primera vez)
                            if chk_key not in st.session_state:
                                st.session_state[chk_key] = ya_ejecutado

                            # El widget lee/escribe directamente de session_state
                            st.checkbox("", key=chk_key, label_visibility="collapsed")
                            chk_val = st.session_state[chk_key]

                            # Registrar hora de inicio automática al marcar
                            if chk_val and not ya_ejecutado and estado not in ["Ejecutado", "Verificado"]:
                                if f"hora_ini_auto_{internal_id}" not in st.session_state:
                                    st.session_state[f"hora_ini_auto_{internal_id}"] = datetime.now().strftime("%H:%M")

                            clase_ej = "ejecutada" if (chk_val or estado == "Ejecutado") else ""
                            st.markdown(f"""
                            <div class="fila-compacta {clase_ej}">
                                <span class="fila-desc" style="flex:1; font-size:13px; line-height:1.4;">{desc}</span>
                                <span class="estado-badge {'eq-estado-ej' if estado=='Ejecutado' else 'eq-estado-pd'}" style="flex-shrink:0; margin-left:2px;">{estado}</span>
                            </div>
                            """, unsafe_allow_html=True)

                        st.markdown("</div></div>", unsafe_allow_html=True)

                    # === COMENTARIO GENERAL Y BOTONES POR UBICACIÓN (solo uno) ===
                    comentario_ubi_key = f"com_ubi_{ubi_key}"
                    if comentario_ubi_key not in st.session_state:
                        st.session_state[comentario_ubi_key] = ""
                    st.text_input(
                        "💬 Comentario general del bloque:",
                        value=st.session_state[comentario_ubi_key],
                        key=comentario_ubi_key,
                        placeholder="Escribe un comentario para todas las actividades de este bloque..."
                    )
                    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

                    col_marcar, col_desmarcar, col_guardar = st.columns(3)
                    with col_marcar:
                        if st.button("✅ Marcar todas", use_container_width=True, type="primary", key=gen_key("btn_marcar_todas_ubi", ubi_key)):
                            ahora = datetime.now().strftime("%H:%M")
                            for _, row in grupo_ubi_df.iterrows():
                                internal_id = limpiar(row.get("ID"), "")
                                if internal_id:
                                    chk_k = gen_key("chk_eq", internal_id)
                                    st.session_state[chk_k] = True
                                    st.session_state[f"hora_ini_auto_{internal_id}"] = ahora
                            st.rerun()

                    with col_desmarcar:
                        if st.button("✕ Desmarcar todas", use_container_width=True, type="secondary", key=gen_key("btn_desmarcar_todas_ubi", ubi_key)):
                            for _, row in grupo_ubi_df.iterrows():
                                internal_id = limpiar(row.get("ID"), "")
                                if internal_id:
                                    chk_k = gen_key("chk_eq", internal_id)
                                    st.session_state[chk_k] = False
                                    if f"hora_ini_auto_{internal_id}" in st.session_state:
                                        del st.session_state[f"hora_ini_auto_{internal_id}"]
                            st.rerun()

                    with col_guardar:
                        if st.button("💾 Guardar", use_container_width=True, type="primary", key=gen_key("btn_guardar_ubi", ubi_key)):
                            guardados = 0
                            comentario_general = st.session_state.get(comentario_ubi_key, "")
                            for _, row in grupo_ubi_df.iterrows():
                                internal_id = limpiar(row.get("ID"), "")
                                if not internal_id:
                                    continue

                                chk_k = gen_key("chk_eq", internal_id)
                                chk_val = st.session_state.get(chk_k, False)
                                estado_actual = limpiar(row.get("Estado"), "Pendiente")
                                h_ini_bd = limpiar(row.get("Hora_Inicio"), "")
                                h_fin_bd = limpiar(row.get("Hora_Fin"), "")
                                hora_ini_auto = st.session_state.get(f"hora_ini_auto_{internal_id}", "")
                                comentario_bd = limpiar(row.get("Comentarios"), "")

                                if chk_val and estado_actual not in ["Ejecutado", "Verificado"]:
                                    hora_fin = datetime.now().strftime("%H:%M")
                                    hora_ini = hora_ini_auto if hora_ini_auto else (h_ini_bd if h_ini_bd else hora_fin)
                                    datos = {
                                        "Estado": "Ejecutado",
                                        "Hora_Inicio": hora_ini,
                                        "Hora_Fin": hora_fin,
                                        "Fecha_Ejecucion": datetime.now().strftime("%Y-%m-%d")
                                    }
                                    if comentario_general != comentario_bd:
                                        datos["Comentarios"] = comentario_general
                                    if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
                                        guardados += 1
                                        if f"hora_ini_auto_{internal_id}" in st.session_state:
                                            del st.session_state[f"hora_ini_auto_{internal_id}"]
                                        if chk_k in st.session_state:
                                            del st.session_state[chk_k]

                                elif not chk_val and estado_actual == "Ejecutado":
                                    datos = {"Estado": "Pendiente"}
                                    if comentario_general != comentario_bd:
                                        datos["Comentarios"] = comentario_general
                                    if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
                                        guardados += 1

                                else:
                                    if comentario_general != comentario_bd:
                                        if actualizar_orden_supabase(internal_id, "Comentarios", comentario_general):
                                            guardados += 1

                            if guardados > 0:
                                st.success(f"✅ {guardados} cambios guardados en Supabase")
                                st.rerun()
                            else:
                                st.info("No hay cambios para guardar")

                    st.markdown("</div></div>", unsafe_allow_html=True)
    if perfil == "admin" and st.session_state.mostrar_envio_correo:
        st.divider()
        st.subheader("Enviar Resumen por Correo")
        df_envio = df.copy()
        if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_envio.columns:
            df_envio = df_envio[df_envio["Especialidad"] == st.session_state.filtro_especialidad]
        if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_envio.columns:
            df_envio = df_envio[df_envio["Ubicacion"] == st.session_state.filtro_maquina]
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
            ], key=gen_key("radio_cuenta_correo"))
        with col_c2:
            area = st.text_input("Area / Proyecto", value="INY4 MEC", key=gen_key("txt_area_correo"))
        asunto = st.text_input("Asunto del correo", value=f"Ordenes preventivas {area}", key=gen_key("txt_asunto_correo"))
        destinatarios_text = st.text_area(
            "Destinatarios:",
            value="\n".join(DESTINATARIOS_DEFAULT),
            disabled=True,
            key=gen_key("txt_destinatarios")
        )
        col_env1, col_env2 = st.columns(2)
        with col_env1:
            if st.button("ENVIAR CORREO AHORA", use_container_width=True, type="primary", key=gen_key("btn_enviar_correo")):
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
            if st.button("CANCELAR", use_container_width=True, type="secondary", key=gen_key("btn_cancelar_correo")):
                st.session_state.mostrar_envio_correo = False
                st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    boton_cerrar_sesion()


def pantalla_ordenes():
    df = recargar_datos()
    perfil = st.session_state.perfil
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Ordenes Preventivas</span>
        <span style="font-size: 14px; opacity: 0.8;">{st.session_state.filtro_especialidad}</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("ordenes")
    busqueda = st.text_input("Buscar ID OT, equipo o descripcion...", value=st.session_state.busqueda, placeholder="Escribe para buscar...", key=gen_key("txt_busqueda_ordenes"))
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
        if "Actividades" in df_filtrado.columns: mask |= df_filtrado["Actividades"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        if "Nodo" in df_filtrado.columns: mask |= df_filtrado["Nodo"].astype(str).str.lower().str.contains(busqueda_lower, na=False)
        df_filtrado = df_filtrado[mask]
    st.markdown("""
    <div class="tabla-header">
        <div class="col-id">ID OT</div><div class="col-esp">ESP</div><div class="col-desc">DESCRIPCION</div>
        <div class="col-estado">ESTADO</div><div class="col-tec">TECNICO</div>
    </div>
    """, unsafe_allow_html=True)
    for idx, row in df_filtrado.iterrows():
        id_ot = limpiar(row.get("ID OT"), "SIN ID")
        internal_id = limpiar(row.get("ID"), "")
        tipo = limpiar(row.get("Especialidad"), "SIN ESP")
        descripcion = limpiar(row.get("Actividades"), "Sin descripcion")
        estado = limpiar(row.get("Estado"), "Pendiente")
        tecnico = limpiar(row.get("Tecnico_Asignado"), "Sin asignar")
        if tecnico == "Sin asignar" and estado in ["Ejecutado", "Verificado"]:
            estado = "Pendiente"
        estado_clase = obtener_estado_visual(estado)
        desc_corta = descripcion[:35] + "..." if len(descripcion) > 35 else descripcion
        prioridad = limpiar(row.get("Prioridad_Actividad"), "")
        clase_prioridad = obtener_clase_css_prioridad(prioridad)
        nodo = limpiar(row.get("Nodo"), "")
        nodo_html = f"<span class='nodo-badge-mini' style='margin-left:4px;'>{nodo}</span>" if nodo else ""
        comentario_admin = limpiar(row.get("Comentarios"), "")
        com_html = f"<div style='font-size:10px;color:#0EA5E9;margin-top:2px;font-style:italic;'>&#128172; {comentario_admin}</div>" if comentario_admin else ""
        st.markdown(f"""
        <div class="tabla-fila {clase_prioridad}">
            <div class="col-id"><strong>{id_ot}</strong>{nodo_html}</div>
            <div class="col-esp">{tipo}</div>
            <div class="col-desc" title="{descripcion}">{desc_corta}{com_html}</div>
            <div class="col-estado"><span class="estado-badge {estado_clase}">{estado}</span></div>
            <div class="col-tec">{tecnico}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Ver detalle", key=gen_key("btn_ver", internal_id), use_container_width=True):
            st.session_state.orden_seleccionada = internal_id
            st.session_state.pagina = "detalle"
            st.rerun()


def pantalla_mis_ordenes():
    df = recargar_datos()
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Mis Ordenes Asignadas</span>
    </div>
    """, unsafe_allow_html=True)
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
        descripcion = limpiar(row.get("Actividades"), "Sin descripcion")
        estado = limpiar(row.get("Estado"), "Pendiente")
        tecnico = limpiar(row.get("Tecnico_Asignado"), "Sin asignar")
        if tecnico == "Sin asignar" and estado in ["Ejecutado", "Verificado"]:
            estado = "Pendiente"
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
            <div class="col-estado"><span class="estado-badge {estado_clase}">{estado}</span></div>
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
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Ejecutar OT {id_ot}</span>
    </div>
    """, unsafe_allow_html=True)
    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("Volver", use_container_width=True, type="secondary", key=gen_key("ejec_volver")):
            st.session_state.pagina = "mis_ordenes"; st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key=gen_key("ejec_inicio")):
            st.session_state.pagina = "home"; st.session_state.orden_seleccionada = None; st.rerun()
    nodo_info = f"<strong>Nodo:</strong> {limpiar(row.get('Nodo'), 'N/A')}<br>" if 'Nodo' in row else ""
    st.markdown(f"""
    <div class="detail-panel" style="background: #FFFFFF; border: 1px solid #CBD5E1;">
        <div class="equipo-info" style="color: #0F172A;">
            {nodo_info}
            <strong style="color:#0F172A">Equipo:</strong> <span style="color:#0F172A;">{limpiar(row.get('Equipo'), 'N/A')}</span><br>
            <strong style="color:#0F172A">Ubicacion:</strong> <span style="color:#0F172A;">{limpiar(row.get('Ubicacion'), 'N/A')}</span><br>
            <strong style="color:#0F172A">Especialidad:</strong> <span style="color:#0F172A;">{limpiar(row.get('Especialidad'), 'N/A')}</span><br>
            <strong style="color:#0F172A">Estado actual:</strong> <span style="color:#0F172A;">{limpiar(row.get('Estado'), 'Pendiente')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<h3 style='color:#0F172A'>Descripcion del Procedimiento</h3>", unsafe_allow_html=True)
    st.markdown(f'<p style="color:#0F172A; font-size:14px; line-height:1.6;">{limpiar(row.get("Actividades"), "Sin descripcion")}</p>', unsafe_allow_html=True)
    st.markdown("<h3 style='color:#0F172A'>Registro de Ejecucion</h3>", unsafe_allow_html=True)
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
    st.markdown("<h3 style='color:#0F172A'>Comentarios de Ejecucion</h3>", unsafe_allow_html=True)
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
            <div style="background: #DCFCE7; color: #34d399; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; border: 1px solid #059669; margin: 12px 0;">
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
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Detalle OT {id_ot}</span>
    </div>
    """, unsafe_allow_html=True)
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
        <div style="background: #FFFFFF; color: #475569; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #0EA5E9; margin-bottom: 16px; font-size: 13px;">
            <strong>Prioridad: {info_prioridad['label']}</strong> — {info_prioridad['desc']}
        </div>
        """, unsafe_allow_html=True)
    nodo_info = f"<strong>Nodo:</strong> {limpiar(row.get('Nodo'), 'N/A')}<br>" if 'Nodo' in row else ""
    st.markdown(f"""
    <div class="detail-panel" style="background: #FFFFFF; border: 1px solid #CBD5E1;">
        <div class="equipo-info" style="color: #0F172A;">
            {nodo_info}
            <strong style="color:#0F172A">Equipo:</strong> <span style="color:#0F172A;">{limpiar(row.get('Equipo'), 'N/A')}</span><br>
            <strong style="color:#0F172A">Ubicacion:</strong> <span style="color:#0F172A;">{limpiar(row.get('Ubicacion'), 'N/A')}</span><br>
            <strong style="color:#0F172A">Especialidad:</strong> <span style="color:#0F172A;">{limpiar(row.get('Especialidad'), 'N/A')}</span><br>
            <strong style="color:#0F172A">Estado:</strong> <span style="color:#0F172A;">{limpiar(row.get('Estado'), 'Pendiente')}</span><br>
            <strong style="color:#0F172A">Tecnico Asignado:</strong> <span style="color:#0F172A;">{limpiar(row.get('Tecnico_Asignado'), 'Sin asignar')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<h3 style='color:#0F172A'>Descripcion del Procedimiento</h3>", unsafe_allow_html=True)
    st.markdown(f'<p style="color:#0F172A; font-size:14px; line-height:1.6;">{limpiar(row.get("Actividades"), "Sin descripcion")}</p>', unsafe_allow_html=True)
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
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Detalle OT {id_ot}</span>
    </div>
    """, unsafe_allow_html=True)
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
        <div style="background: #FFFFFF; color: #475569; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #0EA5E9; margin-bottom: 16px; font-size: 13px;">
            <strong>Prioridad: {info_prioridad['label']}</strong> — {info_prioridad['desc']}
        </div>
        """, unsafe_allow_html=True)
    nodo_info = f"<strong>Nodo:</strong> {limpiar(row.get('Nodo'), 'N/A')}<br>" if 'Nodo' in row else ""
    st.markdown(f"""
    <div class="detail-panel" style="background: #FFFFFF; border: 1px solid #CBD5E1;">
        <div class="equipo-info">
            {nodo_info}
            <strong style="color:#0F172A">Equipo:</strong> {limpiar(row.get('Equipo'), 'N/A')}<br>
            <strong style="color:#0F172A">Ubicacion:</strong> {limpiar(row.get('Ubicacion'), 'N/A')}<br>
            <strong style="color:#0F172A">Especialidad:</strong> {limpiar(row.get('Especialidad'), 'N/A')}<br>
            <strong style="color:#0F172A">Estado:</strong> {limpiar(row.get('Estado'), 'Pendiente')}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<h3 style='color:#0F172A'>Descripcion del Procedimiento</h3>", unsafe_allow_html=True)
    st.write(limpiar(row.get("Actividades"), "Sin descripcion"))
    st.divider()
    st.subheader("&#128203; Informacion de la Orden")
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
        duracion_html = f"""<div style="background: #DCFCE7; color: #34d399; text-align: center; padding: 8px; border-radius: 8px; margin-top: 12px; font-size: 14px; font-weight: 700; border: 1px solid #059669;">&#9989; Duracion: {duracion}</div>"""
    st.markdown(f"""
    <div style="background: #F8FAFC; border-radius: 12px; padding: 16px; border: 1px solid #E2E8F0; margin-bottom: 12px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div style="background: #F1F5F9; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #3b82f6;">
                <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">&#128100; Tecnico</div>
                <div style="color:#0F172A; font-size:13px; font-weight:600; margin-top:4px;">{tecnico_actual}</div>
            </div>
            <div style="background: #F1F5F9; padding: 10px 12px; border-radius: 8px; border-left: 3px solid {est_color};">
                <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">&#128308; Estado</div>
                <div style="color:{est_color}; font-size:13px; font-weight:700; margin-top:4px;">{estado_actual}</div>
            </div>
            <div style="background: #F1F5F9; padding: 10px 12px; border-radius: 8px; border-left: 3px solid {pri_color};">
                <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">&#9888; Prioridad</div>
                <div style="color:{pri_color}; font-size:13px; font-weight:700; margin-top:4px;">{pri_label}</div>
            </div>
            <div style="background: #F1F5F9; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #a78bfa;">
                <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">&#128197; Fecha Ejecucion</div>
                <div style="color:#0F172A; font-size:13px; font-weight:600; margin-top:4px;">{fecha_ejec}</div>
            </div>
            <div style="background: #F1F5F9; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #60a5fa;">
                <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">&#9200; Hora Inicio</div>
                <div style="color:#0F172A; font-size:13px; font-weight:600; margin-top:4px;">{h_ini}</div>
            </div>
            <div style="background: #F1F5F9; padding: 10px 12px; border-radius: 8px; border-left: 3px solid #f472b6;">
                <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">&#9201; Hora Fin</div>
                <div style="color:#0F172A; font-size:13px; font-weight:600; margin-top:4px;">{h_fin}</div>
            </div>
        </div>
        {duracion_html}
    </div>
    """, unsafe_allow_html=True)
    comentario_detalle = limpiar(row.get("Comentarios"), "")
    if comentario_detalle:
        st.markdown(f"""
        <div style="background: #FEF3C7; border-left: 4px solid #F59E0B; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 13px; color: #78350F;">
            <strong>💬 Comentario:</strong><br>{comentario_detalle}
        </div>
        """, unsafe_allow_html=True)
    if st.button("&#9998; EDITAR EN ASIGNACIONES", use_container_width=True, type="secondary", key=gen_key("det_ir_asignar")):
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


def pantalla_verificar():
    df = recargar_datos()
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Verificar Ordenes Ejecutadas</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("verificar")
    df_ejecutadas = df[(df["Estado"] == "Ejecutado") & (df["Tecnico_Asignado"].notna()) & (df["Tecnico_Asignado"] != "")] if not df.empty and "Estado" in df.columns and "Tecnico_Asignado" in df.columns else pd.DataFrame()
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
        descripcion = limpiar(row.get("Actividades"), "Sin descripcion")
        desc_corta = descripcion[:40] + "..." if len(descripcion) > 40 else descripcion
        fecha_ejec = limpiar(row.get("Fecha_Ejecucion"), "N/A")
        hora_ini = limpiar(row.get("Hora_Inicio"), "N/A")
        hora_fin = limpiar(row.get("Hora_Fin"), "N/A")
        nodo = limpiar(row.get("Nodo"), "")
        nodo_badge = f"<span class='nodo-badge-mini'>{nodo}</span>" if nodo else ""
        st.markdown(f"""
        <div class="detail-panel" style="margin-bottom: 12px; background:#FFFFFF; border:1px solid #E2E8F0;">
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




# ==================== CALLBACK AUTO-GUARDAR ====================
def auto_guardar_fila(internal_id, key_widget):
    """Se ejecuta automáticamente cuando cambia el técnico en una fila"""
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
    """Asigna o desasigna técnico a todas las actividades visibles de la máquina y guarda en Supabase"""
    if not desasignar and not tecnico_masivo:
        return

    df = st.session_state.df_mantenimientos
    # Reconstruir el df filtrado igual que en pantalla_asignacion
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


# ==================== NUEVA PANTALLA ASIGNACIÓN RÁPIDA ====================
def pantalla_asignacion():
    df = recargar_datos()
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>Asignacion de Tecnicos</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("asignacion")

    # Mostrar mensaje de asignación previa
    if st.session_state.get("asig_rapida_msg"):
        st.toast(st.session_state.asig_rapida_msg, icon="💾")
        st.session_state.asig_rapida_msg = None

    # ═══════════════════════════════════════════════════
    # PREPARAR DATAFRAME BASE (filtros globales)
    # ═══════════════════════════════════════════════════
    df_asig_base = df.copy()
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in df_asig_base.columns:
        df_asig_base = df_asig_base[df_asig_base["Especialidad"] == st.session_state.filtro_especialidad]
    if "Nodo" in df_asig_base.columns and st.session_state.filtro_maquina_nodo != "Todas":
        df_asig_base = df_asig_base[df_asig_base["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
    if "Nodo" in df_asig_base.columns and st.session_state.filtro_subsistema_nodo != "Todos":
        df_asig_base = df_asig_base[df_asig_base["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]

    # Filtro de estado eliminado — se muestran todos los estados

    # ═══════════════════════════════════════════════════
    # APLICAR FILTRO DE MÁQUINA (automático según botón clickeado)
    # ═══════════════════════════════════════════════════
    df_asig = df_asig_base.copy()
    if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_asig.columns:
        df_asig = df_asig[df_asig["Ubicacion"] == st.session_state.filtro_maquina]

    # Filtro de procedimiento eliminado — se muestran todos los procedimientos

    # ═══ LAYOUT: Filtros izquierda (1 parte) | Órdenes derecha (3 partes) ═══
    col_izq, col_der = st.columns([1, 3])

    # ═══════════════════════════════════════════════════
    # COLUMNA IZQUIERDA: Filtros apilados (automáticos)
    # ═══════════════════════════════════════════════════
    with col_izq:
        st.markdown("<div style='font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:8px;'>📍 Máquina</div>", unsafe_allow_html=True)
        maquinas_asig = obtener_maquinas_disponibles(df_asig_base)
        for maq in maquinas_asig:
            is_active = st.session_state.filtro_maquina == maq
            btn_type = "primary" if is_active else "secondary"
            if st.button(maq, key=gen_key("btn_maq", maq), type=btn_type, use_container_width=True):
                st.session_state.filtro_maquina = maq
                st.rerun()

        # Filtro de estado eliminado — se muestran todos los estados

        # Filtro de procedimiento eliminado — se muestran todos los procedimientos

    # ═══════════════════════════════════════════════════
    # COLUMNA DERECHA: Lista rápida + asignación masiva
    # ═══════════════════════════════════════════════════
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

        # ========== BARRA DE ASIGNACIÓN MASIVA ==========
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

        # Lista de actividades oculta (asignación masiva arriba)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if df_pagina.empty:
            st.info("📭 No hay actividades con los filtros seleccionados.")
        else:
            st.success(f"✅ {len(df_pagina)} actividades listas para asignar. Usa la barra de arriba.")

        # ========== LISTA DE ACTIVIDADES ==========
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

            st.markdown(f'''
            <div class="asig-rapida-fila {'asignada' if tec_asig else ''}">
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
            ''', unsafe_allow_html=True)

# ==================== PROTECCION DE RUTAS ADMIN ====================
# Si alguien intenta forzar una pagina de admin sin estar autenticado, lo sacamos
paginas_admin = ["home", "ordenes", "asignacion", "verificar", "detalle"]
if st.session_state.perfil == "admin" and not st.session_state.get("admin_autenticado", False):
    st.session_state.pagina = "login"
    st.session_state.perfil = None
    st.session_state.mostrar_login_admin = False
elif st.session_state.perfil != "admin" and st.session_state.pagina in ["asignacion", "verificar"]:
    # Si un tecnico de alguna forma llega a asignacion o verificar, lo saco
    st.session_state.pagina = "login"
    st.session_state.perfil = None

# ==================== EJECUCION PRINCIPAL ====================
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
