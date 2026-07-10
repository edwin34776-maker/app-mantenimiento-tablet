import streamlit as st
import pandas as pd
import os
from io import BytesIO

# ============ CONFIGURACION DE PAGINA ============
st.set_page_config(
    page_title="App Tablet Mtto Preventivo",
    page_icon="🔧",
    layout="wide"
)

# ============ CSS PERSONALIZADO ============
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        border-left: 4px solid #3b82f6;
    }
    .metric-number {
        font-size: 3rem;
        font-weight: bold;
        color: #2563eb;
    }
    .metric-label {
        color: #6b7280;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# ============ FUNCION PARA CARGAR EXCEL ============
@st.cache_data(ttl=300)
def cargar_excel_desde_archivo(ruta_archivo):
    """Carga un archivo Excel desde la ruta especificada."""
    try:
        if os.path.exists(ruta_archivo):
            df = pd.read_excel(ruta_archivo)
            return df, None
        else:
            return None, f"No se encontro el archivo: '{ruta_archivo}'"
    except Exception as e:
        return None, f"Error al leer '{ruta_archivo}': {str(e)}"

def cargar_excel_desde_upload(uploaded_file):
    """Carga un archivo Excel desde el file uploader de Streamlit."""
    try:
        df = pd.read_excel(BytesIO(uploaded_file.read()))
        return df, None
    except Exception as e:
        return None, f"Error al leer el archivo subido: {str(e)}"

# ============ HEADER ============
st.markdown('<div class="main-header"><h1>🔧 App Tablet Mtto Preventivo</h1></div>', unsafe_allow_html=True)

# ============ SIDEBAR - CARGA DE ARCHIVOS ============
with st.sidebar:
    st.header("📁 Gestion de Archivos")
    st.markdown("---")

    # Archivo de mantenimiento
    st.subheader("1. Ordenes de Mantenimiento")
    archivo_mtto = st.file_uploader(
        "Sube 'Formato de mantenimiento preventivo.xlsx'",
        type=["xlsx", "xls"],
        key="mtto_uploader"
    )

    # Archivo de tecnicos
    st.subheader("2. Base de Tecnicos")
    archivo_tecnicos = st.file_uploader(
        "Sube 'tecnico.xlsx'",
        type=["xlsx", "xls"],
        key="tecnico_uploader"
    )

    st.markdown("---")
    st.info("💡 **Tip:** Si los archivos estan en tu repo de GitHub, la app los cargara automaticamente.")

    # Mostrar estado de archivos en repo
    st.subheader("📊 Estado en Repositorio")
    col1, col2 = st.columns(2)
    with col1:
        if os.path.exists("Formato de mantenimiento preventivo.xlsx"):
            st.success("✅ Mtto")
        else:
            st.error("❌ Mtto")
    with col2:
        if os.path.exists("tecnico.xlsx"):
            st.success("✅ Tec")
        else:
            st.error("❌ Tec")

# ============ CARGA DE DATOS ============
df_mantenimiento = None
df_tecnicos = None
error_mtto = None
error_tec = None

# Intentar cargar mantenimiento (upload primero, luego repo)
if archivo_mtto is not None:
    df_mantenimiento, error_mtto = cargar_excel_desde_upload(archivo_mtto)
    if df_mantenimiento is not None:
        st.sidebar.success("✅ Ordenes cargadas desde upload")
else:
    df_mantenimiento, error_mtto = cargar_excel_desde_archivo("Formato de mantenimiento preventivo.xlsx")
    if df_mantenimiento is not None:
        st.sidebar.success("✅ Ordenes cargadas desde repo")

# Intentar cargar tecnicos (upload primero, luego repo)
if archivo_tecnicos is not None:
    df_tecnicos, error_tec = cargar_excel_desde_upload(archivo_tecnicos)
    if df_tecnicos is not None:
        st.sidebar.success("✅ Tecnicos cargados desde upload")
else:
    df_tecnicos, error_tec = cargar_excel_desde_archivo("tecnico.xlsx")
    if df_tecnicos is not None:
        st.sidebar.success("✅ Tecnicos cargados desde repo")

# ============ ALERTAS DE ERROR ============
if error_mtto:
    st.warning(f"⚠️ {error_mtto}")
    st.info("📤 Sube el archivo manualmente usando el panel lateral →")

if error_tec:
    st.warning(f"⚠️ {error_tec}")
    st.info("📤 Sube el archivo manualmente usando el panel lateral →")

# ============ CONTENIDO PRINCIPAL ============
if df_mantenimiento is not None and not df_mantenimiento.empty:

    # Metricas principales
    st.subheader("📊 Dashboard de Ordenes Preventivas")

    col1, col2, col3, col4 = st.columns(4)

    total_ordenes = len(df_mantenimiento)

    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-number">{total_ordenes}</div><div class="metric-label">Total Ordenes</div></div>', unsafe_allow_html=True)

    # Detectar columnas de estado si existen
    cols = df_mantenimiento.columns.tolist()

    # Intentar contar por estado
    estados = {}
    col_estado = None
    for c in cols:
        if 'estado' in c.lower() or 'status' in c.lower():
            col_estado = c
            break

    if col_estado:
        estados = df_mantenimiento[col_estado].value_counts().to_dict()

    with col2:
        activas = estados.get('Activo', estados.get('ACTIVO', estados.get('Activa', 0)))
        st.markdown(f'<div class="metric-card" style="border-left-color: #22c55e;"><div class="metric-number" style="color: #22c55e;">{activas}</div><div class="metric-label">Activas</div></div>', unsafe_allow_html=True)

    with col3:
        pendientes = estados.get('Pendiente', estados.get('PENDIENTE', 0))
        st.markdown(f'<div class="metric-card" style="border-left-color: #f59e0b;"><div class="metric-number" style="color: #f59e0b;">{pendientes}</div><div class="metric-label">Pendientes</div></div>', unsafe_allow_html=True)

    with col4:
        completadas = estados.get('Completado', estados.get('COMPLETADO', estados.get('Finalizado', 0)))
        st.markdown(f'<div class="metric-card" style="border-left-color: #8b5cf6;"><div class="metric-number" style="color: #8b5cf6;">{completadas}</div><div class="metric-label">Completadas</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ============ FILTROS ============
    st.subheader("🔍 Filtros y Busqueda")

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        # Filtro por tecnico si existe columna
        col_tecnico = None
        for c in cols:
            if 'tecnico' in c.lower():
                col_tecnico = c
                break

        if col_tecnico and df_tecnicos is not None:
            tecnicos_lista = ["Todos"] + sorted(df_tecnicos.iloc[:, 0].dropna().unique().tolist())
            tecnico_sel = st.selectbox("👤 Tecnico", tecnicos_lista)
        else:
            tecnico_sel = "Todos"

    with col_f2:
        # Filtro por area/equipo si existe
        col_area = None
        for c in cols:
            if 'area' in c.lower() or 'equipo' in c.lower() or 'maquina' in c.lower():
                col_area = c
                break

        if col_area:
            areas = ["Todas"] + sorted(df_mantenimiento[col_area].dropna().unique().tolist())
            area_sel = st.selectbox("🏭 Area/Equipo", areas)
        else:
            area_sel = "Todas"

    with col_f3:
        # Filtro por fecha si existe
        col_fecha = None
        for c in cols:
            if 'fecha' in c.lower():
                col_fecha = c
                break

        if col_fecha:
            fechas = ["Todas"] + sorted(df_mantenimiento[col_fecha].dropna().unique().tolist())
            fecha_sel = st.selectbox("📅 Fecha", fechas)
        else:
            fecha_sel = "Todas"

    # ============ APLICAR FILTROS ============
    df_filtrado = df_mantenimiento.copy()

    if tecnico_sel != "Todos" and col_tecnico:
        df_filtrado = df_filtrado[df_filtrado[col_tecnico] == tecnico_sel]

    if area_sel != "Todas" and col_area:
        df_filtrado = df_filtrado[df_filtrado[col_area] == area_sel]

    if fecha_sel != "Todas" and col_fecha:
        df_filtrado = df_filtrado[df_filtrado[col_fecha] == fecha_sel]

    st.markdown("---")

    # ============ TABLA DE ORDENES ============
    st.subheader(f"📋 Ordenes Preventivas ({len(df_filtrado)} resultados)")

    # Mostrar DataFrame con estilo
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        height=400,
        hide_index=True
    )

    # ============ ASIGNACION DE TECNICO ============
    if df_tecnicos is not None and not df_tecnicos.empty:
        st.markdown("---")
        st.subheader("👨‍🔧 Asignacion de Tecnicos")

        col_a1, col_a2 = st.columns([2, 1])

        with col_a1:
            # Seleccionar ordenes para asignar
            if len(df_filtrado) > 0:
                ordenes_ids = df_filtrado.iloc[:, 0].tolist()
                orden_sel = st.multiselect(
                    "Selecciona ordenes a asignar",
                    options=ordenes_ids,
                    default=[]
                )

        with col_a2:
            tecnicos_nombres = df_tecnicos.iloc[:, 0].dropna().unique().tolist()
            tecnico_asignar = st.selectbox("Asignar a tecnico", tecnicos_nombres)

            if st.button("✅ Confirmar Asignacion", type="primary", use_container_width=True):
                if orden_sel:
                    st.success(f"✅ {len(orden_sel)} ordenes asignadas a **{tecnico_asignar}**")
                    st.balloons()
                else:
                    st.warning("⚠️ Selecciona al menos una orden")

    # ============ EXPORTAR ============
    st.markdown("---")
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        if st.button("📥 Descargar Excel Filtrado", use_container_width=True):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name='Ordenes')

            st.download_button(
                label="⬇️ Click para descargar",
                data=output.getvalue(),
                file_name="ordenes_filtradas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    with col_exp2:
        if st.button("🔄 Recargar Datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

else:
    # ============ PANTALLA VACIA ============
    st.markdown("<br><br>", unsafe_allow_html=True)

    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; background: #f8fafc; border-radius: 16px;">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📂</div>
            <h3 style="color: #64748b;">Sin datos cargados</h3>
            <p style="color: #94a3b8;">
                Sube los archivos Excel desde el panel lateral<br>
                o asegurate de que esten en tu repositorio de GitHub.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Mostrar estructura esperada
        with st.expander("📋 Estructura esperada de archivos"):
            st.code("""
📁 app-mantenimiento-tablet/
├── 📄 app.py
├── 📊 Formato de mantenimiento preventivo.xlsx
├── 📊 tecnico.xlsx
└── 📄 requirements.txt
            """, language="text")

            st.markdown("**requirements.txt:**")
            st.code("""streamlit
pandas
openpyxl
            """, language="text")

# ============ FOOTER ============
st.markdown("---")
st.caption("🔧 App Tablet Mtto Preventivo | Desarrollado con Streamlit")
