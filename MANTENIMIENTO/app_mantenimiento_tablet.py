import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la página - MODO TABLET
st.set_page_config(
    page_title="App Tablet Mtto Preventivo",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== ESTILOS CSS - DISEÑO TABLET ====================
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f5;
    }

    .tablet-header {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 12px 20px;
        border-radius: 0 0 16px 16px;
        text-align: center;
        font-size: 20px;
        font-weight: 700;
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 4px 15px rgba(26,35,158,0.3);
        position: sticky;
        top: 0;
        z-index: 100;
    }

    .home-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
        padding: 20px;
    }

    .big-counter {
        font-size: 80px;
        font-weight: 900;
        color: #1a237e;
        line-height: 1;
        margin: 20px 0;
    }

    .counter-label {
        font-size: 18px;
        color: #666;
        margin-bottom: 30px;
    }

    .filter-chip {
        background: white;
        border: 2px solid #1a237e;
        color: #1a237e;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }

    .filter-chip:hover, .filter-chip.active {
        background: #1a237e;
        color: white;
    }

    .orders-table {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }

    .table-header {
        background: #1a237e;
        color: white;
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 600;
        display: grid;
        grid-template-columns: 80px 60px 1fr 100px 100px;
        gap: 8px;
        align-items: center;
    }

    .table-row {
        padding: 12px 16px;
        border-bottom: 1px solid #eee;
        display: grid;
        grid-template-columns: 80px 60px 1fr 100px 100px;
        gap: 8px;
        align-items: center;
        cursor: pointer;
        transition: all 0.2s;
    }

    .table-row:hover {
        background: #e8eaf6;
    }

    .estado-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        text-align: center;
    }

    .estado-ejecutado { background-color: #d4edda; color: #155724; }
    .estado-pendiente { background-color: #fff3cd; color: #856404; }
    .estado-verificado { background-color: #cce5ff; color: #004085; }
    .estado-cerrada { background-color: #d1ecf1; color: #0c5460; }

    .progress-bar-container {
        display: flex;
        gap: 15px;
        justify-content: center;
        margin: 20px 0;
        padding: 15px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .progress-item {
        text-align: center;
    }

    .progress-value {
        font-size: 24px;
        font-weight: 800;
    }

    .progress-label {
        font-size: 12px;
        color: #666;
    }

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

    .equipo-info strong {
        color: #1a237e;
    }

    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* ==================== PRIORIDAD DE ACTIVIDADES - COLORES ==================== */
    .prioridad-critico {
        border-left: 5px solid #dc3545 !important;
        background: linear-gradient(90deg, #fff5f5 0%, #ffffff 100%) !important;
    }
    .prioridad-secundario {
        border-left: 5px solid #ffc107 !important;
        background: linear-gradient(90deg, #fffbea 0%, #ffffff 100%) !important;
    }
    .prioridad-estandar {
        border-left: 5px solid #28a745 !important;
        background: linear-gradient(90deg, #f0fff4 0%, #ffffff 100%) !important;
    }

    .leyenda-prioridad {
        display: flex;
        gap: 20px;
        justify-content: center;
        margin: 15px 0;
        padding: 12px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        flex-wrap: wrap;
    }

    .leyenda-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
    }

    .leyenda-dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
    }

    .actividad-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.2s;
    }

    .actividad-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        transform: translateY(-1px);
    }

    .actividad-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .actividad-titulo {
        font-size: 15px;
        font-weight: 700;
        color: #1f2937;
        flex: 1;
    }

    .actividad-prioridad-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .badge-critico {
        background: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
    }

    .badge-secundario {
        background: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }

    .badge-estandar {
        background: #d1fae5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }

    .actividad-descripcion {
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 12px;
        line-height: 1.5;
    }

    .actividad-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 10px;
        border-top: 1px solid #f3f4f6;
    }

    .actividad-meta {
        display: flex;
        gap: 12px;
        font-size: 12px;
        color: #9ca3af;
    }

    @media (max-width: 768px) {
        .actividad-header { flex-direction: column; align-items: flex-start; gap: 8px; }
        .leyenda-prioridad { gap: 10px; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== BASE DE DATOS DE TÉCNICOS ====================

TECNICOS_ELE = [
    "RIVERA SANTOS LUIS ALVARO",
    "NESTOR LEONARDO CORTES TORRES",
    "JAVIER FELIPE ROZO CALDERON",
    "JHON FREDY BERNAL AVILA",
    "YUPER YAIL CASTILLO",
    "ERIK SANTIAGO MARTINEZ HERRERA",
    "QUECANO ANGARITA CARLOS",
    "PULIDO RIOS JAHIR",
    "GARCIA CASAS JEFFERSSON DAVID",
    "CASTAÑEDA ORTIZ EDISON ORACIO",
    "DIAZ SEGURA DANIEL STEVEN",
    "FRANCO SIERRA JOSE ALEJANDRO",
    "MOJICA GARCES JEAN CARLOS",
    "CAROLOINA RINCON",
    "PINILLA ARIAS JHONATAN FERNANDO",
    "JUAN DAVID CHACON VELANDIA"
]

TECNICOS_MEC = [
    "WILSON ABDON QUEVEDO PASTOR",
    "LUIS FERNANDO DELGADO CARMONA",
    "SAENZ SAENZ CARLOS EFREN",
    "PABLO ENRRIQUE TORRES BARON",
    "FELIPE LATORRE DIAZ",
    "MOLINA GONZALEZ MICHAEL ANDRES",
    "MURILLO MURILLO WILLIAM OBER",
    "MOLANO ALFONSO LUIS",
    "MARTINEZ TORRES FREDY ALEXANDER",
    "VARGAS VARGAS JHON ALEJANDER",
    "MERIÑO GIL JOSE MANUEL",
    "DILAN MEDINA",
    "RODRIGUEZ CAMACHO LUIS ALVEIRO",
    "MENDIVIELSO CANTOR JUAN CARLOS",
    "ARIAS  PERDOMO JUAN ESTEBAN",
    "VELASQUEZ OSPINA CRISTIAN JAIR"
]

# ==================== FUNCIONES AUXILIARES ====================

@st.cache_data
def cargar_excel_mantenimiento():
    try:
        df = pd.read_excel("Formato de mantenimiento preventivo.xlsx", sheet_name="Inicial")
        df = df[df['UN'] != 'UN'].reset_index(drop=True)
        if 'Estado' not in df.columns:
            df['Estado'] = 'Pendiente'
        if 'Comentarios' not in df.columns:
            df['Comentarios'] = ''
        if 'Tecnico_Asignado' not in df.columns:
            df['Tecnico_Asignado'] = ''
        if 'Actividades_Hechas' not in df.columns:
            df['Actividades_Hechas'] = ''
        if 'Fecha_Ejecucion' not in df.columns:
            df['Fecha_Ejecucion'] = ''
        if 'Hora_Inicio' not in df.columns:
            df['Hora_Inicio'] = ''
        if 'Hora_Fin' not in df.columns:
            df['Hora_Fin'] = ''
        if 'Prioridad_Actividad' not in df.columns:
            df['Prioridad_Actividad'] = ''
        return df
    except Exception as e:
        st.error(f"⚠️ No se encontró el archivo de mantenimiento. Error: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_excel_tecnicos():
    try:
        df = pd.read_excel("tecnico.xlsx", sheet_name="query")
        df = df[df['ACTIVIDAD'] != 'ACTIVIDAD'].reset_index(drop=True)
        df['TECNICOS'] = df['TECNICOS'].str.strip()
        df['ESPE'] = df['ESPE'].str.strip()
        return df
    except Exception as e:
        st.error(f"⚠️ No se encontró el archivo de técnicos. Error: {e}")
        return pd.DataFrame()

def obtener_tecnicos_por_nodo(nodo, especialidad):
    df_tec = st.session_state.df_tecnicos
    if df_tec.empty:
        return []
    tecnicos = df_tec[
        (df_tec['ACTIVIDAD'] == nodo) & 
        (df_tec['ESPE'] == especialidad) &
        (df_tec['TECNICOS'].notna()) &
        (df_tec['TECNICOS'] != '')
    ]['TECNICOS'].unique().tolist()
    return tecnicos

def obtener_tecnicos_por_especialidad(especialidad):
    if especialidad == 'ELE':
        return TECNICOS_ELE
    elif especialidad == 'MEC':
        return TECNICOS_MEC
    return TECNICOS_ELE + TECNICOS_MEC

def limpiar_nombre_equipo(nombre):
    nombre = str(nombre).strip().upper()
    prefijos = ['MOTOR ', 'REDUCTOR ', 'MOTOREDUCTOR ', 'SERVOMOTOR ', 'CAJA DE ', 
                'TABLERO ', 'BORNEA ', 'AIRE ACONDICIONADO ', 'AIRE ACOND  ', 
                'SISTEMA DE ', 'ESTACION DE ', 'SISTEMA ']
    for prefijo in prefijos:
        if nombre.startswith(prefijo):
            return nombre.replace(prefijo, "")
    return nombre

def calcular_progreso(df):
    total = len(df)
    if total == 0:
        return 0, 0, 0
    ejecutado = len(df[df['Estado'] == 'Ejecutado'])
    verificado = len(df[df['Estado'] == 'Verificado'])
    cerrada = len(df[df['Estado'] == 'Cerrada'])
    pct_ejec = round((ejecutado / total) * 100, 1)
    pct_verif = round((verificado / total) * 100, 1)
    pct_pdte = round(100 - pct_ejec - pct_verif, 1)
    return pct_ejec, pct_pdte, pct_verif

def obtener_estado_visual(estado):
    estados = {
        'Ejecutado': 'estado-ejecutado',
        'Verificado': 'estado-verificado',
        'Cerrada': 'estado-cerrada',
        'Pendiente': 'estado-pendiente'
    }
    return estados.get(estado, 'estado-pendiente')

def obtener_color_prioridad(prioridad):
    colores = {
        'Rojo': {'label': '🔴 CRÍTICO', 'desc': 'Sí o sí se debe realizar'},
        'Amarillo': {'label': '🟡 SECUNDARIO', 'desc': 'Realizar después de las obligatorias'},
        'Verde': {'label': '🟢 ESTÁNDAR', 'desc': 'Actividad simple, poco requisito'},
        '': {'label': '⚪ SIN CLASIFICAR', 'desc': 'No definida'}
    }
    return colores.get(prioridad, colores[''])

def obtener_clase_css_prioridad(prioridad):
    clases = {
        'Rojo': 'prioridad-critico',
        'Amarillo': 'prioridad-secundario',
        'Verde': 'prioridad-estandar',
        '': ''
    }
    return clases.get(prioridad, '')

def boton_volver_inicio(key_suffix=""):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🏠 VOLVER AL INICIO", use_container_width=True, type="secondary", key=f"volver_inicio_{key_suffix}"):
            st.session_state.pagina = 'home'
            st.session_state.orden_seleccionada = None
            st.session_state.busqueda = ''
            st.rerun()

# ==================== INICIALIZAR ESTADO ====================

if 'pagina' not in st.session_state:
    st.session_state.pagina = 'home'
if 'orden_seleccionada' not in st.session_state:
    st.session_state.orden_seleccionada = None
if 'df_mantenimientos' not in st.session_state:
    st.session_state.df_mantenimientos = cargar_excel_mantenimiento()
if 'df_tecnicos' not in st.session_state:
    st.session_state.df_tecnicos = cargar_excel_tecnicos()
if 'filtro_especialidad' not in st.session_state:
    st.session_state.filtro_especialidad = 'Todas'
if 'filtro_maquina' not in st.session_state:
    st.session_state.filtro_maquina = 'Todas'
if 'filtro_esp_asig' not in st.session_state:
    st.session_state.filtro_esp_asig = 'Todas'
if 'filtro_maq_asig' not in st.session_state:
    st.session_state.filtro_maq_asig = 'Todas'
if 'filtro_estado_asig' not in st.session_state:
    st.session_state.filtro_estado_asig = 'Todos'
if 'busqueda' not in st.session_state:
    st.session_state.busqueda = ''
if 'actividades_check' not in st.session_state:
    st.session_state.actividades_check = {}
if 'prioridades_actividades' not in st.session_state:
    st.session_state.prioridades_actividades = {}

# ==================== PANTALLA DE INICIO (HOME) ====================

def pantalla_home():
    df = st.session_state.df_mantenimientos
    st.markdown('<div class="tablet-header">🔧 App Tablet Mtto Preventivo</div>', unsafe_allow_html=True)
    total_ordenes = len(df)
    st.markdown(f"""
    <div class="home-screen">
        <div class="counter-label">ÓRDENES PREVENTIVAS</div>
        <div class="big-counter">{total_ordenes}</div>
        <div class="counter-label">Total de órdenes activas</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; margin-bottom: 10px; font-weight: 600; color: #666;'>Filtrar por Especialidad</div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1,1,1,1])
    with col1:
        if st.button("🔵 TODAS", use_container_width=True, 
                    type="primary" if st.session_state.filtro_especialidad == 'Todas' else "secondary"):
            st.session_state.filtro_especialidad = 'Todas'
            st.rerun()
    with col2:
        if st.button("⚡ ELE", use_container_width=True,
                    type="primary" if st.session_state.filtro_especialidad == 'ELE' else "secondary"):
            st.session_state.filtro_especialidad = 'ELE'
            st.rerun()
    with col3:
        if st.button("🔧 MEC", use_container_width=True,
                    type="primary" if st.session_state.filtro_especialidad == 'MEC' else "secondary"):
            st.session_state.filtro_especialidad = 'MEC'
            st.rerun()
    with col4:
        if st.button("🔄 LIMPIAR", use_container_width=True):
            st.session_state.filtro_especialidad = 'Todas'
            st.session_state.busqueda = ''
            st.rerun()

    maquinas = ['Todas'] + sorted(df['Ubicación'].dropna().unique().tolist()) if not df.empty else ['Todas']
    maquina_sel = st.selectbox("🏭 Máquina / Ubicación", maquinas, 
                               index=maquinas.index(st.session_state.filtro_maquina) if st.session_state.filtro_maquina in maquinas else 0)
    st.session_state.filtro_maquina = maquina_sel

    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📋 VER ÓRDENES PREVENTIVAS", use_container_width=True, type="primary"):
            st.session_state.pagina = 'ordenes'
            st.rerun()
    with col_btn2:
        if st.button("📝 ASIGNACIÓN DE TÉCNICOS", use_container_width=True, type="primary"):
            st.session_state.pagina = 'asignacion'
            st.rerun()

    if not df.empty:
        st.divider()
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("⚡ ELE", len(df[df['Especialidad'] == 'ELE']))
        with col_b:
            st.metric("🔧 MEC", len(df[df['Especialidad'] == 'MEC']))
        with col_c:
            st.metric("✅ Cerradas", len(df[df['Estado'].isin(['Cerrada', 'Verificado'])]))

# ==================== PANTALLA DE ÓRDENES (LISTA) ====================

def pantalla_ordenes():
    df = st.session_state.df_mantenimientos
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>← Órdenes Preventivas</span>
        <span style="font-size: 14px; opacity: 0.8;">{st.session_state.filtro_especialidad}</span>
    </div>
    """, unsafe_allow_html=True)

    boton_volver_inicio("ordenes_top")

    busqueda = st.text_input("🔍 Buscar ID OT, equipo o descripción...", 
                            value=st.session_state.busqueda,
                            placeholder="Escribe para buscar...")
    st.session_state.busqueda = busqueda

    pct_ejec, pct_pdte, pct_verif = calcular_progreso(df)
    st.markdown(f"""
    <div class="progress-bar-container">
        <div class="progress-item"><div class="progress-value" style="color:#28a745">{pct_ejec}%</div><div class="progress-label">✅ Ejecutado</div></div>
        <div class="progress-item"><div class="progress-value" style="color:#dc3545">{pct_pdte}%</div><div class="progress-label">⏳ Pendiente</div></div>
        <div class="progress-item"><div class="progress-value" style="color:#007bff">{pct_verif}%</div><div class="progress-label">🔍 Verificado</div></div>
    </div>
    """, unsafe_allow_html=True)

    df_filtrado = df.copy()
    if st.session_state.filtro_especialidad != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Especialidad'] == st.session_state.filtro_especialidad]
    if st.session_state.filtro_maquina != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Ubicación'] == st.session_state.filtro_maquina]
    if busqueda:
        busqueda_lower = busqueda.lower()
        df_filtrado = df_filtrado[
            df_filtrado['Equipo'].str.lower().str.contains(busqueda_lower, na=False) |
            df_filtrado['Ubicación'].str.lower().str.contains(busqueda_lower, na=False) |
            df_filtrado['ID OT'].astype(str).str.contains(busqueda_lower, na=False) |
            df_filtrado['Descripción de procedimiento'].str.lower().str.contains(busqueda_lower, na=False)
        ]

    st.subheader(f"📋 Órdenes ({len(df_filtrado)})")
    for idx, row in df_filtrado.iterrows():
        id_ot = str(row.get('ID OT', ''))
        tipo = str(row.get('Especialidad', ''))
        descripcion = str(row.get('Descripción de procedimiento', ''))[:50] + "..." if len(str(row.get('Descripción de procedimiento', ''))) > 50 else str(row.get('Descripción de procedimiento', ''))
        estado = str(row.get('Estado', 'Pendiente'))
        tecnico = str(row.get('Tecnico_Asignado', ''))[:15] + "..." if len(str(row.get('Tecnico_Asignado', ''))) > 15 else str(row.get('Tecnico_Asignado', ''))
        if not tecnico: tecnico = "Sin asignar"
        estado_clase = obtener_estado_visual(estado)
        cols = st.columns([1, 1, 4, 1, 1])
        with cols[0]: st.write(f"**{id_ot}**")
        with cols[1]: st.write(f"🔹 {tipo}")
        with cols[2]: st.write(descripcion)
        with cols[3]: st.markdown(f'<span class="estado-badge {estado_clase}">{estado}</span>', unsafe_allow_html=True)
        with cols[4]: st.write(tecnico)
        if st.button(f"📋 Ver", key=f"btn_ver_{idx}"):
            st.session_state.orden_seleccionada = row.to_dict()
            st.session_state.orden_seleccionada['index'] = idx
            st.session_state.pagina = 'detalle'
            st.rerun()
        st.divider()

    boton_volver_inicio("ordenes_bottom")

# ==================== PANTALLA DE DETALLE DE ORDEN ====================

def pantalla_detalle():
    df = st.session_state.df_mantenimientos
    orden = st.session_state.orden_seleccionada
    if orden is None:
        st.session_state.pagina = 'ordenes'
        st.rerun()
        return
    idx = orden.get('index', 0)
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>← Orden {orden.get('ID OT', '')}</span>
        <span style="font-size: 14px; opacity: 0.8;">{orden.get('Especialidad', '')}</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("detalle_top")
    st.markdown("<div class='detail-panel'>", unsafe_allow_html=True)
    nombre_equipo = limpiar_nombre_equipo(orden.get('Equipo', ''))
    ubicacion = str(orden.get('Ubicación', ''))
    nodo = str(orden.get('Nodo', ''))
    especialidad = str(orden.get('Especialidad', ''))
    st.markdown(f"""
    <div class="equipo-info">
        <strong>🔧 {nombre_equipo}</strong><br>
        📍 {ubicacion} | 🏷️ {nodo} | ⚡ {especialidad}
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
            <div style="font-size: 12px; color: #666;">ID OT</div>
            <div style="font-size: 18px; font-weight: 700; color: #1a237e;">{orden.get('ID OT', '')}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        estado_actual = str(orden.get('Estado', 'Pendiente'))
        estado_clase = obtener_estado_visual(estado_actual)
        st.markdown(f"""<div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
            <div style="font-size: 12px; color: #666;">Estado</div>
            <span class="estado-badge {estado_clase}">{estado_actual}</span>
        </div>""", unsafe_allow_html=True)
    with col3:
        tecnico_actual = str(orden.get('Tecnico_Asignado', ''))
        if not tecnico_actual: tecnico_actual = "Sin asignar"
        st.markdown(f"""<div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
            <div style="font-size: 12px; color: #666;">Técnico</div>
            <div style="font-size: 14px; font-weight: 600;">{tecnico_actual}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.subheader("📝 Descripción")
    st.write(orden.get('Descripción de procedimiento', 'Sin descripción'))
    st.subheader("✅ Actividades a Realizar")
    df_actividades = df[(df['Equipo'] == orden.get('Equipo', '')) & (df['Ubicación'] == orden.get('Ubicación', '')) & (df['Nodo'] == nodo)].copy()
    actividades_hechas = str(orden.get('Actividades_Hechas', '')).split(',') if orden.get('Actividades_Hechas') else []
    actividades_hechas = [a.strip() for a in actividades_hechas if a.strip()]
    actividades_marcadas = []
    if len(df_actividades) > 0:
        for i, (_, act) in enumerate(df_actividades.iterrows()):
            act_desc = str(act.get('Actividades', act.get('Descripción de procedimiento', f'Actividad {i+1}')))
            act_key = f"act_{idx}_{i}"
            default_checked = act_key in st.session_state.actividades_check or act_desc in actividades_hechas
            checked = st.checkbox(f"📌 {act_desc}", value=default_checked, key=act_key)
            if checked:
                actividades_marcadas.append(act_desc)
                st.session_state.actividades_check[act_key] = True
            else:
                st.session_state.actividades_check[act_key] = False
    else:
        act_desc = str(orden.get('Descripción de procedimiento', 'Verificación general'))
        act_key = f"act_{idx}_main"
        default_checked = act_key in st.session_state.actividades_check or act_desc in actividades_hechas
        checked = st.checkbox(f"📌 {act_desc}", value=default_checked, key=act_key)
        if checked: actividades_marcadas.append(act_desc)

    st.divider()
    st.subheader("✏️ Actualizar Orden")
    with st.form("form_actualizar"):
        tecnicos_nodo = obtener_tecnicos_por_nodo(nodo, especialidad)
        tecnicos_opciones = tecnicos_nodo if tecnicos_nodo else obtener_tecnicos_por_especialidad(especialidad)
        tecnico_actual = str(orden.get('Tecnico_Asignado', ''))
        tecnico_index = 0
        if tecnico_actual and tecnico_actual in tecnicos_opciones:
            tecnico_index = tecnicos_opciones.index(tecnico_actual) + 1
        tecnico_sel = st.selectbox("👷 Asignar Técnico", ["-- Seleccionar --"] + tecnicos_opciones, index=tecnico_index)
        estados = ["Pendiente", "En Proceso", "Ejecutado", "Verificado", "Cerrada", "Cancelada"]
        estado_actual = str(orden.get('Estado', 'Pendiente'))
        estado_index = estados.index(estado_actual) if estado_actual in estados else 0
        nuevo_estado = st.selectbox("📊 Estado", estados, index=estado_index)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_ejec = st.date_input("📅 Fecha Ejecución", value=datetime.now())
        with col_f2:
            horas_trab = st.number_input("⏱️ Horas", min_value=0.0, max_value=24.0, value=0.0, step=0.5)
        comentarios_actuales = str(orden.get('Comentarios', ''))
        comentarios = st.text_area("💬 Comentarios / Observaciones", value=comentarios_actuales, placeholder="Escribe tus observaciones aquí...")
        submitted = st.form_submit_button("💾 GUARDAR", use_container_width=True)
        if submitted:
            if tecnico_sel == "-- Seleccionar --":
                st.error("⚠️ Por favor selecciona un técnico")
            else:
                mask = (df.index == idx)
                df.loc[mask, 'Estado'] = nuevo_estado
                df.loc[mask, 'Tecnico_Asignado'] = tecnico_sel
                df.loc[mask, 'Comentarios'] = comentarios
                df.loc[mask, 'Actividades_Hechas'] = ','.join(actividades_marcadas)
                df.loc[mask, 'Fecha_Ejecucion'] = fecha_ejec.strftime('%Y-%m-%d')
                df.loc[mask, 'Hora_Inicio'] = str(horas_trab)
                st.session_state.df_mantenimientos = df
                try:
                    with pd.ExcelWriter("Formato de mantenimiento preventivo.xlsx", engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df.to_excel(writer, sheet_name='Inicial_Actualizado', index=False)
                    st.success(f"✅ Guardado correctamente!")
                    st.balloons()
                except Exception as e:
                    st.warning(f"⚠️ Guardado en memoria. Error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    boton_volver_inicio("detalle_bottom")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅️ VOLVER A ÓRDENES", use_container_width=True):
        st.session_state.orden_seleccionada = None
        st.session_state.pagina = 'ordenes'
        st.rerun()

# ==================== PANTALLA DE ASIGNACIÓN CON PRIORIDADES ====================

def pantalla_asignacion():
    df = st.session_state.df_mantenimientos
    df_tec = st.session_state.df_tecnicos
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>📝 Asignación de Técnicos</span>
        <span style="font-size: 14px; opacity: 0.8;">Asignación</span>
    </div>
    """, unsafe_allow_html=True)
    boton_volver_inicio("asignacion_top")

    # LEYENDA DE PRIORIDADES
    st.markdown("""
    <div class="leyenda-prioridad">
        <div class="leyenda-item">
            <span class="leyenda-dot" style="background: #dc3545;"></span>
            <span>🔴 <strong>CRÍTICO</strong> — Sí o sí se debe realizar</span>
        </div>
        <div class="leyenda-item">
            <span class="leyenda-dot" style="background: #ffc107;"></span>
            <span>🟡 <strong>SECUNDARIO</strong> — Realizar después de las obligatorias</span>
        </div>
        <div class="leyenda-item">
            <span class="leyenda-dot" style="background: #28a745;"></span>
            <span>🟢 <strong>ESTÁNDAR</strong> — Actividad simple, poco requisito</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    datos_asignacion = [
        {"id": 1, "desc": "BANDAS TRANSPORTADORAS", "nodo": "BT01", "cant": 1, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Transporte", "procedimiento": "Lubricación de rodamientos, ajuste de tensión, inspección visual de bandas", "prioridad": "Rojo"},
        {"id": 2, "desc": "BRAZO PENDULO", "nodo": "BP01", "cant": 1, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Manipulación", "procedimiento": "Verificación de juntas, calibración de sensores de posición", "prioridad": "Amarillo"},
        {"id": 3, "desc": "CONVEYOR", "nodo": "CR01", "cant": 2, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Transporte", "procedimiento": "Alineación de bandas, revisión de motoresreductores, limpieza de guías", "prioridad": "Rojo"},
        {"id": 4, "desc": "DESEMBOBINADOR", "nodo": "DE01", "cant": 5, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Procesamiento", "procedimiento": "Calibración de frenos, ajuste de tensión del material, lubricación", "prioridad": "Rojo"},
        {"id": 5, "desc": "EMBOBINADOR DE SCRAP", "nodo": "EB01", "cant": 2, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Procesamiento", "procedimiento": "Revisión de cilindros hidráulicos, ajuste de presión, cambio de filtros", "prioridad": "Amarillo"},
        {"id": 6, "desc": "ESTACION DE APILADO", "nodo": "EA01", "cant": 4, "tecnico": "Sanchez Jair E.", "especialidad": "MEC", "maquina": "Almacenamiento", "procedimiento": "Verificación de sensores fotoeléctricos, ajuste de mesa elevadora", "prioridad": "Verde"},
        {"id": 7, "desc": "FORMADORA", "nodo": "FM01", "cant": 7, "tecnico": "Sanchez Jair E.", "especialidad": "MEC", "maquina": "Procesamiento", "procedimiento": "Cambio de matrices, calibración de presión, revisión de cilindros", "prioridad": "Rojo"},
        {"id": 8, "desc": "HORNO ELECTRICO", "nodo": "HE01", "cant": 3, "tecnico": "Ramirez Fabrianis", "especialidad": "ELE", "maquina": "Tratamiento", "procedimiento": "Verificación de resistencias, calibración de termocuplas, revisión de contactores", "prioridad": "Rojo"},
        {"id": 9, "desc": "MECANISMO RIELES", "nodo": "MR01", "cant": 6, "tecnico": "Valencia Carlos", "especialidad": "MEC", "maquina": "Transporte", "procedimiento": "Lubricación de carros, ajuste de rieles, revisión de finales de carrera", "prioridad": "Verde"},
        {"id": 10, "desc": "CORTADORA", "nodo": "CT01", "cant": 2, "tecnico": "", "especialidad": "MEC", "maquina": "Procesamiento", "procedimiento": "Afilado de cuchillas, ajuste de guías, revisión de sistema neumático", "prioridad": "Amarillo"},
        {"id": 11, "desc": "PUNZONADORA", "nodo": "PZ01", "cant": 3, "tecnico": "", "especialidad": "MEC", "maquina": "Procesamiento", "procedimiento": "Cambio de punzones, calibración de mesa, lubricación de guías", "prioridad": "Verde"},
        {"id": 12, "desc": "SISTEMA HIDRAULICO", "nodo": "SH01", "cant": 1, "tecnico": "", "especialidad": "MEC", "maquina": "Auxiliar", "procedimiento": "Cambio de aceite, revisión de válvulas, purga de sistema", "prioridad": "Rojo"},
        {"id": 13, "desc": "MOTOR PRINCIPAL", "nodo": "MP01", "cant": 2, "tecnico": "", "especialidad": "ELE", "maquina": "Procesamiento", "procedimiento": "Medición de resistencia de bobinado, verificación de aislamiento, ajuste de acoplamiento", "prioridad": "Rojo"},
        {"id": 14, "desc": "TABLERO CONTROL", "nodo": "TC01", "cant": 1, "tecnico": "", "especialidad": "ELE", "maquina": "Control", "procedimiento": "Verificación de conexiones, limpieza de bornes, prueba de relés y contactores", "prioridad": "Amarillo"},
        {"id": 15, "desc": "AIRE ACONDICIONADO", "nodo": "AA01", "cant": 2, "tecnico": "", "especialidad": "ELE", "maquina": "Climatización", "procedimiento": "Limpieza de filtros, revisión de refrigerante, verificación de compresor", "prioridad": "Verde"},
    ]

    df_asig = pd.DataFrame(datos_asignacion)

    st.markdown("<br>", unsafe_allow_html=True)
    col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 1])
    with col_f1:
        filtro_esp_asig = st.selectbox("⚡ Especialidad", ["Todas", "ELE", "MEC"],
            index=["Todas", "ELE", "MEC"].index(st.session_state.get('filtro_esp_asig', 'Todas')))
        st.session_state.filtro_esp_asig = filtro_esp_asig
    with col_f2:
        maquinas_asig = ["Todas"] + sorted(df_asig['maquina'].unique().tolist())
        filtro_maq_asig = st.selectbox("🏭 Máquina", maquinas_asig,
            index=maquinas_asig.index(st.session_state.get('filtro_maq_asig', 'Todas')) if st.session_state.get('filtro_maq_asig', 'Todas') in maquinas_asig else 0)
        st.session_state.filtro_maq_asig = filtro_maq_asig
    with col_f3:
        filtro_estado_asig = st.selectbox("📊 Estado Asignación", ["Todos", "Asignado", "Pendiente"],
            index=["Todos", "Asignado", "Pendiente"].index(st.session_state.get('filtro_estado_asig', 'Todos')))
        st.session_state.filtro_estado_asig = filtro_estado_asig
    with col_f4:
        filtro_prioridad_asig = st.selectbox("🎨 Prioridad", ["Todas", "Rojo", "Amarillo", "Verde"], index=0)

    total_asig = len(df_asig)
    asignadas = len(df_asig[df_asig['tecnico'] != ''])
    pendientes = total_asig - asignadas
    pct_asig = round((asignadas / total_asig) * 100, 1) if total_asig > 0 else 0
    pct_pend = round((pendientes / total_asig) * 100, 1) if total_asig > 0 else 0
    rojas = len(df_asig[df_asig['prioridad'] == 'Rojo'])
    amarillas = len(df_asig[df_asig['prioridad'] == 'Amarillo'])
    verdes = len(df_asig[df_asig['prioridad'] == 'Verde'])

    st.markdown(f"""
    <div style="display: flex; gap: 15px; justify-content: center; margin: 20px 0; padding: 15px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); flex-wrap: wrap;">
        <div style="text-align: center; min-width: 80px;">
            <div style="font-size: 24px; font-weight: 800; color: #28a745;">{pct_asig}%</div>
            <div style="font-size: 11px; color: #666;">✅ Asignadas ({asignadas})</div>
        </div>
        <div style="text-align: center; min-width: 80px;">
            <div style="font-size: 24px; font-weight: 800; color: #dc3545;">{pct_pend}%</div>
            <div style="font-size: 11px; color: #666;">⏳ Pendientes ({pendientes})</div>
        </div>
        <div style="width: 1px; background: #e5e7eb; margin: 0 5px;"></div>
        <div style="text-align: center; min-width: 60px;">
            <div style="font-size: 22px; font-weight: 800; color: #dc3545;">{rojas}</div>
            <div style="font-size: 11px; color: #666;">🔴 Rojas</div>
        </div>
        <div style="text-align: center; min-width: 60px;">
            <div style="font-size: 22px; font-weight: 800; color: #ffc107;">{amarillas}</div>
            <div style="font-size: 11px; color: #666;">🟡 Amarillas</div>
        </div>
        <div style="text-align: center; min-width: 60px;">
            <div style="font-size: 22px; font-weight: 800; color: #28a745;">{verdes}</div>
            <div style="font-size: 11px; color: #666;">🟢 Verdes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_filtrado_asig = df_asig.copy()
    if filtro_esp_asig != "Todas":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['especialidad'] == filtro_esp_asig]
    if filtro_maq_asig != "Todas":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['maquina'] == filtro_maq_asig]
    if filtro_estado_asig == "Asignado":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['tecnico'] != '']
    elif filtro_estado_asig == "Pendiente":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['tecnico'] == '']
    if filtro_prioridad_asig != "Todas":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['prioridad'] == filtro_prioridad_asig]

    st.subheader(f"📋 Actividades ({len(df_filtrado_asig)})")

    if filtro_esp_asig == "ELE":
        tecnicos_disponibles = TECNICOS_ELE
    elif filtro_esp_asig == "MEC":
        tecnicos_disponibles = TECNICOS_MEC
    else:
        tecnicos_disponibles = TECNICOS_ELE + TECNICOS_MEC

    for idx, row in df_filtrado_asig.iterrows():
        desc = row['desc']
        nodo = row['nodo']
        cant = row['cant']
        tecnico_actual = row['tecnico']
        especialidad = row['especialidad']
        prioridad = row['prioridad']
        procedimiento = row['procedimiento']
        # Determinar estado de asignación basado en el técnico actual
        is_asignado = tecnico_actual != '' and tecnico_actual != '-- Sin asignar --'

        prioridad_info = obtener_color_prioridad(prioridad)
        prioridad_clase = obtener_clase_css_prioridad(prioridad)
        badge_clase = f"badge-{prioridad.lower()}" if prioridad else ""
        badge_texto = prioridad_info['label']

        # Badge de estado de asignación
        if is_asignado:
            estado_asig_texto = "✅ Asignado"
            estado_asig_bg = "#d4edda"
            estado_asig_color = "#155724"
        else:
            estado_asig_texto = "⏳ Pendiente"
            estado_asig_bg = "#fff3cd"
            estado_asig_color = "#856404"

        st.markdown(f"""
        <div class="actividad-card {prioridad_clase}">
            <div class="actividad-header">
                <div class="actividad-titulo">🔧 {desc}</div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span class="actividad-prioridad-badge {badge_clase}">{badge_texto}</span>
                    <span style="display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; background: {estado_asig_bg}; color: {estado_asig_color};">{estado_asig_texto}</span>
                </div>
            </div>
            <div class="actividad-descripcion">{procedimiento}</div>
            <div class="actividad-footer">
                <div class="actividad-meta">
                    <span>🏷️ <strong>{nodo}</strong></span>
                    <span>📦 {cant} actividad{'es' if cant > 1 else ''}</span>
                    <span>⚡ {especialidad}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_t1, col_t2, col_t3 = st.columns([2, 2, 1])
        with col_t1:
            opciones_prioridad = ["Rojo", "Amarillo", "Verde"]
            prioridad_index = opciones_prioridad.index(prioridad) if prioridad in opciones_prioridad else 0
            nueva_prioridad = st.selectbox("🎨 Prioridad del procedimiento", opciones_prioridad,
                index=prioridad_index, key=f"prioridad_{row['id']}",
                help="🔴 CRÍTICO | 🟡 SECUNDARIO | 🟢 ESTÁNDAR")
        with col_t2:
            opciones_tec = ["-- Sin asignar --"] + tecnicos_disponibles
            tec_index = 0
            if tecnico_actual and tecnico_actual in tecnicos_disponibles:
                tec_index = tecnicos_disponibles.index(tecnico_actual) + 1
            nuevo_tecnico = st.selectbox("👷 Asignar técnico", opciones_tec,
                index=tec_index, key=f"tecnico_asig_{row['id']}")
        with col_t3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"💾", key=f"btn_guardar_asig_{row['id']}", help="Guardar asignación y prioridad"):
                if nuevo_tecnico != "-- Sin asignar --":
                    df_asig.loc[df_asig['id'] == row['id'], 'tecnico'] = nuevo_tecnico
                else:
                    df_asig.loc[df_asig['id'] == row['id'], 'tecnico'] = ''
                df_asig.loc[df_asig['id'] == row['id'], 'prioridad'] = nueva_prioridad
                st.success(f"✅ Guardado: {desc} - Prioridad: {nueva_prioridad}")
                st.rerun()

        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 GUARDAR TODAS LAS ASIGNACIONES", use_container_width=True, type="primary"):
        st.success("✅ Todas las asignaciones han sido guardadas")
        st.balloons()

    boton_volver_inicio("asignacion_bottom")

# ==================== NAVEGACIÓN ====================

if st.session_state.pagina == 'home':
    pantalla_home()
elif st.session_state.pagina == 'ordenes':
    pantalla_ordenes()
elif st.session_state.pagina == 'detalle':
    pantalla_detalle()
elif st.session_state.pagina == 'asignacion':
    pantalla_asignacion()
