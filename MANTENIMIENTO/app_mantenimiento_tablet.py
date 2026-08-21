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
import hashlib
import html

# ==================== CONFIGURACIÓN ====================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://cpazmoebqbsrahviifvp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
if not SUPABASE_KEY:
    st.error("SUPABASE_KEY no configurada.")
    st.stop()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

DESTINATARIOS_DEFAULT = ["mantobogota@gmail.com", "supermantobogota@gmail.com"]

# Mapeo único entre nombres de la app y columnas de Supabase
MAPEO_COLUMNAS = {
    "ID": "id", "ID OT": "id_ot", "Actividades": "actividades", "Procedimiento": "procedimiento",
    "Tecnico_Asignado": "tecnico_asignado", "Tecnico_Asignado_2": "tecnico_asignado_2", "Prioridad_Actividad": "prioridad_actividad",
    "Actividades_Hechas": "actividades_hechas", "Fecha_Ejecucion": "fecha_ejecucion",
    "Hora_Inicio": "hora_inicio", "Hora_Fin": "hora_fin", "Estado": "estado",
    "Comentarios": "comentarios", "Equipo": "equipo", "Ubicacion": "ubicacion",
    "Especialidad": "especialidad", "Nodo": "nodo"
}

def mapear_campo_supabase(campo):
    return MAPEO_COLUMNAS.get(campo, campo.lower().replace(" ", "_").replace(".", "").replace("-", "_").replace("__", "_"))

def limpiar(valor, default=""):
    if valor is None:
        return default
    try:
        if pd.isna(valor):
            return default
    except Exception:
        pass
    s = str(valor).strip()
    return default if s.lower() in ("nan", "none", "nat", "null") else s

