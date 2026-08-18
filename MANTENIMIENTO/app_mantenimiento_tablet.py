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

# =========================
# CONFIGURACIÓN
# =========================
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

# =========================
# UTILIDADES
# =========================
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

def limpiar_valor_excel(valor):
    if pd.isna(valor):
        return None
    if isinstance(valor, str) and valor.strip() == "":
        return None
    return valor

def mapear_campo_supabase(campo):
    mapeo = {
        "ID": "id",
        "ID OT": "id_ot",
        "Actividades": "actividades",
        "Procedimiento": "procedimiento",
        "Tecnico_Asignado": "tecnico_asignado",
        "Prioridad_Actividad": "prioridad_actividad",
        "Actividades_Hechas": "actividades_hechas",
        "Fecha_Ejecucion": "fecha_ejecucion",
        "Hora_Inicio": "hora_inicio",
        "Hora_Fin": "hora_fin",
        "Estado": "estado",
        "Comentarios": "comentarios",
        "Equipo": "equipo",
        "Ubicacion": "ubicacion",
        "Especialidad": "especialidad",
        "Nodo": "nodo"
    }
    if campo in mapeo:
        return mapeo[campo]
    return campo.lower().replace(" ", "_").replace(".", "").replace("-", "_").replace("__", "_")

# =========================
# CORREO
# =========================
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
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Preventivas")
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
    msg["From"] = email_user
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo_html, "html"))

    attachment = MIMEBase("application", "octet-stream")
    attachment.set_payload(output.read())
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", f'attachment; filename="{area_mecanica}.xlsx"')
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

# =========================
# SUPABASE
# =========================
def cargar_ordenes_supabase():
    try:
        response = supabase.table("ordenes_trabajo").select("*").order("id", desc=False).execute()
        data = response.data
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        columnas_mapeo = {}
        for col in df.columns:
            if col == "id":
                columnas_mapeo[col] = "ID"
            elif col == "id_ot":
                columnas_mapeo[col] = "ID OT"
            elif col == "actividades":
                columnas_mapeo[col] = "Actividades"
            elif col == "procedimiento":
                columnas_mapeo[col] = "Procedimiento"
            elif col == "tecnico_asignado":
                columnas_mapeo[col] = "Tecnico_Asignado"
            elif col == "prioridad_actividad":
                columnas_mapeo[col] = "Prioridad_Actividad"
            elif col == "actividades_hechas":
                columnas_mapeo[col] = "Actividades_Hechas"
            elif col == "fecha_ejecucion":
                columnas_mapeo[col] = "Fecha_Ejecucion"
            elif col == "hora_inicio":
                columnas_mapeo[col] = "Hora_Inicio"
            elif col == "hora_fin":
                columnas_mapeo[col] = "Hora_Fin"
            else:
                columnas_mapeo[col] = col.capitalize()

        df = df.rename(columns=columnas_mapeo)

        columnas_default = {
            "Estado": "Pendiente",
            "Comentarios": "",
            "Tecnico_Asignado": "",
            "Actividades_Hechas": "",
            "Fecha_Ejecucion": "",
            "Hora_Inicio": "",
            "Hora_Fin": "",
            "Prioridad_Actividad": "",
            "ID OT": "",
            "Procedimiento": ""
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
        columnas_editables = [
            "Tecnico_Asignado",
            "Estado",
            "Prioridad_Actividad",
            "Comentarios",
            "Fecha_Ejecucion",
            "Hora_Inicio",
            "Hora_Fin"
        ]

        exitosos = 0

        for idx, row in df.iterrows():
            id_interno = row.get("ID")
            if pd.isna(id_interno):
                continue

            datos = {}
            for col in columnas_editables:
                if col in row.index:
                    datos[col] = limpiar_valor_excel(row[col])

            if datos:
                if guardar_orden_supabase(id_interno, datos):
                    exitosos += 1

        st.success(f"{exitosos} órdenes actualizadas en Supabase")
        return exitosos > 0

    except Exception as e:
        st.error(f"Error guardando asignaciones: {e}")
        return False

# =========================
# EXCEL -> SUPABASE
# =========================
def excel_a_supabase(archivo_excel, llave="id_ot"):
    try:
        df_excel = pd.read_excel(archivo_excel)
        df_excel.columns = [str(c).strip() for c in df_excel.columns]

        if llave not in df_excel.columns:
            return False, f"El Excel debe contener la columna '{llave}'"

        actualizadas = 0
        errores = []

        for _, row in df_excel.iterrows():
            valor_llave = row.get(llave)

            if pd.isna(valor_llave) or str(valor_llave).strip() == "":
                errores.append("Fila sin llave válida")
                continue

            datos = {}
            for col in df_excel.columns:
                if col == llave:
                    continue

                valor = limpiar_valor_excel(row[col])
                datos[mapear_campo_supabase(col)] = valor

            try:
                supabase.table("ordenes_trabajo").update(datos).eq(llave, valor_llave).execute()
                actualizadas += 1
            except Exception as e:
                errores.append(f"{valor_llave}: {str(e)}")

        if errores:
            return True, f"Actualizadas: {actualizadas}. Errores: {len(errores)}"
        return True, f"Actualizadas: {actualizadas} filas correctamente"

    except Exception as e:
        return False, f"Error leyendo Excel: {str(e)}"

def excel_a_supabase_upsert(archivo_excel):
    try:
        df_excel = pd.read_excel(archivo_excel)
        df_excel.columns = [str(c).strip() for c in df_excel.columns]

        registros = []
        for _, row in df_excel.iterrows():
            item = {}
            for col in df_excel.columns:
                item[mapear_campo_supabase(col)] = limpiar_valor_excel(row[col])
            registros.append(item)

        supabase.table("ordenes_trabajo").upsert(registros).execute()
        return True, f"Subidas/actualizadas {len(registros)} filas"
    except Exception as e:
        return False, f"Error: {str(e)}"

# =========================
# UI
# =========================
st.set_page_config(
    page_title="App Tablet Mtto Preventivo",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
    .home-screen { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; min-height: auto; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="tablet-header">App Tablet Mtto Preventivo</div>', unsafe_allow_html=True)

# =========================
# SECCIÓN: ACTUALIZAR DESDE EXCEL
# =========================
st.subheader("Actualizar base de datos desde Excel")

archivo_excel = st.file_uploader("Sube tu archivo Excel", type=["xlsx"])

col1, col2 = st.columns(2)

with col1:
    llave_excel = st.selectbox("Columna llave para actualizar", ["id_ot", "id"], index=0)

with col2:
    modo_guardado = st.selectbox("Modo de guardado", ["Actualizar", "Upsert"], index=0)

if archivo_excel is not None:
    try:
        df_preview = pd.read_excel(archivo_excel)
        df_preview.columns = [str(c).strip() for c in df_preview.columns]

        st.write("Vista previa del archivo:")
        st.dataframe(df_preview, use_container_width=True)

        if st.button("Procesar Excel"):
            if modo_guardado == "Actualizar":
                ok, msg = excel_a_supabase(archivo_excel, llave=llave_excel)
            else:
                ok, msg = excel_a_supabase_upsert(archivo_excel)

            if ok:
                st.success(msg)
            else:
                st.error(msg)

    except Exception as e:
        st.error(f"Error al leer el Excel: {e}")
