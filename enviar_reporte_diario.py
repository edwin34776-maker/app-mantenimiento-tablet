#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📧 Reporte Preventivo Diario Automático — 7:00 AM
=================================================
Envía por correo las actividades EJECUTADAS del día anterior
(lo que se hizo "hoy" llega mañana a las 7 AM), con Excel adjunto.

Se ejecuta con GitHub Actions (gratis) o con cualquier programador/cron.
No depende de que la app de Streamlit esté abierta.

Configuración por variables de entorno (secrets en GitHub):
  SUPABASE_URL, SUPABASE_KEY   -> conexión a la base de datos
  EMAIL_USER, EMAIL_PASS       -> correo Gmail remitente (contraseña de aplicación)
  DESTINATARIOS                -> correos separados por coma (opcional)
  AREA_MECANICA                -> filtro por Ubicacion/máquina (opcional, "Todas" = todo)
  REPORTE_DIA                  -> "ayer" (por defecto) o "hoy"
"""
import os
import io
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd
from supabase import create_client

# ==================== CONFIGURACIÓN ====================
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "")
DESTINATARIOS = [d.strip() for d in os.environ.get(
    "DESTINATARIOS",
    "mantobogota@gmail.com,supermantobogota@gmail.com,johann.avendano@darnel.com"
).split(",") if d.strip()]
AREA = os.environ.get("AREA_MECANICA", "Todas")          # filtro por máquina/ubicación
MODO_DIA = os.environ.get("REPORTE_DIA", "ayer")         # 'ayer' = lo de hoy, enviado mañana 7am

if not EMAIL_USER or not EMAIL_PASS:
    sys.exit("❌ EMAIL_USER / EMAIL_PASS no configurados")

# ==================== CARGAR DATOS DE SUPABASE ====================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
registros = []
offset = 0
while True:
    lote = (supabase.table("ordenes_trabajo")
            .select("*")
            .order("id", desc=False)
            .range(offset, offset + 999)
            .execute().data or [])
    registros.extend(lote)
    if len(lote) < 1000:
        break
    offset += 1000

if not registros:
    sys.exit("⚠️  La base de datos está vacía. No se envía correo.")

df = pd.DataFrame(registros)

# Mapeo columnas Supabase -> nombres de la app
renom = {"id_ot": "ID OT", "equipo": "Equipo", "actividades": "Actividades",
         "tecnico_asignado": "Tecnico_Asignado", "prioridad_actividad": "Prioridad_Actividad",
         "fecha_ejecucion": "Fecha_Ejecucion", "hora_inicio": "Hora_Inicio",
         "hora_fin": "Hora_Fin", "estado": "Estado", "comentarios": "Comentarios",
         "ubicacion": "Ubicacion", "especialidad": "Especialidad", "nodo": "Nodo",
         "procedimiento": "Procedimiento"}
df = df.rename(columns={k: v for k, v in renom.items() if k in df.columns})

# ==================== FILTRO: EJECUTADAS DEL DÍA DEL REPORTE ====================
hoy = datetime.now().date()
fecha_reporte = (hoy - timedelta(days=1)) if MODO_DIA == "ayer" else hoy

if "Fecha_Ejecucion" in df.columns:
    df["Fecha_Ejecucion"] = pd.to_datetime(df["Fecha_Ejecucion"], errors="coerce")
    df_dia = df[df["Fecha_Ejecucion"].dt.date == fecha_reporte]
else:
    df_dia = df.iloc[0:0]

# Filtrar por área/máquina si se configuró
if AREA != "Todas" and "Ubicacion" in df_dia.columns:
    df_dia = df_dia[df_dia["Ubicacion"] == AREA]

if df_dia.empty:
    print(f"⚠️  No hay ejecuciones registradas para el {fecha_reporte} ({AREA}). "
          "Se envía correo informativo con 0 actividades.")
    df_dia = df.iloc[0:0]  # para que el Excel salga con encabezados

ejecutadas = len(df_dia[df_dia["Estado"] == "Ejecutado"]) if "Estado" in df_dia.columns else 0
verificadas = len(df_dia[df_dia["Estado"] == "Verificado"]) if "Estado" in df_dia.columns else 0
total = len(df_dia)
pct = round((ejecutadas + verificadas) / total * 100, 1) if total else 0.0

print(f"📊 Reporte del {fecha_reporte} | Área: {AREA} | Actividades: {total} "
      f"(Ej: {ejecutadas}, Ve: {verificadas})")

# ==================== GENERAR EXCEL ====================
output = io.BytesIO()
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

cols_show = [c for c in ["ID OT", "Ubicacion", "Equipo", "Especialidad", "Actividades",
                         "Tecnico_Asignado", "Prioridad_Actividad", "Estado",
                         "Fecha_Ejecucion", "Hora_Inicio", "Hora_Fin", "Comentarios", "Nodo"]
             if c in df_dia.columns]
df_excel = df_dia[cols_show].copy() if cols_show else pd.DataFrame({"Sin datos": []})
df_excel.insert(0, "N°", range(1, len(df_excel) + 1)) if cols_show else None

azul, blanco, gris = "0B5A94", "FFFFFF", "F2F6FA"
borde = Side(style="thin", color="D9E2F3")

with pd.ExcelWriter(output, engine="openpyxl") as writer:
    pd.DataFrame().to_excel(writer, index=False, sheet_name="Resumen")
    df_excel.to_excel(writer, index=False, sheet_name="Ejecutadas")

output.seek(0)
wb = load_workbook(output)
ws_res, ws = wb["Resumen"], wb["Ejecutadas"]
ws_res.sheet_view.showGridLines = False
for col, w in {"A": 4, "B": 28, "C": 22, "D": 22, "E": 22}.items():
    ws_res.column_dimensions[col].width = w

ws_res.merge_cells("B2:E3")
c = ws_res["B2"]
c.value = f"🔧  Reporte Preventivo Diario\n{AREA} — {fecha_reporte.strftime('%d/%m/%Y')}"
c.fill = PatternFill("solid", fgColor=azul)
c.font = Font(color=blanco, bold=True, size=16)
c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

tarjetas = [("B5:C6", "Ejecutadas el día", total, "178A43"),
            ("D5:E6", "% Avance del día", f"{pct}%", "1677D2")]
for rango, titulo, valor, color in tarjetas:
    ws_res.merge_cells(rango)
    celda = ws_res[rango.split(":")[0]]
    celda.value = f"{titulo}\n{valor}"
    celda.fill = PatternFill("solid", fgColor=color)
    celda.font = Font(color=blanco, bold=True, size=13)
    celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

ws_res["B8"], ws_res["C8"] = "Enviado automáticamente", datetime.now().strftime("%d/%m/%Y %H:%M")
ws_res["B8"].font = Font(bold=True, color=azul)
ws_res["C8"].font = Font(color=azul)

ws.freeze_panes = "A2"
for cell in ws[1]:
    cell.fill = PatternFill("solid", fgColor=azul)
    cell.font = Font(color=blanco, bold=True, size=10)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = Border(bottom=borde)
ws.row_dimensions[1].height = 30
anchos = {"N°": 6, "ID OT": 13, "Ubicacion": 25, "Equipo": 28, "Especialidad": 14,
          "Actividades": 45, "Tecnico_Asignado": 28, "Prioridad_Actividad": 14,
          "Estado": 14, "Fecha_Ejecucion": 18, "Hora_Inicio": 12, "Hora_Fin": 12,
          "Comentarios": 45, "Nodo": 18}
for cell in ws[1]:
    if cell.value:
        ws.column_dimensions[get_column_letter(cell.column)].width = anchos.get(str(cell.value), 18)
for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
    for cell in row:
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    if "Fecha_Ejecucion" in [str(c.value) for c in ws[1]] and ws.cell(row, 9).value:
        ws.cell(row, 9).number_format = "dd/mm/yyyy"

wb.active = wb.sheetnames.index("Resumen")
output.seek(0)
wb.save(output)
output.seek(0)
print("📎 Excel generado")

# ==================== ENVIAR CORREO ====================
nombre_archivo = f"Reporte_Diario_{AREA.replace(' ', '_')}_{fecha_reporte.strftime('%Y%m%d')}.xlsx"
cuerpo = f"""<html><body style="font-family: Arial, sans-serif; color: #333;">
    <p style="font-size:16px; font-weight:bold;">🔧 Reporte Preventivo Diario — {AREA}</p>
    <p style="font-size:14px;">Actividades ejecutadas el <b>{fecha_reporte.strftime('%d/%m/%Y')}</b>:</p>
    <ul style="font-size:14px;">
        <li><b>Total del día:</b> {total}</li>
        <li><b>Ejecutadas:</b> {ejecutadas}</li>
        <li><b>Verificadas:</b> {verificadas}</li>
        <li><b>% avance del día:</b> {pct}%</li>
    </ul>
    <p style="font-size:12px; color:#888;">Enviado automáticamente a las 7:00 AM.</p>
</body></html>"""

msg = MIMEMultipart()
msg["From"] = EMAIL_USER
msg["To"] = ", ".join(DESTINATARIOS)
msg["Subject"] = f"📧 Reporte Diario {AREA} — Ejecuciones del {fecha_reporte.strftime('%d/%m/%Y')}"
msg.attach(MIMEText(cuerpo, "html"))
adj = MIMEBase("application", "octet-stream")
adj.set_payload(output.read())
encoders.encode_base64(adj)
adj.add_header("Content-Disposition", f'attachment; filename="{nombre_archivo}"')
msg.attach(adj)

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, DESTINATARIOS, msg.as_string())
    print(f"✅ Correo enviado a: {', '.join(DESTINATARIOS)}")
except Exception as e:
    sys.exit(f"❌ Error al enviar: {e}")