def _norm_valor(v):
    """Normaliza NaN / string vacío a None para comparar y enviar a Supabase."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    if isinstance(v, str) and v.strip() == "":
        return None
    return v

# ==================== CORREO ====================

def escapar(texto):
    """Escapa HTML para prevenir XSS en st.markdown con unsafe_allow_html."""
    return html.escape(str(texto)) if texto is not None else ""
def enviar_correo_preventivo(df, destinatarios, asunto, area_mecanica="INY4 MEC", email_remitente=None):
    suf = "_2" if email_remitente == "supermantobogota@gmail.com" else ""
    email_user = st.secrets.get(f"EMAIL_USER{suf}", "")
    email_pass = st.secrets.get(f"EMAIL_PASS{suf}", "")
    if not email_user or not email_pass:
        return False, "Credenciales no configuradas"

    total = len(df)
    pcts = {"Ejecutado": 0.0, "Pendiente": 0.0, "Verificado": 0.0}
    if total:
        for est in pcts:
            pcts[est] = round(len(df[df["Estado"] == est]) / total * 100, 1)

    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Preventivas")
    except Exception as e:
        return False, f"Error creando Excel: {e}"
    output.seek(0)

    cuerpo_html = f"""<html><body style="font-family: Arial, sans-serif; color: #333;">
        <p style="font-size: 16px; font-weight: bold;">Preventivo</p>
        <p style="font-size: 14px;">{area_mecanica}</p>
        <p style="font-size: 14px;">Ejecutadas {pcts['Ejecutado']}%</p>
        <p style="font-size: 14px;">Pendientes {pcts['Pendiente']}%</p>
        <p style="font-size: 14px;">Verificar {pcts['Verificado']}%</p>
        <br><p style="font-size: 14px;">Comentario:</p></body></html>"""

    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo_html, "html"))
    adj = MIMEBase("application", "octet-stream")
    adj.set_payload(output.read())
    encoders.encode_base64(adj)
    adj.add_header("Content-Disposition", f'attachment; filename="{area_mecanica}.xlsx"')
    msg.attach(adj)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.sendmail(email_user, destinatarios, msg.as_string())
        return True, f"Correo enviado desde {email_user}"
    except Exception as e:
        return False, f"Error al enviar: {e}"

# ==================== SUPABASE: CARGA Y ACTUALIZACIÓN ====================
@st.cache_data(ttl=30, show_spinner=False)
def _cargar_ordenes_cache():
    try:
        data = supabase.table("ordenes_trabajo").select("*").order("id", desc=False).execute().data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        inv = {v: k for k, v in MAPEO_COLUMNAS.items()}
        df = df.rename(columns={c: inv.get(c, c.capitalize()) for c in df.columns})
        for col, default in {"Estado": "Pendiente", "Comentarios": "", "Tecnico_Asignado": "",
                             "Tecnico_Asignado_2": "", "Actividades_Hechas": "", "Fecha_Ejecucion": "",
                             "Hora_Inicio": "", "Hora_Fin": "", "Prioridad_Actividad": "",
                             "ID OT": "", "Procedimiento": ""}.items():
            if col not in df.columns:
                df[col] = default
        return df
    except Exception as e:
        st.error(f"Error cargando ordenes: {e}")
        return pd.DataFrame()

def cargar_ordenes_supabase():
    return _cargar_ordenes_cache()
def actualizar_campos_supabase(id_interno, datos_nuevos, datos_originales=None):
    try:
        datos_a_enviar = {}
        for key, value in datos_nuevos.items():
            nuevo = _norm_valor(value)
            if datos_originales is not None:
                original = _norm_valor(datos_originales.get(key, datos_originales.get(mapear_campo_supabase(key), "")))
                if nuevo == original:
                    continue
            datos_a_enviar[mapear_campo_supabase(key)] = nuevo
        if datos_a_enviar:
            supabase.table("ordenes_trabajo").update(datos_a_enviar).eq("id", id_interno).execute()
        return True
    except Exception as e:
        st.error(f"Error actualizando orden: {e}")
        return False

def actualizar_orden_supabase(id_interno, campo, valor):
    try:
        if isinstance(valor, str) and valor.strip() == "":
            valor = None
        supabase.table("ordenes_trabajo").update({mapear_campo_supabase(campo): valor}).eq("id", id_interno).execute()
        return True
    except Exception as e:
        st.error(f"Error actualizando campo '{campo}': {e}")
        return False

# ==================== SINCRONIZACIÓN EXCEL ↔ SUPABASE ====================
def sincronizar_excel_a_supabase(df_excel, modo="reemplazar"):
    try:
        df = df_excel.copy()
        cols_originales = {c.strip().lower(): c for c in df.columns}
        mapeo_columnas = {
            "id_ot": ["id ot", "id_ot", "ot", "numero ot", "no. ot", "orden", "no ot", "id"],
            "equipo": ["equipo", "descripción", "descripcion", "id activo", "id_activo", "activo", "maquina", "máquina", "un"],
            "ubicacion": ["ubicacion", "ubicación", "lugar", "area", "área", "un", "unidad", "localizacion", "sala"],
            "especialidad": ["especialidad", "esp", "tipo de ot", "tipo_ot", "tipo", "area tecnica", "disciplina"],
            "actividades": ["actividades", "actividad", "descr", "descripcion", "descripción", "tarea", "trabajo", "falla", "problema"],
            "procedimiento": ["procedimiento", "proc", "proceso", "tipo procedimiento"],
            "nodo": ["nodo", "codigo", "código", "referencia", "id nodo", "tag"],
            "prioridad_actividad": ["prioridad", "prioridad_actividad", "prioridad actividad", "nivel", "color", "urgencia"],
            "tecnico_asignado": ["tecnico_asignado", "tecnico asignado", "tecnico", "tecnico 1", "tecnico1", "tecnico_asignado_1"],
            "tecnico_asignado_2": ["tecnico_asignado_2", "tecnico asignado 2", "tecnico 2", "tecnico2", "tecnico2_asignado"]
        }
        columnas_renombrar = {}
        for supabase_col, posibles in mapeo_columnas.items():
            for posible in posibles:
                if posible in cols_originales:
                    columnas_renombrar[cols_originales[posible]] = supabase_col
                    break
        df = df.rename(columns=columnas_renombrar)
        detectadas = list(columnas_renombrar.values())
        faltantes = [c for c in mapeo_columnas if c not in detectadas]
        st.markdown(f"""
        <div style="background: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px; padding: 10px; margin: 8px 0;">
            <div style="font-size: 12px; color: #166534;">
                ✅ <b>Columnas detectadas:</b> {', '.join(detectadas) if detectadas else 'Ninguna'}<br>
                {'⚠️ <b>Sin detectar:</b> ' + ', '.join(faltantes) if faltantes else '✅ Todas las columnas principales encontradas'}
            </div>
        </div>""", unsafe_allow_html=True)

        # Si falta equipo u ubicacion, usar la otra como respaldo
        if "equipo" not in df.columns and "ubicacion" in df.columns:
            df["equipo"] = df["ubicacion"]
            st.info("ℹ️ No se detectó columna 'equipo'. Se usará 'ubicacion' como equipo.")
        if "ubicacion" not in df.columns and "equipo" in df.columns:
            df["ubicacion"] = df["equipo"]
            st.info("ℹ️ No se detectó columna 'ubicacion'. Se usará 'equipo' como ubicacion.")

        cols_validas = [c for c in mapeo_columnas if c in df.columns]
        if not cols_validas:
            st.error(f"❌ No se detectaron columnas válidas. Columnas en tu Excel: {list(df_excel.columns)}")
            return False, "No se detectaron columnas válidas"
        df = df[cols_validas].where(pd.notnull(df), None)
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(lambda x: None if isinstance(x, str) and x.strip() == "" else x)

        def generar_id_unico(row):
            raw = "|".join(str(row.get(c, "")) for c in ["id_ot", "equipo", "ubicacion", "actividades", "nodo"])
            return hashlib.md5(raw.encode()).hexdigest()[:20]
        df["id_unico"] = df.apply(generar_id_unico, axis=1)

        # NO convertir id_ot a numérico para preservar ceros a la izquierda
        if "id_ot" in df.columns:
            df["id_ot"] = df["id_ot"].apply(
                lambda x: str(int(x)).zfill(len(str(x))) if pd.notna(x) and str(x).replace(".", "", 1).isdigit()
                else (str(x) if pd.notna(x) else None))

        registros = df.to_dict(orient="records")
        total = len(registros)
        if total == 0:
            return False, "❌ No hay registros válidos para sincronizar"

        if modo == "reemplazar":
            with st.spinner("🗑️ Borrando datos antiguos..."):
                supabase.table("ordenes_trabajo").delete().neq("id", 0).execute()
        elif modo != "upsert":
            return False, "Modo no válido"

        procesados, batch_size = 0, 500
        barra = st.progress(0)
        for i in range(0, total, batch_size):
            lote = registros[i:i + batch_size]
            if modo == "reemplazar":
                supabase.table("ordenes_trabajo").insert(lote).execute()
            else:
                supabase.table("ordenes_trabajo").upsert(lote, on_conflict="id_unico").execute()
            procesados += len(lote)
            barra.progress(min((i + batch_size) / total, 1.0))
        barra.empty()

        if modo == "reemplazar":
            return True, f"✅ Sincronización completa: {procesados} registros insertados con ID único."
        return True, f"✅ Sincronización completa: {procesados} registros actualizados/insertados. Las asignaciones de técnicos se mantuvieron."
    except Exception as e:
        return False, f"❌ Error: {e}"

# ==================== ESTILOS ====================
st.set_page_config(page_title="App Tablet Mtto Preventivo", page_icon="🔧", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu, header, footer, [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stToolbar"] { visibility: hidden !important; }
    .stDeployButton { display: none; }
    .stApp { background-color: #F1F5F9; max-width: 100vw; overflow-x: hidden; }
    .main .block-container { padding-left: 0.3rem !important; padding-right: 0.3rem !important; max-width: 100% !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
    div[data-testid="stVerticalBlock"] > div { margin-bottom: 0.2rem !important; }
    .stMarkdown { margin-bottom: 0 !important; }
    iframe, .stSelectbox, .stTextInput, .stButton { max-width: 100%; }
    .stSelectbox label, .stTextInput label { color: #475569 !important; }
    .stButton>button { border-radius: 6px; font-weight: 600; font-size: 12px !important; padding: 4px 12px !important; }

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

    .perfil-card { background: #FFFFFF; color: #0F172A; border-radius: 16px; padding: 24px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; border: 3px solid transparent; }
    .perfil-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
    .perfil-admin { border-color: #dc3545; }
    .perfil-tecnico { border-color: #28a745; }
    .perfil-supervisor { border-color: #007bff; }
    .perfil-icon { font-size: 48px; margin-bottom: 12px; }
    .perfil-titulo { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
    .perfil-desc { font-size: 12px; color: #666; }

    .tecnico-card, .maquina-card { background: white; border-radius: 12px; padding: 12px 16px; margin-bottom: 8px; border: 2px solid #e9ecef; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: space-between; }
    .tecnico-card:hover, .maquina-card:hover { border-color: #1a237e; box-shadow: 0 2px 8px rgba(26,35,158,0.15); }
    .tecnico-card.activa, .maquina-card.activa { border-color: #1a237e; background: linear-gradient(135deg, #e8eaf6 0%, #ffffff 100%); }
    .tecnico-nombre, .maquina-nombre { font-size: 14px; font-weight: 700; color: #1a237e; }
    .maquina-nombre { font-size: 15px; }
    .tecnico-esp { font-size: 11px; color: #666; }
    .tecnico-badge, .maquina-badge { background: #1a237e; color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; min-width: 28px; text-align: center; }
    .tecnico-badge.cero { background: #6c757d; }
    .tecnico-badge.alta { background: #dc3545; }
    .tecnico-badge.media { background: #ffc107; color: #333; }
    .tecnico-badge.baja { background: #28a745; }
    .grupo-ele { border-left: 4px solid #ffc107 !important; }
    .grupo-mec { border-left: 4px solid #28a745 !important; }

    .filtro-nodo-label { font-size: 12px; color: #666; margin-bottom: 4px; font-weight: 600; text-transform: uppercase; }
    .contador-maquinas { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin: 10px 0; }
    .contador-maquina { background: #FFFFFF; color: #0F172A; border-radius: 8px; padding: 8px 12px; text-align: center; border: 1px solid #e9ecef; min-width: 80px; }
    .contador-maquina-valor { font-size: 18px; font-weight: 800; color: #60a5fa; }
    .contador-maquina-label { font-size: 10px; color: #475569; }
    .nodo-badge-mini { background: #e8eaf6; color: #1a237e; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; font-family: monospace; }

    .eq-bloque { background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); border-radius: 16px; margin-bottom: 8px; color: #0F172A; border: 1px solid #1E3A5F; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.25); }
    .eq-bloque-header { background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%); padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
    .eq-bloque-titulo { font-size: 15px; font-weight: 800; color: #ffffff; letter-spacing: 0.3px; line-height: 1.3; }
    .eq-bloque-meta { font-size: 11px; color: #0F172A; margin-top: 4px; }
    .eq-progress-bar { width: 100%; height: 6px; background: #FFFFFF; border-radius: 3px; margin-top: 8px; overflow: hidden; }
    .eq-progress-fill { height: 100%; background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%); border-radius: 3px; transition: width 0.3s ease; }
    .eq-bloque-contenido { padding: 10px 14px; }

    /* === FILAS COMPACTAS DE ACTIVIDADES DENTRO DEL BLOQUE DE EQUIPO === */
    .eq-bloque-contenido div[data-testid="stVerticalBlock"] > div { margin-bottom: 2px !important; padding-bottom: 2px !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] { gap: 0.3rem !important; margin-bottom: 2px !important; padding-bottom: 2px !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div { padding: 0 !important; margin: 0 !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div:first-child { min-width: 24px !important; max-width: 28px !important; flex: none !important; }
    .eq-bloque-contenido div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) { padding-left: 2px !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"], .eq-bloque-contenido .stCheckbox { margin: 0 !important; padding: 0 !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label, .eq-bloque-contenido .stCheckbox > label { min-height: 20px !important; margin: 0 !important; padding: 0 !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div { margin: 0 !important; padding: 0 !important; }
    .eq-bloque-contenido div[data-testid="stCheckbox"] > label > div[data-testid="stWidgetLabel"] { display: none !important; }
    .eq-bloque-contenido div[data-testid="stTextInput"] { margin-bottom: 0 !important; }
    .eq-bloque-contenido div[data-testid="stTextInput"] > div > div > input { padding: 2px 6px !important; height: 28px !important; font-size: 11px !important; min-height: 28px !important; }
    .eq-bloque-contenido div[data-testid="element-container"] { margin-bottom: 0 !important; }

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

    /* === LISTA RÁPIDA DE ASIGNACIÓN === */
    .asig-rapida-header { display: none !important; }
    .asig-rapida-fila { display: grid; grid-template-columns: 1fr 50px 1.5fr 80px 160px; gap: 8px; padding: 8px 12px; background: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; align-items: center; font-size: 12px; margin-bottom: 4px; transition: all 0.15s; }
    .asig-rapida-fila:hover { border-color: #0EA5E9; box-shadow: 0 2px 6px rgba(14,165,233,0.08); }
    .asig-rapida-fila.asignada { border-left: 3px solid #10B981; background: #F0FDF4; }
    .batch-bar-rapida { background: linear-gradient(135deg, #F0F9FF, #E0F2FE); border: 1px solid #BAE6FD; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px; }

    .fila-compacta { display: flex; align-items: center; gap: 2px; padding: 6px 10px 6px 4px; margin-bottom: 4px; border-radius: 6px; border: 1px solid #E2E8F0; background: #FFFFFF; transition: all 0.15s; }
    .fila-compacta:hover { border-color: #0EA5E9; background: #F0F9FF; }
    .fila-compacta.ejecutada { opacity: 0.65; background: #F0FDF4; border-color: #86EFAC; }
    .fila-compacta.ejecutada .fila-desc { text-decoration: line-through; color: #166534; }

    /* === EXPANDERS COMPACTOS === */
    [data-testid="stExpander"] { margin-bottom: 4px !important; }
    [data-testid="stExpander"] > details { border: 1px solid #E2E8F0; border-radius: 8px; background: #FFFFFF; overflow: hidden; }
    [data-testid="stExpander"] > details > summary { padding: 8px 12px !important; font-size: 12px !important; font-weight: 600 !important; color: #0F172A !important; min-height: unset !important; }
    [data-testid="stExpander"] > details > summary:hover { background: #F8FAFC; }
    [data-testid="stExpander"] > details[open] > summary { background: #F0F9FF; border-bottom: 1px solid #E2E8F0; }
    [data-testid="stExpander"] .streamlit-expanderContent { padding: 10px 12px !important; }
    [data-testid="stExpander"] .streamlit-expanderContent p { margin-bottom: 4px !important; font-size: 12px !important; }
    [data-testid="stExpander"] .streamlit-expanderContent .stSelectbox { margin-top: 8px !important; }

    @media (max-width: 768px) {
        .big-counter { font-size: 48px; }
        .tablet-header { font-size: 16px; padding: 10px 12px; }
        .home-screen { padding: 5px; }
        .tabla-header { font-size: 9px; grid-template-columns: 60px 40px 1fr 80px 90px; padding: 6px 8px; }
        .tabla-fila { font-size: 11px; grid-template-columns: 60px 40px 1fr 80px 90px; padding: 6px 8px; }
        .asig-rapida-header { display: none; }
        .asig-rapida-fila { grid-template-columns: 1fr 1fr; gap: 6px; padding: 10px; }
        .asig-rapida-fila > div:nth-child(1) { grid-column: 1 / -1; }
        .asig-rapida-fila > div:nth-child(2) { grid-column: 1; }
        .asig-rapida-fila > div:nth-child(3) { grid-column: 2; text-align: right; }
        .asig-rapida-fila > div:nth-child(4) { grid-column: 1; }
        .asig-rapida-fila > div:nth-child(5) { grid-column: 2; }
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

    /* === ASIGNACIÓN RÁPIDA: CHECKBOX PEGADO A LA TARJETA === */
    .asig-rapida-fila { margin-bottom: 2px !important; }
    div[data-testid="stHorizontalBlock"]:has(.asig-rapida-fila) > div[data-testid="column"]:first-child {
        padding-right: 2px !important;
        min-width: 24px !important;
        max-width: 28px !important;
        flex: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.asig-rapida-fila) > div[data-testid="column"]:nth-child(2) {
        padding-left: 2px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.asig-rapida-fila) {
        gap: 0px !important;
        margin-bottom: 2px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.asig-rapida-fila) div[data-testid="stCheckbox"] {
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.asig-rapida-fila) div[data-testid="stCheckbox"] > label {
        min-height: 18px !important;
        padding: 0 !important;
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== TÉCNICOS ====================
TECNICOS_ELE = [
    "RIVERA SANTOS LUIS ALVARO", "NESTOR LEONARDO CORTES TORRES", "JAVIER FELIPE ROZO CALDERON",
     "YUPER YAIL CASTILLO", "ERIK SANTIAGO MARTINEZ HERRERA",
    "JHONATAN ALARCON", "PULIDO RIOS JAHIR", "CASTAÑEDA ORTIZ EDISON ORACIO", 
    "DIAZ SEGURA DANIEL STEVEN", "FRANCO SIERRA JOSE ALEJANDRO",
    "MOJICA GARCES JEAN CARLOS", "JUAN DAVID CHACON VELANDIA"
]
TECNICOS_MEC = [
     "LUIS FERNANDO DELGADO CARMONA", "SAENZ SAENZ CARLOS EFREN",
    "PABLO ENRRIQUE TORRES BARON", "FELIPE LATORRE DIAZ", "MOLINA GONZALEZ MICHAEL ANDRES",
    "MURILLO MURILLO WILLIAM OBER", "MOLANO ALFONSO LUIS", "PINILLA ARIAS JHONATAN FERNANDO",
    "VARGAS VARGAS JHON ALEJANDER", "MERIÑO GIL JOSE MANUEL", "DILAN MEDINA",
    "RODRIGUEZ CAMACHO LUIS ALVEIRO", "MENDIVIELSO CANTOR JUAN CARLOS", "ARIAS  PERDOMO JUAN ESTEBAN",
    "VELASQUEZ OSPINA CRISTIAN JAIR"
]

def obtener_tecnicos_por_especialidad(especialidad):
    return {"ELE": TECNICOS_ELE, "MEC": TECNICOS_MEC}.get(especialidad, TECNICOS_ELE + TECNICOS_MEC)

def obtener_especialidad_tecnico(nombre):
    if nombre in TECNICOS_ELE:
        return "ELE"
    if nombre in TECNICOS_MEC:
        return "MEC"
    return ""

def abreviar_tecnico(nombre):
    """Convierte 'RIVERA SANTOS LUIS ALVARO' → 'R. SANTOS' (solo para gráficas)"""
    if not nombre or nombre in ("Sin asignar", "", "—"):
        return "—"
    partes = nombre.strip().split()
    if len(partes) >= 2:
        return f"{partes[0][0]}. {partes[1]}"
    return nombre

def contar_ordenes_por_tecnico(df, tecnico):
    if df.empty:
        return 0
    count = 0
    if "Tecnico_Asignado" in df.columns:
        count += len(df[df["Tecnico_Asignado"] == tecnico])
    if "Tecnico_Asignado_2" in df.columns:
        count += len(df[df["Tecnico_Asignado_2"] == tecnico])
    return count

def obtener_tecnicos_con_carga(df, especialidad="Todas"):
    tecnicos = [{"nombre": t, "especialidad": obtener_especialidad_tecnico(t),
                 "carga": contar_ordenes_por_tecnico(df, t)}
                for t in obtener_tecnicos_por_especialidad(especialidad)]
    tecnicos.sort(key=lambda x: x["carga"])
    return tecnicos

# ==================== HELPERS DE DATOS ====================
def cargar_excel_mantenimiento():
    try:
        return cargar_ordenes_supabase()
    except Exception as e:
        st.error(f"Error al cargar ordenes: {e}")
        return pd.DataFrame()

def recargar_datos(forzar=False):
    if forzar or "df_mantenimientos" not in st.session_state:
        df = cargar_ordenes_supabase()
        st.session_state.df_mantenimientos = df
    return st.session_state.df_mantenimientos
def calcular_progreso(df):
    total = len(df)
    if total == 0:
        return 0, 0, 0
    pct_ejec = round(len(df[df["Estado"] == "Ejecutado"]) / total * 100, 1)
    pct_verif = round(len(df[df["Estado"] == "Verificado"]) / total * 100, 1)
    return pct_ejec, round(100 - pct_ejec - pct_verif, 1), pct_verif

def obtener_estado_visual(estado):
    return {"Ejecutado": "estado-ejecutado", "Verificado": "estado-verificado"}.get(estado, "estado-pendiente")

def obtener_color_prioridad(prioridad):
    colores = {
        "Rojo": {"label": "CRITICO", "desc": "Si o si se debe realizar"},
        "Amarillo": {"label": "SECUNDARIO", "desc": "Realizar despues de las obligatorias"},
        "Verde": {"label": "ESTANDAR", "desc": "Actividad simple, poco requisito"},
        "": {"label": "SIN CLASIFICAR", "desc": "No definida"}
    }
    return colores.get(prioridad, colores[""])

def obtener_clase_css_prioridad(prioridad):
    return {"Rojo": "prioridad-critico", "Amarillo": "prioridad-secundario", "Verde": "prioridad-estandar"}.get(prioridad, "")

def extraer_maquina_nodo(nodo):
    if pd.isna(nodo) or str(nodo).strip() == "":
        return "SIN_NODO"
    partes = str(nodo).split("-")
    return partes[0] if partes else str(nodo)

def extraer_subsistema_nodo(nodo):
    if pd.isna(nodo) or str(nodo).strip() == "":
        return "SIN_CODIGO"
    partes = str(nodo).split("-")
    return partes[1] if len(partes) > 1 else "SIN_CODIGO"

def obtener_maquinas_disponibles(df):
    if df.empty or "Ubicacion" not in df.columns:
        return ["Todas"]
    try:
        maquinas = [m for m in df["Ubicacion"].dropna().unique().tolist() if str(m).strip()]
        return ["Todas"] + sorted(maquinas)
    except Exception:
        return ["Todas"]

def calcular_duracion(hora_inicio, hora_fin):
    try:
        if not hora_inicio or not hora_fin:
            return None
        hi = datetime.strptime(str(hora_inicio).strip(), "%H:%M")
        hf = datetime.strptime(str(hora_fin).strip(), "%H:%M")
        total_min = int((hf - hi).total_seconds() / 60)
        if total_min < 0:
            total_min += 24 * 60
        horas, mins = total_min // 60, total_min % 60
        return f"{horas}h {mins}m" if horas > 0 else f"{mins} min"
    except Exception:
        return None

def estado_efectivo(row):
    """Si no tiene técnico pero figura Ejecutado/Verificado, se trata como Pendiente."""
    estado = limpiar(row.get("Estado"), "Pendiente")
    if not limpiar(row.get("Tecnico_Asignado"), "") and estado in ("Ejecutado", "Verificado"):
        return "Pendiente"
    return estado

def aplicar_filtros_globales(df, maquina=""):
    """Aplica especialidad + máquina + nodo/subsistema. maquina=None omite el filtro de máquina."""
    d = df.copy()
    if st.session_state.filtro_especialidad != "Todas" and "Especialidad" in d.columns:
        d = d[d["Especialidad"] == st.session_state.filtro_especialidad]
    maq = st.session_state.filtro_maquina if maquina == "" else maquina
    if maq and maq != "Todas" and "Ubicacion" in d.columns:
        d = d[d["Ubicacion"] == maq]
    if "Nodo" in d.columns:
        if st.session_state.filtro_maquina_nodo != "Todas":
            d = d[d["Nodo"].apply(extraer_maquina_nodo) == st.session_state.filtro_maquina_nodo]
        if st.session_state.filtro_subsistema_nodo != "Todos":
            d = d[d["Nodo"].apply(extraer_subsistema_nodo) == st.session_state.filtro_subsistema_nodo]
    return d

def gen_key(base, *parts):
    # Ya NO usamos perfil/pagina para no invalidar widgets al navegar
    raw = f"{base}_{'_'.join(str(p) for p in parts)}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]
def get_row_by_internal_id(df, internal_id):
    if df.empty or "ID" not in df.columns or not internal_id:
        return None, None
    mask = df["ID"].astype(str) == str(internal_id)
    if mask.any():
        idx = df[mask].index[0]
        return idx, df.loc[idx]
    return None, None

# ==================== COMPONENTES UI ====================
def header_tablet(titulo, badge=""):
    badge_html = f'<span style="font-size: 13px; opacity: 0.8;">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>{titulo}</span>{badge_html}
    </div>""", unsafe_allow_html=True)

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

