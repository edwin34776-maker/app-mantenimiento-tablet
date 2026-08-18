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

# Configuración de Supabase
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

# Función para limpiar valores
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

# Función para enviar correos
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
            df.to_excel(writer, index=False, sheet_name="Reporte")
        
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = ", ".join(destinatarios)
        msg['Subject'] = asunto
        
        cuerpo_correo = (
            "<p>Hola,</p>"
            "<p>A continuación, se presenta el reporte de actividades:</p>"
            "<ul>"
            f"<li><strong>Ejecutadas:</strong> {ejecutadas_pct}%</li>"
            f"<li><strong>Pendientes:</strong> {pendientes_pct}%</li>"
            f"<li><strong>Verificadas:</strong> {verificar_pct}%</li>"
            "</ul>"
            "<p>Adjunto encontrarán el archivo con los detalles.</p>"
            "<p>Saludos,<br>Equipo de Mantenimiento</p>"
        )
        msg.attach(MIMEText(cuerpo_correo, 'html'))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(output.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="reporte_{area_mecanica}.xlsx"')
        msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_user, email_pass)
        server.sendmail(email_user, destinatarios, msg.as_string())
        server.quit()
        
        return True, "Correo enviado correctamente"
    except Exception as e:
        return False, f"Error al enviar el correo: {e}"


# Función para cargar datos desde Excel a Supabase
def cargar_excel_a_supabase(archivo_excel, nombre_tabla):
    try:
        df = pd.read_excel(archivo_excel)
        datos = df.to_dict('records')
        data, count = supabase.table(nombre_tabla).insert(datos).execute()
        return count, None
    except Exception as e:
        return None, f"Error al cargar los datos: {e}"


# Interfaz principal de la aplicación
st.title("App Tablet Mtto")

# Sección de progreso
col1, col2 = st.columns(2)
with col1:
    st.markdown("### Progreso de Asignación")

with col2:
    st.markdown("### Progreso de Verificación")

# Barra de botones
st.markdown("---")
st.markdown("### Acciones")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("VER ÓRDENES", use_container_width=True):
        st.write("Mostrando órdenes...")

with col2:
    if st.button("ENVIAR REPORTE POR CORREO", use_container_width=True):
        st.write("Enviando reporte por correo...")

with col3:
    if st.button("ACTUALIZAR BASE DE DATOS", use_container_width=True):
        st.subheader("Cargar Datos desde Excel a SQL")
        archivo_excel = st.file_uploader("Sube el archivo Excel", type=["xlsx", "xls"])
        nombre_tabla = st.text_input("Nombre de la tabla en Supabase")
        
        if archivo_excel and nombre_tabla:
            if st.button("Cargar Datos"):
                cantidad_registros, error = cargar_excel_a_supabase(archivo_excel, nombre_tabla)
                if error:
                    st.error(error)
                else:
                    st.success(f"Se cargaron {cantidad_registros} registros en la tabla {nombre_tabla}.")

# Filtrar por especialidad
st.markdown("---")
st.markdown("### Filtrar por Especialidad")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("TODAS", use_container_width=True):
        st.write("Filtrando por todas las especialidades...")

with col2:
    if st.button("ELE", use_container_width=True):
        st.write("Filtrando por ELE...")

with col3:
    if st.button("MEC", use_container_width=True):
        st.write("Filtrando por MEC...")

# Botón para cerrar sesión
st.markdown("---")
if st.button("CERRAR SESIÓN", use_container_width=True):
    st.write("Cerrando sesión...")