def botones_nav(pagina_volver, prefix):
    col_back, col_home = st.columns(2)
    with col_back:
        if st.button("Volver", use_container_width=True, type="secondary", key=gen_key(f"{prefix}_volver")):
            st.session_state.pagina = pagina_volver
            st.rerun()
    with col_home:
        if st.button("Inicio", use_container_width=True, type="secondary", key=gen_key(f"{prefix}_inicio")):
            st.session_state.pagina = "home"
            st.session_state.orden_seleccionada = None
            st.rerun()

def render_fila_orden(row, con_comentario=False, truncar_tecnico=False):
    """Fila de tabla OT usada en 'Ordenes' y 'Mis Ordenes'. Devuelve el internal_id."""
    id_ot = limpiar(row.get("ID OT"), "SIN ID")
    internal_id = limpiar(row.get("ID"), "")
    tipo = limpiar(row.get("Especialidad"), "SIN ESP")
    descripcion = limpiar(row.get("Actividades"), "Sin descripcion")
    estado = estado_efectivo(row)
    tecnico = limpiar(row.get("Tecnico_Asignado"), "")
    tecnico2 = limpiar(row.get("Tecnico_Asignado_2"), "")
    tecnicos_str = tecnico
    if tecnico2 and tecnico2 != tecnico:
        tecnicos_str = f"{tecnico} + {tecnico2}"
    if not tecnicos_str:
        tecnicos_str = "Sin asignar"
    if truncar_tecnico:
        tecnicos_str = f"{tecnicos_str[:15]}..."
    desc_corta = descripcion[:35] + "..." if len(descripcion) > 35 else descripcion
    nodo = limpiar(row.get("Nodo"), "")
    nodo_html = f"<span class='nodo-badge-mini' style='margin-left:4px;'>{nodo}</span>" if nodo else ""
    comentario = limpiar(row.get("Comentarios"), "") if con_comentario else ""
    com_html = f"<div style='font-size:10px;color:#0EA5E9;margin-top:2px;font-style:italic;'>&#128172; {comentario}</div>" if comentario else ""
    st.markdown(f"""
    <div class="tabla-fila {obtener_clase_css_prioridad(limpiar(row.get('Prioridad_Actividad'), ''))}">
        <div class="col-id"><strong>{id_ot}</strong>{nodo_html}</div>
        <div class="col-esp">{tipo}</div>
        <div class="col-desc" title="{descripcion}">{desc_corta}{com_html}</div>
        <div class="col-estado"><span class="estado-badge {obtener_estado_visual(estado)}">{estado}</span></div>
        <div class="col-tec">{tecnicos_str}</div>
    </div>""", unsafe_allow_html=True)
    return internal_id

def panel_info_orden(row, incluir_tecnico=False):
    """Panel Equipo/Ubicación/Especialidad/Estado usado en detalle y ejecución."""
    nodo = limpiar(row.get('Nodo'), '')
    equipo = limpiar(row.get('Equipo'), 'N/A')
    ubicacion = limpiar(row.get('Ubicacion'), 'N/A')
    especialidad = limpiar(row.get('Especialidad'), 'N/A')
    estado = limpiar(row.get('Estado'), 'Pendiente')
    est_color = {"Pendiente": "#f59e0b", "Ejecutado": "#22c55e", "Verificado": "#3b82f6"}.get(estado, "#64748b")
    html = f"""<div style="background: #FFFFFF; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-top: 10px; border: 1px solid #CBD5E1; color: #0F172A;">
        <div style="font-size: 14px; line-height: 1.8;">"""
    if nodo:
        html += f'<div><strong>Nodo:</strong> {nodo}</div>'
    html += f'<div><strong>Equipo:</strong> {equipo}</div>'
    html += f'<div><strong>Ubicación:</strong> {ubicacion}</div>'
    html += f'<div><strong>Especialidad:</strong> {especialidad}</div>'
    html += f'<div><strong>Estado:</strong> <span style="color:{est_color}; font-weight:700;">{estado}</span></div>'
    if incluir_tecnico:
        tec1 = limpiar(row.get("Tecnico_Asignado"), "")
        tec2 = limpiar(row.get("Tecnico_Asignado_2"), "")
        tec_label = "Sin asignar"
        if tec1 and tec2 and tec1 != tec2:
            tec_label = f"{tec1} + {tec2}"
        elif tec1:
            tec_label = tec1
        elif tec2:
            tec_label = tec2
        html += f'<div><strong>Técnico Asignado:</strong> {tec_label}</div>'
    html += """</div></div>"""
    st.markdown(html, unsafe_allow_html=True)

def gauge_progreso(titulo, pct, color_restante, label_centro, val_a, label_a, color_a, val_b, label_b, color_b):
    arc = 251.33
    verde = round(arc * pct / 100, 2)
    resto = round(arc - verde, 2)
    st.markdown(f"""
    <div style="background:#FFFFFF; border-radius:16px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,.08); border:1px solid #E2E8F0;">
        <div style="font-size:13px; font-weight:700; color:#0F172A; margin-bottom:6px; text-align:center;">{titulo}</div>
        <div style="display:flex; justify-content:center;">
            <svg width="180" height="105" viewBox="0 0 220 125">
                <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#E2E8F0" stroke-width="22" stroke-linecap="round"/>
                <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="#22c55e" stroke-width="22" stroke-linecap="round"
                    stroke-dasharray="{verde} {resto}" stroke-dashoffset="0"/>
                <path d="M 30 110 A 80 80 0 0 1 190 110" fill="none" stroke="{color_restante}" stroke-width="22" stroke-linecap="round"
                    stroke-dasharray="{resto} {verde}" stroke-dashoffset="-{verde}"/>
                <text x="110" y="100" text-anchor="middle" font-size="10" fill="#64748B" font-family="system-ui,sans-serif">{label_centro}</text>
                <text x="110" y="80" text-anchor="middle" font-size="28" font-weight="900" fill="#0F172A" font-family="system-ui,sans-serif">{pct}%</text>
            </svg>
        </div>
        <div style="display:flex; justify-content:center; gap:20px; margin-top:2px;">
            <div style="text-align:center;">
                <div style="font-size:16px; font-weight:800; color:{color_a};">{val_a}</div>
                <div style="font-size:9px; color:#64748B; font-weight:600;">{label_a}</div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:16px; font-weight:800; color:{color_b};">{val_b}</div>
                <div style="font-size:9px; color:#64748B; font-weight:600;">{label_b}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

def tarjeta_contador(valor, label, color):
    return (f'<div style="background: white; padding: 6px 12px; border-radius: 8px; text-align: center; '
            f'border: 2px solid {color}; min-width: 70px;">'
            f'<div style="font-size: 18px; font-weight: 800; color: {color};">{valor}</div>'
            f'<div style="font-size: 9px; color: #666;">{label}</div></div>')

def buscar_en_df(df, busqueda, columnas):
    if not busqueda:
        return df
    mask = pd.Series([False] * len(df), index=df.index)
    for col in columnas:
        if col in df.columns:
            mask |= df[col].astype(str).str.lower().str.contains(busqueda.lower(), na=False)
    return df[mask]

# ==================== SESSION STATE ====================
for k, v in {
    "perfil": None, "pagina": "login", "orden_seleccionada": None,
    "filtro_especialidad": "Todas", "filtro_maquina": "Todas",
    "filtro_esp_asig": "Todas", "filtro_maq_asig": "Todas", "filtro_estado_asig": "Todos",
    "busqueda": "", "mostrar_envio_correo": False,
    "filtro_maquina_nodo": "Todas", "filtro_subsistema_nodo": "Todos",
    "tecnico_seleccionado": "Seleccionar tecnico...", "tecnico_filtro_especialidad": "Todas",
    "mostrar_todos_tecnicos": False, "asignacion_exitosa": None,
    "mostrar_opciones_ordenes": False, "actividad_expandida": None,
    "admin_autenticado": False, "mostrar_login_admin": False,
    "asignaciones_temp": {}, "asig_rapida_msg": None
}.items():
    st.session_state.setdefault(k, v)
if "df_mantenimientos" not in st.session_state:
    st.session_state.df_mantenimientos = cargar_excel_mantenimiento()

# ==================== LOGIN ADMIN (SECRETS) ====================
def autenticar_admin(password):
    # 1. Intentar hash primero (más seguro)
    admin_hash = st.secrets.get("ADMIN_PASSWORD_HASH", "")
    if admin_hash:
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        return (True, "OK") if pwd_hash == admin_hash else (False, "Contrasena incorrecta")

    # 2. Fallback a texto plano (para no romper config actual)
    admin_pass = st.secrets.get("ADMIN_PASSWORD", "")
    if not admin_pass:
        return False, "ADMIN_PASSWORD no configurado en Secrets"
    return (True, "OK") if password == admin_pass else (False, "Contrasena incorrecta")
def pantalla_login():
    header_tablet("App Tablet Mtto Preventivo")

    # ========== DASHBOARD DE MONITOREO (visible para todos) ==========
    df = cargar_excel_mantenimiento()
    if not df.empty:
        st.markdown("<div style='font-size:16px; font-weight:700; color:#0F172A; margin: 12px 0 10px 0;'>📊 Avance por Especialidad — Diagrama de Proceso</div>", unsafe_allow_html=True)

        col_e, col_m = st.columns(2)

        for col, esp_label, esp_color, esp_code in [(col_e, "ELE", "#3B82F6", "ELE"), (col_m, "MEC", "#22C55E", "MEC")]:
            with col:
                if "Especialidad" in df.columns:
                    df_esp = df[df["Especialidad"] == esp_code]
                else:
                    df_esp = df

                total_esp = len(df_esp)
                if total_esp == 0:
                    st.info(f"📭 Sin datos {esp_label}")
                    continue

                pend = len(df_esp[df_esp["Estado"] == "Pendiente"]) if "Estado" in df_esp.columns else 0
                ejec = len(df_esp[df_esp["Estado"] == "Ejecutado"]) if "Estado" in df_esp.columns else 0
                verif = len(df_esp[df_esp["Estado"] == "Verificado"]) if "Estado" in df_esp.columns else 0
                pct_avance = round((ejec + verif) / total_esp * 100, 1) if total_esp else 0

                st.markdown(f"""
                <div style="background: white; border-radius: 14px; padding: 16px; border: 2px solid {esp_color}; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                        <div style="font-size: 18px; font-weight: 800; color: {esp_color};">⚡ {esp_label}</div>
                        <div style="font-size: 24px; font-weight: 900; color: #0F172A;">{pct_avance}%</div>
                    </div>
                    <div style="width: 100%; height: 28px; background: #F1F5F9; border-radius: 14px; overflow: hidden; margin-bottom: 12px; position: relative;">
                        <div style="width: {pct_avance}%; height: 100%; background: linear-gradient(90deg, {esp_color}, {esp_color}aa); border-radius: 14px;"></div>
                        <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 11px; font-weight: 700; color: #0F172A;">{total_esp} actividades</div>
                    </div>
                    <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px;">
                        <div style="flex: 1; text-align: center;">
                            <div style="width: 36px; height: 36px; background: {'#F59E0B' if pend > 0 else '#E2E8F0'}; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 800; margin: 0 auto 4px;">{pend}</div>
                            <div style="font-size: 9px; color: #64748B; font-weight: 600; text-transform: uppercase;">Pendiente</div>
                        </div>
                        <div style="color: #CBD5E1; font-size: 16px;">→</div>
                        <div style="flex: 1; text-align: center;">
                            <div style="width: 36px; height: 36px; background: {'#22C55E' if ejec > 0 else '#E2E8F0'}; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 800; margin: 0 auto 4px;">{ejec}</div>
                            <div style="font-size: 9px; color: #64748B; font-weight: 600; text-transform: uppercase;">Ejecutado</div>
                        </div>
                        <div style="color: #CBD5E1; font-size: 16px;">→</div>
                        <div style="flex: 1; text-align: center;">
                            <div style="width: 36px; height: 36px; background: {'#3B82F6' if verif > 0 else '#E2E8F0'}; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 800; margin: 0 auto 4px;">{verif}</div>
                            <div style="font-size: 9px; color: #64748B; font-weight: 600; text-transform: uppercase;">Verificado</div>
                        </div>
                    </div>
                    <div style="margin-top: 12px; display: flex; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: {pend/total_esp*100 if total_esp else 0}%; background: #F59E0B;"></div>
                        <div style="width: {ejec/total_esp*100 if total_esp else 0}%; background: #22C55E;"></div>
                        <div style="width: {verif/total_esp*100 if total_esp else 0}%; background: #3B82F6;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Torta general


    st.markdown("""
    <div style="text-align: center; padding: 10px 0 20px 0;">
        <div style="font-size: 14px; color: #666; margin-bottom: 20px;">Selecciona tu perfil para continuar</div>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="perfil-card perfil-admin" style="text-align: center; padding: 20px;">
            <div class="perfil-icon">&#128100;</div>
            <div class="perfil-titulo" style="color: #dc3545;">ADMIN</div>
            <div class="perfil-desc"><div>Asigna tecnicos</div><div>Verifica ejecuciones</div></div>
        </div>""", unsafe_allow_html=True)
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
            <div class="perfil-desc"><div>Ve sus ordenes</div><div>Ejecuta actividades</div></div>
        </div>""", unsafe_allow_html=True)
        if st.button("ENTRAR COMO TECNICO", use_container_width=True, type="primary", key=gen_key("login_tecnico")):
            st.session_state.perfil = "tecnico"
            st.session_state.pagina = "home"
            st.rerun()

# ==================== PANTALLA: HOME ====================
def _home_envio_correo(df):
    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        col_title, col_close = st.columns([5, 1])
        with col_title:
            st.markdown("**📧 Configurar envío de reporte**")
        with col_close:
            if st.button("❌", use_container_width=True, type="secondary", key="btn_cerrar_correo"):
                st.session_state.mostrar_envio_correo = False
                st.rerun()
        col1, col2 = st.columns(2)
        with col1:
            dest = st.multiselect("Destinatarios", DESTINATARIOS_DEFAULT, default=DESTINATARIOS_DEFAULT, key="mail_dest")
        with col2:
            area = st.text_input("Área / Mecánica", value="INY4 MEC", key="mail_area")
        if st.button("📤 ENVIAR AHORA", use_container_width=True, type="primary", key="btn_send_mail"):
            ok, msg = enviar_correo_preventivo(df, dest, f"Reporte Preventivo {area}", area)
            if ok:
                st.success(msg)
                st.session_state.mostrar_envio_correo = False
            else:
                st.error(msg)

def pantalla_home():
    perfil = st.session_state.perfil
    df = recargar_datos()
    header_tablet("App Tablet Mtto", "&#128100; Admin" if perfil == "admin" else "&#128295; Tecnico")

    if perfil == "admin" and not df.empty:
        # ========== GAUGES DE ASIGNACIÓN Y VERIFICACIÓN ==========
        total_act = len(df)
        asignadas = 0
        if total_act > 0 and "Tecnico_Asignado" in df.columns:
            asignadas = len(df[df["Tecnico_Asignado"].notna() & (df["Tecnico_Asignado"] != "")])
        pendientes_asig = total_act - asignadas
        pct_asig = round(asignadas / total_act * 100, 1) if total_act else 0

        verificadas = 0
        ejecutadas = 0
        if "Estado" in df.columns:
            verificadas = len(df[df["Estado"] == "Verificado"])
            ejecutadas = len(df[df["Estado"] == "Ejecutado"])
        total_verif = verificadas + ejecutadas
        pct_verif = round(verificadas / total_verif * 100, 1) if total_verif else 0

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            gauge_progreso("⏱️ Progreso de Asignación", pct_asig, "#ef4444", "Completado",
                           asignadas, "Asignadas", "#22c55e",
                           pendientes_asig, "Pendientes", "#ef4444")
        with col_g2:
            gauge_progreso("✅ Progreso de Verificación", pct_verif, "#f59e0b", "Verificadas",
                           verificadas, "Verificadas", "#22c55e",
                           ejecutadas, "Ejecutadas", "#f59e0b")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # ========== GRÁFICA DE TORTA GENERAL ==========
    if perfil == "admin":
        st.markdown("<div style='text-align: center; margin: 15px 0 10px 0; font-weight: 600; color: #666;'>Filtrar por Especialidad</div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        for col, esp in zip([col1, col2, col3], ["Todas", "ELE", "MEC"]):
            with col:
                activo = st.session_state.filtro_especialidad == esp
                if st.button(esp.upper(), use_container_width=True, type="primary" if activo else "secondary", key=gen_key(f"btn_filtro_{esp}")):
                    st.session_state.filtro_especialidad = esp
                    if esp != "Todas":
                        st.session_state.pagina = "asignacion"
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

        col_btn1, col_btn3 = st.columns(2)
        with col_btn1:
            if st.button("VER ORDENES ▼", use_container_width=True, type="primary", key=gen_key("btn_ver_ordenes_toggle")):
                st.session_state.mostrar_opciones_ordenes = not st.session_state.mostrar_opciones_ordenes
                st.rerun()
        with col_btn3:
            if st.button("ENVIAR REPORTE POR CORREO", use_container_width=True, type="primary", key=gen_key("btn_abrir_correo")):
                st.session_state.mostrar_envio_correo = True
                st.rerun()
        if st.session_state.mostrar_opciones_ordenes:
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            col_op1, col_op2 = st.columns(2)
            with col_op1:
                if st.button("PREVENTIVAS", use_container_width=True, type="secondary", key=gen_key("btn_ver_preventivas")):
                    st.session_state.mostrar_opciones_ordenes = False
                    st.session_state.pagina = "ordenes"
                    st.rerun()
            with col_op2:
                if st.button("EJECUTADAS", use_container_width=True, type="secondary", key=gen_key("btn_ver_ejecutadas")):
                    st.session_state.mostrar_opciones_ordenes = False
                    st.session_state.pagina = "verificar"
                    st.rerun()
        if st.button("🔄 SINCRONIZAR EXCEL", use_container_width=True, type="primary", key=gen_key("btn_sincronizar_home")):
            st.session_state.pagina = "sincronizar"
            st.rerun()

    elif perfil == "tecnico":
        _home_tecnico(df)

    if perfil == "admin" and st.session_state.mostrar_envio_correo:
        _home_envio_correo(df)

    st.markdown("<br>", unsafe_allow_html=True)
    boton_cerrar_sesion()


def _chk_key(internal_id):
    """Genera la key única del checkbox para una actividad."""
    return gen_key("chk_eq", internal_id)


def _home_tecnico(df):
    tecnicos_info = obtener_tecnicos_con_carga(df, "Todas")
    opciones = ["Seleccionar tecnico..."] + [t["nombre"] for t in tecnicos_info]
    idx_tec = next((i + 1 for i, t in enumerate(tecnicos_info)
                    if t["nombre"] == st.session_state.tecnico_seleccionado), 0)
    tecnico_sel = st.selectbox("Selecciona tu nombre:", opciones, index=idx_tec, key=gen_key("sel_tecnico_home"))
    st.session_state.tecnico_seleccionado = tecnico_sel
    if tecnico_sel == "Seleccionar tecnico...":
        return

    tecnico_actual = tecnico_sel
    esp_sel = obtener_especialidad_tecnico(tecnico_actual)
    df = recargar_datos()
    mask_tec = pd.Series([False] * len(df), index=df.index)
    if "Tecnico_Asignado" in df.columns:
        mask_tec |= df["Tecnico_Asignado"] == tecnico_actual
    if "Tecnico_Asignado_2" in df.columns:
        mask_tec |= df["Tecnico_Asignado_2"] == tecnico_actual
    df_mias = df[mask_tec].copy() if mask_tec.any() else df.copy()

    total_asignadas = len(df_mias)
    conteos = {est: len(df_mias[df_mias["Estado"] == est]) if "Estado" in df_mias.columns else 0
               for est in ["Pendiente", "Ejecutado", "Verificado"]}

    st.markdown(f"""
    <div style="text-align: center; margin: 15px 0 8px 0;">
        <div style="font-size: 14px; font-weight: 700; color: #1a237e;">{tecnico_actual}</div>
        <div style="font-size: 11px; color: #666;">Especialidad: {esp_sel}</div>
    </div>
    <div style="display: flex; gap: 8px; justify-content: center; margin: 10px 0; flex-wrap: wrap;">
        {tarjeta_contador(total_asignadas, "Total", "#1a237e")}
        {tarjeta_contador(conteos["Pendiente"], "Pendientes", "#ffc107")}
        {tarjeta_contador(conteos["Ejecutado"], "Ejecutadas", "#28a745")}
        {tarjeta_contador(conteos["Verificado"], "Verificadas", "#007bff")}
    </div>""", unsafe_allow_html=True)

    st.subheader(f"Mostrando {len(df_mias)} de {total_asignadas} ordenes")

    df_pendientes = df_mias[df_mias["Estado"].isin(["Pendiente", "", None, "NaN"])]
    if df_pendientes.empty and not df_mias.empty:
        st.success("🎉 ¡Todas las actividades están completadas! No quedan tareas pendientes.")
        st.balloons()
        return
    if df_mias.empty:
        st.info("No tienes ordenes con los filtros seleccionados.")
        return

    # === ESTRUCTURA: Ubicación → Equipo → Actividades ===
    for ubicacion_raw, grupo_ubi_df in df_pendientes.groupby(["Ubicacion"]):
        ubicacion = ubicacion_raw[0] if isinstance(ubicacion_raw, tuple) else ubicacion_raw
        grupo_ubi_df = grupo_ubi_df.copy()
        if grupo_ubi_df.empty:
            continue
        ubi_key = str(ubicacion).replace(" ", "_").replace("-", "_").replace(".", "")

        st.markdown(f"""
        <div style="background: linear-gradient(180deg, #0F172A 0%, #0B1120 100%); border-radius: 16px; margin-bottom: 12px; color: #0F172A; border: 1px solid #1E3A5F; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.25);">
            <div style="background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%); padding: 12px 16px; text-align: center;">
                <div style="font-size: 18px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;">📍 {ubicacion}</div>
            </div>
            <div style="padding: 10px 14px;">""", unsafe_allow_html=True)

        for equipo_raw, grupo_eq_df in grupo_ubi_df.groupby(["Equipo"]):
            equipo = equipo_raw[0] if isinstance(equipo_raw, tuple) else equipo_raw
            equipo_limpio = limpiar(equipo, "Sin equipo")
            grupo_eq_df = grupo_eq_df.copy()
            if grupo_eq_df.empty:
                continue

            total_act = len(grupo_eq_df)
            tecnico_bloque = grupo_eq_df["Tecnico_Asignado"].mode()
            tecnico_bloque = tecnico_bloque[0] if len(tecnico_bloque) > 0 else "Sin asignar"
            eq_key = ubi_key + "__" + str(equipo_limpio).replace(" ", "_").replace("-", "_").replace(".", "")

            # Contar realizadas basado en ESTADO de BD
            realizadas_bd = len(grupo_eq_df[grupo_eq_df["Estado"].isin(["Ejecutado", "Verificado"])])
            pct_realizadas = round(realizadas_bd / total_act * 100, 1) if total_act else 0
            estado_bloque = "Completado" if realizadas_bd == total_act and total_act > 0 else "Pendiente"

            st.markdown(f"""
            <div class="eq-bloque" style="margin-bottom: 10px; border-radius: 12px; overflow: hidden; border: 1px solid #1E3A5F;">
                <div class="eq-bloque-header" style="padding: 10px 14px;">
                    <div style="flex:1; min-width:0;">
                        <div class="eq-bloque-titulo">🔧 {equipo_limpio}</div>
                        <div class="eq-bloque-meta">
                            👤 {tecnico_bloque} | 📋 {total_act} actividades | ✅ {realizadas_bd} realizadas
                        </div>
                        <div class="eq-progress-bar">
                            <div class="eq-progress-fill" style="width: {pct_realizadas}%;"></div>
                        </div>
                    </div>
                    <span class="estado-badge {'eq-estado-ej' if estado_bloque == 'Completado' else 'eq-estado-pd'}" style="margin-left:12px; flex-shrink:0;">{estado_bloque}</span>
                </div>
                <div class="eq-bloque-contenido">""", unsafe_allow_html=True)

            for _, row in grupo_eq_df.iterrows():
                internal_id = limpiar(row.get("ID"), "")
                if not internal_id:
                    continue
                desc = limpiar(row.get("Actividades"), "Sin descripcion")
                estado = limpiar(row.get("Estado"), "Pendiente")
                ya_ejecutada = estado in ["Ejecutado", "Verificado"]

                # === FIX CRÍTICO: 1 sola fuente de verdad — el session_state del widget ===
                chk_key = _chk_key(internal_id)
                if chk_key not in st.session_state:
                    st.session_state[chk_key] = ya_ejecutada

                cols_fila = st.columns([0.02, 1], gap="small")
                with cols_fila[0]:
                    chk_val = st.checkbox("", key=chk_key, label_visibility="collapsed")
                    if chk_val and not ya_ejecutada and not st.session_state.get(f"hora_ini_auto_{internal_id}"):
                        st.session_state[f"hora_ini_auto_{internal_id}"] = datetime.now().strftime("%H:%M")

                with cols_fila[1]:
                    clase_ej = "ejecutada" if (chk_val or ya_ejecutada) else ""
                    st.markdown(f"""
                    <div class="fila-compacta {clase_ej}">
                        <span class="fila-desc" style="flex:1; font-size:13px; line-height:1.4;">{desc}</span>
                        <span class="estado-badge {'eq-estado-ej' if estado == 'Ejecutado' else 'eq-estado-pd'}" style="flex-shrink:0; margin-left:2px;">{estado}</span>
                    </div>""", unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

        _bloque_acciones_ubicacion(ubi_key, grupo_ubi_df)
        st.markdown("</div></div>", unsafe_allow_html=True)


def _bloque_acciones_ubicacion(ubi_key, grupo_ubi_df):
    """Comentario general + botones Desmarcar/Guardar de un bloque de ubicación."""
    comentario_key = f"com_ubi_{ubi_key}"
    st.session_state.setdefault(comentario_key, "")
    st.text_input("💬 Comentario general del bloque:", value=st.session_state[comentario_key],
                  key=comentario_key, placeholder="Escribe un comentario para todas las actividades de este bloque...")
    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    col_desmarcar, col_guardar = st.columns(2)
    with col_desmarcar:
        if st.button("✕ Desmarcar todas", use_container_width=True, type="secondary", key=gen_key("btn_desmarcar_todas_ubi", ubi_key)):
            for _, row in grupo_ubi_df.iterrows():
                internal_id = limpiar(row.get("ID"), "")
                if internal_id:
                    chk_key = _chk_key(internal_id)
                    st.session_state[chk_key] = False
                    st.session_state.pop(f"hora_ini_auto_{internal_id}", None)
            st.rerun()

    with col_guardar:
        if st.button("💾 Guardar", use_container_width=True, type="primary", key=gen_key("btn_guardar_ubi", ubi_key)):
            _guardar_bloque_ubicacion(ubi_key, grupo_ubi_df, comentario_key)


def _guardar_bloque_ubicacion(ubi_key, grupo_ubi_df, comentario_key):
    guardados = 0
    comentario_general = st.session_state.get(comentario_key, "")
    for _, row in grupo_ubi_df.iterrows():
        internal_id = limpiar(row.get("ID"), "")
        if not internal_id:
            continue
        chk_key = _chk_key(internal_id)
        chk_val = st.session_state.get(chk_key, False)
        estado_actual = limpiar(row.get("Estado"), "Pendiente")
        comentario_bd = limpiar(row.get("Comentarios"), "")
        cambia_comentario = comentario_general != comentario_bd

        if chk_val and estado_actual not in ["Ejecutado", "Verificado"]:
            hora_fin = datetime.now().strftime("%H:%M")
            hora_ini = (st.session_state.get(f"hora_ini_auto_{internal_id}", "")
                        or limpiar(row.get("Hora_Inicio"), "") or hora_fin)
            datos = {"Estado": "Ejecutado", "Hora_Inicio": hora_ini, "Hora_Fin": hora_fin,
                     "Fecha_Ejecucion": datetime.now().strftime("%Y-%m-%d")}
            if cambia_comentario:
                datos["Comentarios"] = comentario_general
            if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
                guardados += 1
                st.session_state.pop(f"hora_ini_auto_{internal_id}", None)
                st.session_state.pop(chk_key, None)

        elif not chk_val and estado_actual == "Ejecutado":
            datos = {"Estado": "Pendiente"}
            if cambia_comentario:
                datos["Comentarios"] = comentario_general
            if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
                guardados += 1
                st.session_state.pop(chk_key, None)

        elif cambia_comentario:
            if actualizar_orden_supabase(internal_id, "Comentarios", comentario_general):
                guardados += 1

    if guardados > 0:
        st.success(f"✅ {guardados} cambios guardados en Supabase")
        st.rerun()
    else:
        st.info("No hay cambios para guardar")
# ==================== PANTALLA: ORDENES (ADMIN) ====================
def pantalla_ordenes():
    df = recargar_datos()
    header_tablet("Ordenes Preventivas", st.session_state.filtro_especialidad)
    boton_volver_inicio("ordenes")

    busqueda = st.text_input("Buscar ID OT, equipo o descripcion...", value=st.session_state.busqueda,
                             placeholder="Escribe para buscar...", key=gen_key("txt_busqueda_ordenes"))
    st.session_state.busqueda = busqueda

    pct_ejec, pct_pdte, pct_verif = calcular_progreso(df)
    st.markdown(f"""
    <div class="progress-bar-container">
        <div class="progress-item"><div class="progress-value" style="color:#28a745">{pct_ejec}%</div><div class="progress-label">Ejecutado</div></div>
        <div class="progress-item"><div class="progress-value" style="color:#dc3545">{pct_pdte}%</div><div class="progress-label">Pendiente</div></div>
        <div class="progress-item"><div class="progress-value" style="color:#007bff">{pct_verif}%</div><div class="progress-label">Verificado</div></div>
    </div>""", unsafe_allow_html=True)

    df_filtrado = aplicar_filtros_globales(df)
    df_filtrado = buscar_en_df(df_filtrado, busqueda, ["Equipo", "Ubicacion", "ID OT", "Actividades", "Nodo"])

    st.markdown("""
    <div class="tabla-header">
        <div class="col-id">ID OT</div><div class="col-esp">ESP</div><div class="col-desc">DESCRIPCION</div>
        <div class="col-estado">ESTADO</div><div class="col-tec">TECNICO</div>
    </div>""", unsafe_allow_html=True)

    for _, row in df_filtrado.iterrows():
        internal_id = render_fila_orden(row, con_comentario=True)
        if st.button("Ver detalle", key=gen_key("btn_ver", internal_id), use_container_width=True):
            st.session_state.orden_seleccionada = internal_id
            st.session_state.pagina = "detalle"
            st.rerun()

# ==================== PANTALLA: MIS ORDENES (TÉCNICO) ====================
def pantalla_mis_ordenes():
    df = recargar_datos()
    header_tablet("Mis Ordenes Asignadas")
    boton_volver_inicio("mis_ordenes")

    tecnico_sel = st.session_state.get("tecnico_seleccionado", "Seleccionar tecnico...")
    if tecnico_sel == "Seleccionar tecnico...":
        st.warning("Por favor selecciona tu nombre en la pantalla principal.")
        if st.button("VOLVER AL INICIO", use_container_width=True, key=gen_key("btn_volver_sel_tec")):
            st.session_state.pagina = "home"
            st.rerun()
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_estado = st.selectbox("Filtrar por estado", ["Todos", "Pendiente", "Ejecutado", "Verificado"],
                                     index=0, key=gen_key("filtro_estado_tec"))
    with col_f2:
        busq_tec = st.text_input("Buscar...", placeholder="ID OT o equipo", key=gen_key("busq_tec"))

    mask_tec = pd.Series([False] * len(df), index=df.index)
    if "Tecnico_Asignado" in df.columns:
        mask_tec |= df["Tecnico_Asignado"] == tecnico_sel
    if "Tecnico_Asignado_2" in df.columns:
        mask_tec |= df["Tecnico_Asignado_2"] == tecnico_sel
    df_mias = df[mask_tec].copy() if mask_tec.any() else pd.DataFrame()
    if filtro_estado != "Todos" and "Estado" in df_mias.columns:
        df_mias = df_mias[df_mias["Estado"] == filtro_estado]
    df_mias = buscar_en_df(df_mias, busq_tec, ["ID OT", "Equipo"])

    mask_tec_all = pd.Series([False] * len(df), index=df.index)
    if "Tecnico_Asignado" in df.columns:
        mask_tec_all |= df["Tecnico_Asignado"] == tecnico_sel
    if "Tecnico_Asignado_2" in df.columns:
        mask_tec_all |= df["Tecnico_Asignado_2"] == tecnico_sel
    if mask_tec_all.any():
        df_todas = df[mask_tec_all]
        total_asignadas = len(df_todas)
        pendientes = len(df_todas[df_todas["Estado"] == "Pendiente"])
        ejecutadas = len(df_todas[df_todas["Estado"] == "Ejecutado"])
    else:
        total_asignadas = pendientes = ejecutadas = 0

    st.markdown(f"""
    <div style="display: flex; gap: 10px; justify-content: center; margin: 10px 0;">
        {tarjeta_contador(total_asignadas, "Total Asignadas", "#1a237e")}
        {tarjeta_contador(pendientes, "Pendientes", "#ffc107")}
        {tarjeta_contador(ejecutadas, "Ejecutadas", "#28a745")}
    </div>""", unsafe_allow_html=True)

    st.subheader(f"Mostrando {len(df_mias)} orden(es)")
    if df_mias.empty:
        st.info("No tienes ordenes con los filtros seleccionados.")
        return

    for _, row in df_mias.iterrows():
        internal_id = render_fila_orden(row, truncar_tecnico=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ver detalle", key=gen_key("btn_ver_tec", internal_id), use_container_width=True):
                st.session_state.orden_seleccionada = internal_id
                st.session_state.pagina = "detalle_tecnico"
                st.rerun()
        with col2:
            if estado_efectivo(row) == "Pendiente" and st.button("Ejecutar", key=gen_key("btn_ejec", internal_id), use_container_width=True, type="primary"):
                st.session_state.orden_seleccionada = internal_id
                st.session_state.pagina = "ejecutar"
                st.rerun()

# ==================== PANTALLA: EJECUTAR ====================
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

    header_tablet(f"Ejecutar OT {limpiar(row.get('ID OT'), 'SIN ID')}")
    botones_nav("mis_ordenes", "ejec")
    panel_info_orden(row)

    st.markdown("<h3 style='color:#0F172A'>Descripcion del Procedimiento</h3>", unsafe_allow_html=True)
    st.markdown(f'<p style="color:#0F172A; font-size:14px; line-height:1.6;">{limpiar(row.get("Actividades"), "Sin descripcion")}</p>', unsafe_allow_html=True)
    st.markdown("<h3 style='color:#0F172A'>Registro de Ejecucion</h3>", unsafe_allow_html=True)

    def _hora_default(campo):
        try:
            return datetime.strptime(limpiar(row.get(campo), ""), "%H:%M").time()
        except Exception:
            return datetime.now().time()

    col1, col2 = st.columns(2)
    with col1:
        hora_inicio = st.time_input("Hora Inicio", value=_hora_default("Hora_Inicio"), key=gen_key("hora_inicio_ejec"))
    with col2:
        hora_fin = st.time_input("Hora Fin", value=_hora_default("Hora_Fin"), key=gen_key("hora_fin_ejec"))

    st.markdown("<h3 style='color:#0F172A'>Comentarios de Ejecucion</h3>", unsafe_allow_html=True)
    nuevo_comentario = st.text_area("Describa lo realizado...", value=limpiar(row.get("Comentarios"), ""), key=gen_key("comentario_ejecucion"))

    hora_valida = hora_fin >= hora_inicio
    if not hora_valida:
        st.warning("⚠️ La hora de fin es anterior a la hora de inicio. Por favor verifica.")

    if st.button("MARCAR COMO EJECUTADO", use_container_width=True, type="primary", key=gen_key("btn_marcar_ejecutado"), disabled=not hora_valida):
        datos = {"Estado": "Ejecutado", "Comentarios": nuevo_comentario,
                 "Fecha_Ejecucion": datetime.now().strftime("%Y-%m-%d"),
                 "Hora_Inicio": hora_inicio.strftime("%H:%M"), "Hora_Fin": hora_fin.strftime("%H:%M")}
        if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
            for col, val in datos.items():
                df.at[idx, col] = val
            st.markdown("""
            <div style="background: #DCFCE7; color: #34d399; padding: 12px; border-radius: 8px; text-align: center; font-weight: 700; border: 1px solid #059669; margin: 12px 0;">
                ✅ Orden marcada como EJECUTADA y guardada en Supabase
            </div>""", unsafe_allow_html=True)
            st.balloons()
            st.session_state.pagina = "mis_ordenes"
            st.session_state.orden_seleccionada = None
            st.rerun()
        else:
            st.error("Error al guardar en Supabase. Intenta de nuevo.")

# ==================== PANTALLA: DETALLE TÉCNICO ====================
def pantalla_detalle_tecnico():
    df = recargar_datos()
    internal_id = st.session_state.orden_seleccionada
    idx, row = get_row_by_internal_id(df, internal_id)
    if idx is None:
        st.error("Orden no encontrada.")
        if st.button("Volver", use_container_width=True, key=gen_key("dettec_volver_err")):
            st.session_state.pagina = "mis_ordenes"
            st.session_state.orden_seleccionada = None
            st.rerun()
        return

    header_tablet(f"Detalle OT {limpiar(row.get('ID OT'), 'SIN ID')}")
    botones_nav("mis_ordenes", "dettec")

    prioridad = limpiar(row.get("Prioridad_Actividad"), "")
    if prioridad:
        info = obtener_color_prioridad(prioridad)
        st.markdown(f"""
        <div style="background: #FFFFFF; color: #475569; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #0EA5E9; margin-bottom: 16px; font-size: 13px;">
            <strong>Prioridad: {info['label']}</strong> — {info['desc']}
        </div>""", unsafe_allow_html=True)

    panel_info_orden(row, incluir_tecnico=True)
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

# ==================== PANTALLA: DETALLE (ADMIN) ====================
def pantalla_detalle():
    df = recargar_datos()
    internal_id = st.session_state.orden_seleccionada
    idx, row = get_row_by_internal_id(df, internal_id)
    if idx is None:
        st.error("Orden no encontrada.")
        if st.button("Volver", use_container_width=True, key=gen_key("det_volver_err")):
            st.session_state.pagina = "ordenes"
            st.session_state.orden_seleccionada = None
            st.rerun()
        return

    header_tablet(f"Detalle OT {limpiar(row.get('ID OT'), 'SIN ID')}")
    botones_nav("ordenes", "det")

    prioridad = limpiar(row.get("Prioridad_Actividad"), "")
    if prioridad:
        info = obtener_color_prioridad(prioridad)
        st.markdown(f"""
        <div style="background: #FFFFFF; color: #475569; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #0EA5E9; margin-bottom: 16px; font-size: 13px;">
            <strong>Prioridad: {info['label']}</strong> — {info['desc']}
        </div>""", unsafe_allow_html=True)

    panel_info_orden(row)
    st.markdown("<h3 style='color:#0F172A'>Descripcion del Procedimiento</h3>", unsafe_allow_html=True)
    st.write(limpiar(row.get("Actividades"), "Sin descripcion"))
    st.divider()
    st.subheader("&#128203; Informacion de la Orden")

    estado_actual = limpiar(row.get("Estado"), "Pendiente")
    fecha_ejec = limpiar(row.get("Fecha_Ejecucion"), "—")
    h_ini = limpiar(row.get("Hora_Inicio"), "—")
    h_fin = limpiar(row.get("Hora_Fin"), "—")
    duracion = calcular_duracion(h_ini, h_fin) if h_ini != "—" and h_fin != "—" else None
    pri_color = {"Rojo": "#ef4444", "Amarillo": "#f59e0b", "Verde": "#22c55e"}.get(prioridad, "#64748b")
    pri_label = obtener_color_prioridad(prioridad)["label"] if prioridad else "SIN CLASIFICAR"
    est_color = {"Pendiente": "#f59e0b", "Ejecutado": "#22c55e", "Verificado": "#3b82f6"}.get(estado_actual, "#64748b")

    tec1_det = limpiar(row.get("Tecnico_Asignado"), "")
    tec2_det = limpiar(row.get("Tecnico_Asignado_2"), "")
    tec_label = "Sin asignar"
    if tec1_det and tec2_det and tec1_det != tec2_det:
        tec_label = f"{tec1_det} + {tec2_det}"
    elif tec1_det:
        tec_label = tec1_det
    elif tec2_det:
        tec_label = tec2_det

    def _info_card(icono, label, valor, color_borde, color_texto="#0F172A", peso=600):
        st.markdown(f"""
        <div style="background: #F1F5F9; padding: 10px 12px; border-radius: 8px; border-left: 3px solid {color_borde}; margin-bottom: 8px;">
            <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">{icono} {label}</div>
            <div style="color:{color_texto}; font-size:13px; font-weight:{peso}; margin-top:4px;">{valor}</div>
        </div>""", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        _info_card("&#128100;", "Técnico", tec_label, "#3b82f6")
        _info_card("&#9888;", "Prioridad", pri_label, pri_color, pri_color, 700)
        _info_card("&#9200;", "Hora Inicio", h_ini, "#60a5fa")
    with col_b:
        _info_card("&#128308;", "Estado", estado_actual, est_color, est_color, 700)
        _info_card("&#128197;", "Fecha Ejecución", fecha_ejec, "#a78bfa")
        _info_card("&#9201;", "Hora Fin", h_fin, "#f472b6")

    if duracion:
        st.markdown(f"""
        <div style="background: #DCFCE7; color: #059669; text-align: center; padding: 8px; border-radius: 8px; 
        margin-top: 4px; font-size: 14px; font-weight: 700; border: 1px solid #059669;">&#9989; Duración: {duracion}</div>""", unsafe_allow_html=True)

    comentario_detalle = limpiar(row.get("Comentarios"), "")
    if comentario_detalle:
        st.markdown(f"""
        <div style="background: #FEF3C7; border-left: 4px solid #F59E0B; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px; font-size: 13px; color: #78350F;">
            <strong>💬 Comentario:</strong><br>{comentario_detalle}
        </div>""", unsafe_allow_html=True)

    if st.button("&#9998; EDITAR EN ASIGNACIONES", use_container_width=True, type="secondary", key=gen_key("det_ir_asignar")):
        st.session_state.pagina = "asignacion"
        st.rerun()
    if st.session_state.perfil in ["admin", "supervisor"] and estado_actual == "Ejecutado":
        if st.button("VERIFICAR ORDEN", use_container_width=True, type="primary", key=gen_key("det_verificar")):
            if actualizar_orden_supabase(internal_id, "Estado", "Verificado"):
                df.at[idx, "Estado"] = "Verificado"
                st.success("Orden VERIFICADA")
                st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                st.rerun()
            else:
                st.error("Error al verificar")

# ==================== PANTALLA: VERIFICAR ====================
def pantalla_verificar():
    df = recargar_datos()
    header_tablet("Verificar Ordenes Ejecutadas")
    boton_volver_inicio("verificar")

    df_ejecutadas = (df[(df["Estado"] == "Ejecutado") & df["Tecnico_Asignado"].notna() & (df["Tecnico_Asignado"] != "")]
                     if not df.empty and "Estado" in df.columns and "Tecnico_Asignado" in df.columns else pd.DataFrame())
    st.subheader(f"Ordenes ejecutadas pendientes de verificacion ({len(df_ejecutadas)})")
    if df_ejecutadas.empty:
        st.info("No hay ordenes ejecutadas pendientes de verificacion.")
        return

    for _, row in df_ejecutadas.iterrows():
        tec1_v = limpiar(row.get("Tecnico_Asignado"), "")
        tec2_v = limpiar(row.get("Tecnico_Asignado_2"), "")
        tec_label = "Sin asignar"
        if tec1_v and tec2_v and tec1_v != tec2_v:
            tec_label = f"{tec1_v} + {tec2_v}"
        elif tec1_v:
            tec_label = tec1_v
        elif tec2_v:
            tec_label = tec2_v
        internal_id = limpiar(row.get("ID"), "")
        id_ot = limpiar(row.get("ID OT"), "SIN ID")
        descripcion = limpiar(row.get("Actividades"), "Sin descripcion")
        desc_corta = descripcion[:40] + "..." if len(descripcion) > 40 else descripcion
        nodo = limpiar(row.get("Nodo"), "")
        nodo_badge = f"<span class='nodo-badge-mini'>{nodo}</span>" if nodo else ""

        st.markdown(f"""
        <div class="detail-panel" style="margin-bottom: 12px; background:#FFFFFF; border:1px solid #E2E8F0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong>OT {id_ot}</strong> {nodo_badge}
                <span class="estado-badge estado-ejecutado">Ejecutado</span>
            </div>
            <div style="font-size: 12px; color: #666;">
                <strong>{limpiar(row.get('Especialidad'), 'SIN ESP')}</strong> | {limpiar(row.get('Equipo'), 'Sin equipo')} — {limpiar(row.get('Ubicacion'), 'Sin ubicacion')}<br>
                Tecnico: {tec_label}<br>
                Ejecutado: {limpiar(row.get('Fecha_Ejecucion'), 'N/A')} | {limpiar(row.get('Hora_Inicio'), 'N/A')} - {limpiar(row.get('Hora_Fin'), 'N/A')}
            </div>
            <div style="font-size: 11px; color: #333; margin-top: 6px;">{desc_corta}</div>
        </div>""", unsafe_allow_html=True)

        with st.expander("Ver detalles y comentarios"):
            st.write(f"**Descripcion completa:** {descripcion}")
            st.write(f"**Comentarios:** {limpiar(row.get('Comentarios'), 'Sin comentarios')}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Verificado", use_container_width=True, type="primary", key=gen_key("verif_btn", internal_id)):
                    if actualizar_orden_supabase(internal_id, "Estado", "Verificado"):
                        st.success(f"OT {id_ot} verificada correctamente")
                        st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                        st.rerun()
                    else:
                        st.error("Error al verificar")
            with col2:
                if st.button("RECHAZAR", use_container_width=True, type="secondary", key=gen_key("rech_btn", internal_id)):
                    if actualizar_orden_supabase(internal_id, "Estado", "Pendiente"):
                        st.warning(f"OT {id_ot} devuelta a Pendiente")
                        st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                        st.rerun()
                    else:
                        st.error("Error al rechazar")

# ==================== ASIGNACIÓN: CALLBACKS AUTO-GUARDADO ====================
def _datos_reasignacion(nuevo_tec, estado_bd):
    """Al cambiar técnico: si estaba Ejecutado/Verificado vuelve a Pendiente y limpia registro."""
    datos = {"Tecnico_Asignado": nuevo_tec}
    if estado_bd in ["Ejecutado", "Verificado"]:
        datos.update({"Estado": "Pendiente", "Hora_Inicio": None, "Hora_Fin": None,
                      "Fecha_Ejecucion": None, "Comentarios": None})
    elif nuevo_tec == "" and estado_bd != "Pendiente":
        datos["Estado"] = "Pendiente"
    return datos

def _reflejar_en_session(idx, datos):
    if "Tecnico_Asignado" in datos:
        st.session_state.df_mantenimientos.loc[idx, "Tecnico_Asignado"] = datos["Tecnico_Asignado"]
    if "Tecnico_Asignado_2" in datos:
        st.session_state.df_mantenimientos.loc[idx, "Tecnico_Asignado_2"] = datos["Tecnico_Asignado_2"]
    if "Estado" in datos:
        st.session_state.df_mantenimientos.loc[idx, "Estado"] = datos["Estado"]

def auto_guardar_fila(internal_id, key_widget, campo="Tecnico_Asignado"):
    """Se ejecuta automáticamente cuando cambia el técnico en una fila."""
    nuevo_tec = st.session_state.get(key_widget, "")
    if nuevo_tec == "Sin asignar":
        nuevo_tec = ""
    df = st.session_state.df_mantenimientos
    idx, row = get_row_by_internal_id(df, internal_id)
    if idx is None or nuevo_tec == limpiar(row.get(campo), ""):
        return
    datos = _datos_reasignacion(nuevo_tec, limpiar(row.get("Estado"), "Pendiente"))
    datos_filtrados = {campo: datos["Tecnico_Asignado"]}
    for k in ["Estado", "Hora_Inicio", "Hora_Fin", "Fecha_Ejecucion", "Comentarios"]:
        if k in datos:
            datos_filtrados[k] = datos[k]
    if actualizar_campos_supabase(internal_id, datos_filtrados, row.to_dict()):
        _reflejar_en_session(idx, datos_filtrados)
        msg = f"✅ Guardado: OT {limpiar(row.get('ID OT'), 'SIN ID')}"
        st.session_state.asig_rapida_msg = msg
        st.toast(msg, icon="💾")

# ==================== PANTALLA: ASIGNACIÓN RÁPIDA ====================
def pantalla_asignacion():
    df = recargar_datos()
    header_tablet("Asignacion de Tecnicos")
    boton_volver_inicio("asignacion")

    if st.session_state.get("asig_rapida_msg"):
        st.toast(st.session_state.asig_rapida_msg, icon="💾")
        st.session_state.asig_rapida_msg = None

    df_asig_base = aplicar_filtros_globales(df, maquina=None)
    df_asig = df_asig_base.copy()
    if st.session_state.filtro_maquina != "Todas" and "Ubicacion" in df_asig.columns:
        df_asig = df_asig[df_asig["Ubicacion"] == st.session_state.filtro_maquina]

    col_izq, col_der = st.columns([1, 3])

    with col_izq:
        st.markdown("<div style='font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:8px;'>📍 Máquina</div>", unsafe_allow_html=True)
        for maq in obtener_maquinas_disponibles(df_asig_base):
            activo = st.session_state.filtro_maquina == maq
            if st.button(maq, key=gen_key("btn_maq", maq), type="primary" if activo else "secondary", use_container_width=True):
                st.session_state.filtro_maquina = maq
                st.rerun()

    with col_der:
        maq_sel = st.session_state.filtro_maquina
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <div style="font-size: 16px; font-weight: 700; color: #0F172A;">{maq_sel if maq_sel != "Todas" else "Todas las máquinas"}</div>
            <div style="font-size: 13px; color: #64748B;">{len(df_asig)} actividades encontradas</div>
        </div>""", unsafe_allow_html=True)







        # ========== GRÁFICA: TORTA 3D POR EQUIPO + LEYENDA POR TÉCNICO ==========
        def _render_torta_3d_equipos(datos_equipos, titulo="Distribución por Equipo"):
            import math
            if not datos_equipos:
                return ""
            total = sum(d["valor"] for d in datos_equipos)
            if total == 0:
                return ""

            colores = [
                "#E91E63", "#9C27B0", "#673AB7", "#3F51B5",
                "#2196F3", "#00BCD4", "#009688", "#8BC34A",
                "#FF9800", "#FF5722", "#795548", "#607D8B",
            ]
            colores_dark = [
                "#AD1457", "#6A1B9A", "#4527A0", "#283593",
                "#1565C0", "#00838F", "#00695C", "#558B2F",
                "#E65100", "#BF360C", "#3E2723", "#37474F",
            ]

            cx, cy = 350, 230
            rx, ry = 125, 68
            extrusion = 26
            explode = 12

            def pol2cart(cx, cy, rx, ry, ang_deg):
                rad = math.radians(ang_deg)
                return cx + rx * math.cos(rad), cy + ry * math.sin(rad)

            def en_mitad_inferior(ang):
                a = ang % 360
                if a < 0: a += 360
                return 0 <= a <= 180

            slices_data = []
            start_angle = -90
            for i, d in enumerate(datos_equipos):
                pct = round(d["valor"] / total * 100, 1)
                sweep = (d["valor"] / total) * 360
                end_angle = start_angle + sweep
                mid_angle = start_angle + sweep / 2

                off_rad = math.radians(mid_angle)
                off_x = explode * math.cos(off_rad)
                off_y = explode * math.sin(off_rad)

                slices_data.append({
                    "i": i, "nombre": d["nombre"], "valor": d["valor"],
                    "pct": pct, "start": start_angle, "end": end_angle,
                    "mid": mid_angle, "sweep": sweep,
                    "off_x": off_x, "off_y": off_y,
                    "color": colores[i % len(colores)],
                    "color_dark": colores_dark[i % len(colores_dark)]
                })
                start_angle = end_angle

            svg_parts = []
            callouts = []

            for s in slices_data:
                i = s["i"]
                ox, oy = s["off_x"], s["off_y"]
                c = s["color"]
                cd = s["color_dark"]
                sa, ea, ma = s["start"], s["end"], s["mid"]
                sw = s["sweep"]

                x1, y1 = pol2cart(cx + ox, cy + oy, rx, ry, sa)
                x2, y2 = pol2cart(cx + ox, cy + oy, rx, ry, ea)
                large_arc = 1 if sw > 180 else 0

                if sw < 360:
                    path_inf = 'M %d %d L %.1f %.1f A %d %d 0 %d 1 %.1f %.1f Z' % (
                        int(cx + ox), int(cy + oy + extrusion),
                        x1, y1 + extrusion, rx, ry, large_arc, x2, y2 + extrusion)
                    svg_parts.append('<path d="%s" fill="%s" opacity="0.30"/>' % (path_inf, cd))

                if en_mitad_inferior(sa):
                    svg_parts.append('<path d="M %.1f %.1f L %.1f %.1f L %d %d L %d %d Z" fill="%s" opacity="0.55"/>' % (
                        x1, y1, x1, y1 + extrusion, int(cx + ox), int(cy + oy + extrusion), int(cx + ox), int(cy + oy), cd))

                if en_mitad_inferior(ea):
                    svg_parts.append('<path d="M %.1f %.1f L %.1f %.1f L %d %d L %d %d Z" fill="%s" opacity="0.55"/>' % (
                        x2, y2, x2, y2 + extrusion, int(cx + ox), int(cy + oy + extrusion), int(cx + ox), int(cy + oy), cd))

                if sw < 360:
                    as_i = sa if sa > 0 else 0
                    as_e = ea if ea < 180 else 180
                    if sa < 0 and ea > 0: as_i = 0
                    if sa < 180 and ea > 180: as_e = 180
                    if as_i < as_e:
                        ix1, iy1 = pol2cart(cx + ox, cy + oy, rx, ry, as_i)
                        ix2, iy2 = pol2cart(cx + ox, cy + oy, rx, ry, as_e)
                        large_arc_inf = 1 if (as_e - as_i) > 180 else 0
                        svg_parts.append('<path d="M %.1f %.1f A %d %d 0 %d 1 %.1f %.1f L %.1f %.1f A %d %d 0 %d 0 %.1f %.1f Z" fill="%s" opacity="0.40"/>' % (
                            ix1, iy1, rx, ry, large_arc_inf, ix2, iy2, ix2, iy2 + extrusion, rx, ry, large_arc_inf, ix1, iy1 + extrusion, cd))

                if sw >= 360:
                    svg_parts.append('<ellipse cx="%d" cy="%d" rx="%d" ry="%d" fill="%s" stroke="#FFFFFF" stroke-width="2"/>' % (
                        int(cx + ox), int(cy + oy), rx, ry, c))
                else:
                    path_top = 'M %d %d L %.1f %.1f A %d %d 0 %d 1 %.1f %.1f Z' % (
                        int(cx + ox), int(cy + oy), x1, y1, rx, ry, large_arc, x2, y2)
                    svg_parts.append('<path d="%s" fill="%s" stroke="#FFFFFF" stroke-width="2"/>' % (path_top, c))

                # === CALLOUT MEJORADO ===
                mx, my = pol2cart(cx + ox, cy + oy, rx + 10, ry + 6, ma)

                box_w = 140
                box_h = 44
                line_len = 32

                if ma >= -90 and ma <= 90:
                    box_x = mx + line_len
                    line_x2 = box_x - 5
                    if box_x + box_w > 690:
                        box_x = 690 - box_w
                        line_x2 = box_x - 5
                else:
                    box_x = mx - line_len - box_w
                    line_x2 = box_x + box_w + 5
                    if box_x < 10:
                        box_x = 10
                        line_x2 = box_x + box_w + 5

                box_y = my - box_h / 2
                if box_y < 10: box_y = 10
                if box_y > 350: box_y = 350

                mid_y = box_y + box_h / 2

                callouts.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (mx, my, c))
                callouts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (mx, my, line_x2, my, c))
                callouts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>' % (line_x2, my, line_x2, mid_y, c))
                callouts.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="8" fill="white" stroke="%s" stroke-width="2.5"/>' % (box_x, box_y, box_w, box_h, c))

                nombre_corto = s["nombre"][:16]
                callouts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="9" fill="#64748B" font-family="system-ui,sans-serif" font-weight="600">%s</text>' % (box_x + box_w/2, box_y + 16, nombre_corto))
                callouts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="15" fill="%s" font-family="system-ui,sans-serif" font-weight="800">%s%%</text>' % (box_x + box_w/2, box_y + 34, c, s["pct"]))

            svg_content = '\n'.join(svg_parts + callouts)
            svg = '<svg width="100%%" height="400" viewBox="0 0 700 400" style="font-family: system-ui, sans-serif;"><rect x="0" y="0" width="700" height="400" fill="transparent"/>%s</svg>' % svg_content
            return svg

        def _render_leyenda_tecnicos(datos_tecnicos):
            if not datos_tecnicos:
                return ""
            items = []
            colores = [
                "#E91E63", "#9C27B0", "#673AB7", "#3F51B5",
                "#2196F3", "#00BCD4", "#009688", "#8BC34A",
                "#FF9800", "#FF5722", "#795548", "#607D8B",
            ]
            for i, d in enumerate(datos_tecnicos):
                c = colores[i % len(colores)]
                items.append(
                    '<div style="display:flex; align-items:center; gap:6px; padding:5px 12px; background:#F8FAFC; border-radius:8px; border:1px solid #E2E8F0;">'
                    '<div style="width:14px; height:14px; border-radius:4px; background:%s; flex-shrink:0;"></div>'
                    '<span style="font-size:12px; color:#0F172A; font-weight:600;">%s</span>'
                    '<span style="font-size:11px; color:#64748B;">(%s)</span></div>' % (c, d["nombre"], d["valor"])
                )
            return '<div style="display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin-top:14px; padding-top:14px; border-top:1px solid #E2E8F0;">%s</div>' % ''.join(items)

        if not df_asig.empty and st.session_state.filtro_maquina == "Todas" and len(df_asig["Ubicacion"].dropna().unique()) > 1:
            st.markdown("<div style='font-size:14px; font-weight:700; color:#0F172A; margin: 18px 0 10px 0;'>📊 Distribución de Actividades por Técnico Asignado</div>", unsafe_allow_html=True)

            # === TORTA: Agrupar por TÉCNICO ASIGNADO ===
            tecnicos_count = {}
            for _, row in df_asig.iterrows():
                t1 = limpiar(row.get("Tecnico_Asignado"), "")
                t2 = limpiar(row.get("Tecnico_Asignado_2"), "")
                if t1:
                    tecnicos_count[t1] = tecnicos_count.get(t1, 0) + 1
                if t2 and t2 != t1:
                    tecnicos_count[t2] = tecnicos_count.get(t2, 0) + 1

            # Agregar "Sin asignar" si hay actividades sin técnico
            sin_asignar = 0
            for _, row in df_asig.iterrows():
                t1 = limpiar(row.get("Tecnico_Asignado"), "")
                t2 = limpiar(row.get("Tecnico_Asignado_2"), "")
                if not t1 and not t2:
                    sin_asignar += 1
            if sin_asignar > 0:
                tecnicos_count["Sin asignar"] = sin_asignar

            tecnicos_sorted = sorted(tecnicos_count.items(), key=lambda x: x[1], reverse=True)
            if len(tecnicos_sorted) > 8:
                top = tecnicos_sorted[:7]
                otros_val = sum(v for _, v in tecnicos_sorted[7:])
                datos_torta = [{"nombre": abreviar_tecnico(k), "valor": v} for k, v in top]
                if otros_val > 0:
                    datos_torta.append({"nombre": "Otros", "valor": otros_val})
            else:
                datos_torta = [{"nombre": abreviar_tecnico(k), "valor": v} for k, v in tecnicos_sorted]

            # === LEYENDA: Agrupar por EQUIPO ===
            equipos_count = {}
            for _, row in df_asig.iterrows():
                eq = limpiar(row.get("Ubicacion"), "Sin equipo")
                equipos_count[eq] = equipos_count.get(eq, 0) + 1
            equipos_sorted = sorted(equipos_count.items(), key=lambda x: x[1], reverse=True)
            datos_leyenda = [{"nombre": k, "valor": v} for k, v in equipos_sorted[:10]]

            if datos_torta:
                svg_torta = _render_torta_3d_equipos(datos_torta)
                leyenda_html = _render_leyenda_tecnicos(datos_leyenda)
                st.markdown('<div style="background: white; border-radius: 16px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #E2E8F0;">' + svg_torta + leyenda_html + '</div>', unsafe_allow_html=True)
            else:
                st.info("📭 Sin datos para la gráfica.")

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        sel_key = gen_key("seleccion_asig")
        st.session_state.setdefault(sel_key, {})
        seleccion = st.session_state[sel_key]

        esp_filtro = st.session_state.filtro_especialidad
        if esp_filtro == "Todas" and "Especialidad" in df_asig.columns:
            esps_unicas = df_asig["Especialidad"].dropna().unique()
            if len(esps_unicas) == 1:
                esp_filtro = esps_unicas[0]
        lista_tecnicos = ["NO APLICA DEFINIR ACTIVIDAD", ""] + [t["nombre"] for t in obtener_tecnicos_con_carga(df, esp_filtro if esp_filtro else "Todas")]

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='background: linear-gradient(135deg, #F0F9FF, #E0F2FE); border: 1px solid #BAE6FD; border-radius: 10px; padding: 12px 16px; margin-bottom: 14px;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-weight:700; color:#0369a1; font-size:13px; margin-bottom:10px;'>✅ Asignación masiva por selección</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            tec1_masivo = st.selectbox("Técnico", lista_tecnicos, key=gen_key("masivo_tec1"), label_visibility="collapsed")
        with c2:
            if st.button("🚀 Asignar a seleccionadas", use_container_width=True, type="primary", key=gen_key("btn_masivo_asig")):
                guardados = 0
                tec1_masivo_valor = "" if tec1_masivo in ("NO APLICA DEFINIR ACTIVIDAD", "") else tec1_masivo
                for _, row in df_asig.iterrows():
                    internal_id = limpiar(row.get("ID"), "")
                    if not internal_id or not seleccion.get(internal_id, False):
                        continue
                    datos = {}
                    if tec1_masivo_valor != limpiar(row.get("Tecnico_Asignado"), ""):
                        datos["Tecnico_Asignado"] = tec1_masivo_valor
                    if datos:
                        if actualizar_campos_supabase(internal_id, datos, row.to_dict()):
                            idx_local, _ = get_row_by_internal_id(st.session_state.df_mantenimientos, internal_id)
                            if idx_local is not None:
                                _reflejar_en_session(idx_local, datos)
                            guardados += 1
                if guardados > 0:
                    st.success(f"✅ {guardados} actividades actualizadas")
                    st.session_state[sel_key] = {}
                    st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                    st.rerun()
                else:
                    st.warning("Selecciona actividades y un técnico primero")
        with c3:
            if st.button("🗑️ Limpiar", use_container_width=True, type="secondary", key=gen_key("btn_masivo_limpiar")):
                st.session_state[sel_key] = {}
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        if df_asig.empty:
            st.info("📭 No hay ordenes con los filtros seleccionados.")
            st.stop()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.success(f"✅ {len(df_asig)} actividades. Marca las que quieras y asigna arriba.")

        seen_ids = set()
        for _, row in df_asig.iterrows():
            estado = limpiar(row.get("Estado"), "Pendiente")
            tec_asig = limpiar(row.get("Tecnico_Asignado"), "")
            tec_asig2 = limpiar(row.get("Tecnico_Asignado_2"), "")
            nodo = limpiar(row.get("Nodo"), "")
            nodo_badge = f"<span class='nodo-badge-mini'>{nodo}</span>" if nodo else ""
            estado_cls = {"Ejecutado": "eq-estado-ej", "Verificado": "eq-estado-vf"}.get(estado, "eq-estado-pd")
            tecnicos_str = tec_asig
            if tec_asig2 and tec_asig2 != tec_asig:
                tecnicos_str = f"{tec_asig} + {tec_asig2}"
            if not tecnicos_str:
                tecnicos_str = "Sin asignar"

            internal_id = limpiar(row.get("ID"), "")
            chk_val = False
            if internal_id:
                chk_val = seleccion.get(internal_id, False)

            # Fila de actividad
            if internal_id in seen_ids:
                continue
            seen_ids.add(internal_id)
            col_chk, col_info = st.columns([0.04, 1], gap="small")
            with col_chk:
                if internal_id:
                    is_sel = st.checkbox("Sel", value=chk_val, key=gen_key("chk_sel", internal_id), label_visibility="collapsed")
                    seleccion[internal_id] = is_sel
            with col_info:
                st.markdown(f"""
                <div class="asig-rapida-fila {'asignada' if tec_asig or tec_asig2 else ''}" style="margin-bottom:2px;">
                    <div>
                        <div class="asig-ot"><strong>OT {escapar(limpiar(row.get("ID OT"), "SIN ID"))}</strong> {nodo_badge}</div>
                        <div style="font-size:11px;color:#64748B;">{escapar(limpiar(row.get("Procedimiento"), ""))}</div>
                        <div style="font-size:12px;color:#0F172A;margin-top:2px;">{escapar(limpiar(row.get("Actividades"), "Sin descripción"))}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="estado-badge {estado_cls}">{escapar(estado)}</span>
                        <div style="font-size:10px;color:#64748B;margin-top:4px;">{escapar(tecnicos_str)}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

def pantalla_sincronizar():
    header_tablet("🔄 Sincronizar desde Excel")
    boton_volver_inicio("sincronizar")

    st.markdown("""
    <div style="background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 12px; padding: 16px; margin: 12px 0;">
        <div style="font-size: 14px; font-weight: 700; color: #0369a1; margin-bottom: 6px;">📋 ¿Cómo funciona el ID Único?</div>
        <div style="font-size: 12px; color: #475569; line-height: 1.6;">
            La app genera automáticamente un <b>ID único</b> para cada actividad basado en:
            <code>id_ot + equipo + ubicacion + actividades + nodo</code>.<br><br>
            ✅ <b>Reemplazar Todo:</b> Borra todo e inserta el Excel (usa la primera vez).<br>
            🔄 <b>Actualizar/Insertar:</b> Solo cambia lo que cambió, mantiene técnicos y estados.
        </div>
    </div>""", unsafe_allow_html=True)

    # --- PASO 1: SUBIR ARCHIVO ---
    st.subheader("📁 Paso 1: Sube tu Excel")
    archivo = st.file_uploader("Arrastra tu archivo Excel aquí", type=["xlsx", "xls"], key="sync_upload_excel_v3")

    if archivo is None:
        st.info("⬆️ Sube un archivo Excel para comenzar")
        # Limpiar session si había uno anterior
        for k in ["sync_archivo_bytes", "sync_archivo_name", "sync_df_excel"]:
            st.session_state.pop(k, None)
        return

    # Guardar en session_state para que no se pierda al interactuar con otros widgets
    if "sync_archivo_bytes" not in st.session_state or st.session_state.get("sync_archivo_name") != archivo.name:
        st.session_state.sync_archivo_bytes = archivo.read()
        st.session_state.sync_archivo_name = archivo.name
        # Resetear df cacheado si cambia el archivo
        st.session_state.pop("sync_df_excel", None)

    archivo_bytes = io.BytesIO(st.session_state.sync_archivo_bytes)
    nombre_archivo = st.session_state.sync_archivo_name.lower()

    # --- PASO 2: CONFIGURAR SKIPROWS ---
    st.subheader("⚙️ Paso 2: Configurar encabezados")
    col_skip, col_info = st.columns([1, 3])
    with col_skip:
        skiprows_int = int(st.number_input(
            "Saltar filas antes del header", min_value=0, max_value=10,
            value=1, step=1, key="sync_skiprows_input_v2"))
    with col_info:
        st.caption("💡 Si tu Excel tiene título arriba del encabezado, pon 1. Si no, pon 0.")

    # --- FUNCIONES AUXILIARES (definidas con nombre_archivo ya conocido) ---
    def leer_excel(buf, skip):
        buf.seek(0)
        engine = "xlrd" if nombre_archivo.endswith(".xls") else "openpyxl"
        return pd.read_excel(buf, engine=engine, skiprows=skip)

    def detectar_header(buf, max_skip=5):
        posibles = ["un", "id ot", "tipo de ot", "descr", "procedimiento", "nodo", "equipo", "ubicacion", "especialidad", "actividades"]
        mejor_skip, mejor_puntaje = 0, -999
        for s in range(max_skip + 1):
            try:
                df_test = pd.read_excel(io.BytesIO(buf.getvalue()), engine="openpyxl", skiprows=s, nrows=3)
                cols_lower = [str(c).strip().lower() for c in df_test.columns]
                puntaje = sum(1 for h in posibles if any(h in c for c in cols_lower))
                puntaje -= sum(1 for c in cols_lower if "unnamed" in c) * 3
                if puntaje > mejor_puntaje:
                    mejor_puntaje, mejor_skip = puntaje, s
            except Exception:
                continue
        return mejor_skip

    # --- PASO 3: LEER Y VALIDAR ---
    st.subheader("📊 Paso 3: Vista previa")

    # Cachear df_excel en session_state para no releer al cambiar modo
    cache_key = f"sync_df_excel_{skiprows_int}_{nombre_archivo}"
    if st.session_state.get("sync_df_cache_key") != cache_key:
        st.session_state.pop("sync_df_excel", None)
        st.session_state.sync_df_cache_key = cache_key

    if "sync_df_excel" in st.session_state:
        df_excel = st.session_state.sync_df_excel
        st.success(f"📊 Excel en caché: **{len(df_excel)} filas** × **{len(df_excel.columns)} columnas**")
    else:
        try:
            df_excel = leer_excel(archivo_bytes, skiprows_int)
            cols_lower = [str(c).strip().lower() for c in df_excel.columns]
            headers_ok = any(h in cols_lower for h in ["un", "id ot", "tipo de ot", "descr", "equipo", "ubicacion", "actividades", "procedimiento"])

            if any("unnamed" in c for c in cols_lower) or not headers_ok:
                st.warning("⚠️ Los headers no se leyeron bien. Auto-detectando fila de encabezados...")
                auto_skip = detectar_header(archivo_bytes)
                if auto_skip != skiprows_int:
                    st.info(f"🔍 Header real detectado en fila {auto_skip + 1}. Releyendo...")
                    df_excel = leer_excel(archivo_bytes, auto_skip)
                    skiprows_int = auto_skip
                else:
                    st.error("❌ No se pudieron detectar los headers automáticamente. Revisa el archivo.")
                    return

            st.session_state.sync_df_excel = df_excel
            st.success(f"✅ Excel leído: **{len(df_excel)} filas** × **{len(df_excel.columns)} columnas** (saltadas {skiprows_int} filas)")
        except ImportError as e:
            if "xlrd" in str(e):
                st.error("❌ Falta la librería 'xlrd' para archivos .xls. Agrega `xlrd>=2.0.1` a requirements.txt.")
            else:
                st.error(f"❌ Error de importación: {e}")
            return
        except Exception as e:
            st.error(f"❌ Error leyendo Excel: {e}")
            return

    with st.expander("👁️ Ver primeras 10 filas", expanded=True):
        st.dataframe(df_excel.head(10), use_container_width=True)

    st.markdown(f"<div style='font-size:11px;color:#64748B;'>📋 Columnas detectadas: <code>{list(df_excel.columns)}</code></div>", unsafe_allow_html=True)

    # Validaciones
    cols_lower = [str(c).strip().lower() for c in df_excel.columns]
    if any("unnamed" in c for c in cols_lower):
        st.error("❌ Hay columnas 'Unnamed'. Aumenta 'Saltar filas antes del header'.")
        return
    elif not any(h in cols_lower for h in ["un", "id ot", "tipo de ot", "descr", "equipo", "ubicacion", "actividades"]):
        st.error("❌ No se detectaron columnas esperadas. Revisa el archivo.")
        return

    cols_norm = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df_excel.columns]
    esperadas = ["id_ot", "equipo", "ubicacion", "especialidad", "actividades", "procedimiento", "nodo", "prioridad_actividad"]
    faltantes = [c for c in esperadas if c not in cols_norm]
    if faltantes:
        st.warning(f"⚠️ Columnas no detectadas: **{', '.join(faltantes)}**")
    else:
        st.success("✅ Todas las columnas principales detectadas.")

    # Preview de IDs únicos
    st.subheader("🔑 IDs Únicos generados")
    st.caption("La app crea estos IDs automáticamente para cada fila.")
    df_preview = df_excel.head(5).copy()
    df_preview.columns = cols_norm
    if "equipo" in df_preview.columns and "actividades" in df_preview.columns:
        df_preview["id_unico_generado"] = df_preview.apply(
            lambda r: hashlib.md5("|".join(str(r.get(c, "")) for c in ["id_ot", "equipo", "ubicacion", "actividades", "nodo"]).encode()).hexdigest()[:20], axis=1)
        cols_show = [c for c in ["id_ot", "equipo", "actividades", "id_unico_generado"] if c in df_preview.columns]
        st.dataframe(df_preview[cols_show], use_container_width=True)

    # --- PASO 4: MODO Y SINCRONIZAR ---
    st.subheader("🚀 Paso 4: Sincronizar")
    modo = st.radio("Elige qué hacer:", [
        "🗑️ REEMPLAZAR TODO — Borra todo e inserta el Excel nuevo",
        "🔄 ACTUALIZAR/INSERTAR — Mantiene lo existente, actualiza por ID único"
    ], key="sync_modo_sync_v3")
    modo_valor = "reemplazar" if "REEMPLAZAR" in modo else "upsert"

    if modo_valor == "reemplazar":
        st.error("⚠️ **ATENCIÓN:** Esto borrará TODOS los datos actuales. ¡Usa con cuidado!")

    # Checkbox de confirmación para reemplazar
    confirmar = True
    if modo_valor == "reemplazar":
        confirmar = st.checkbox("✅ Sí, quiero borrar todo y reemplazar", key="sync_confirmar_borrar")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        btn_text = "🚀 REEMPLAZAR Y SINCRONIZAR" if modo_valor == "reemplazar" else "🚀 ACTUALIZAR Y SINCRONIZAR"
        if st.button(btn_text, use_container_width=True, type="primary", key="sync_btn_sync_v3", disabled=not confirmar):
            with st.spinner("Sincronizando, por favor espera..."):
                exito, mensaje = sincronizar_excel_a_supabase(df_excel, modo=modo_valor)
            if exito:
                st.success(mensaje)
                st.balloons()
                # Limpiar archivo de session_state
                for k in ["sync_archivo_bytes", "sync_archivo_name", "sync_df_excel", "sync_df_cache_key"]:
                    st.session_state.pop(k, None)
                st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
                st.info("🔄 Datos actualizados. Puedes volver al inicio.")
            else:
                st.error(mensaje)

# ==================== PROTECCIÓN DE RUTAS ADMIN ====================
# Si alguien intenta forzar una pagina de admin sin estar autenticado, lo sacamos
if st.session_state.perfil == "admin" and not st.session_state.get("admin_autenticado", False):
    st.session_state.pagina = "login"
    st.session_state.perfil = None
    st.session_state.mostrar_login_admin = False
elif st.session_state.perfil != "admin" and st.session_state.pagina in ["asignacion", "verificar"]:
    # Si un tecnico de alguna forma llega a asignacion o verificar, lo saco
    st.session_state.pagina = "login"
    st.session_state.perfil = None

# ==================== EJECUCIÓN PRINCIPAL ====================
PANTALLAS = {
    "login": pantalla_login,
    "home": pantalla_home,
    "ordenes": pantalla_ordenes,
    "mis_ordenes": pantalla_mis_ordenes,
    "ejecutar": pantalla_ejecutar,
    "detalle_tecnico": pantalla_detalle_tecnico,
    "detalle": pantalla_detalle,
    "asignacion": pantalla_asignacion,
    "verificar": pantalla_verificar,
    "sincronizar": pantalla_sincronizar,
}
pagina_actual = st.session_state.pagina
if pagina_actual in PANTALLAS:
    PANTALLAS[pagina_actual]()
else:
    st.session_state.pagina = "login"
    st.rerun()
