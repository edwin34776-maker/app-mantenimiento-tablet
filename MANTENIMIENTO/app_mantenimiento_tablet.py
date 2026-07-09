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
    /* Reset y base */
    .stApp {
        background-color: #f0f2f5;
    }

    /* Barra superior azul tipo tablet */
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

    /* Pantalla de inicio - Contador grande */
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

    /* Filtros tipo tablet */
    .filter-row {
        display: flex;
        gap: 10px;
        justify-content: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
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

    /* Tabla de órdenes tipo tablet */
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

    .table-row.selected {
        background: #c5cae9;
        border-left: 4px solid #1a237e;
    }

    /* Estados */
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

    /* Indicadores de progreso */
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

    .progress-ejec { color: #28a745; }
    .progress-pdte { color: #dc3545; }
    .progress-verif { color: #007bff; }

    /* Detalle de orden */
    .detail-panel {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-top: 10px;
    }

    .detail-header {
        background: #1a237e;
        color: white;
        padding: 16px;
        border-radius: 12px 12px 0 0;
        margin: -20px -20px 20px -20px;
    }

    /* Checkboxes de actividades */
    .activity-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px;
        background: #f8f9fa;
        border-radius: 8px;
        margin-bottom: 8px;
        border: 1px solid #e9ecef;
    }

    .activity-checkbox {
        width: 24px;
        height: 24px;
        accent-color: #1a237e;
        margin-top: 2px;
    }

    .activity-text {
        flex: 1;
        font-size: 14px;
        line-height: 1.4;
    }

    .activity-text.completed {
        text-decoration: line-through;
        color: #888;
    }

    /* Botón flotante */
    .fab-button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: #1a237e;
        color: white;
        border: none;
        font-size: 28px;
        box-shadow: 0 4px 15px rgba(26,35,158,0.4);
        cursor: pointer;
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Botón GUARDAR */
    .btn-guardar {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 14px;
        border-radius: 12px;
        text-align: center;
        font-size: 16px;
        font-weight: 700;
        border: none;
        width: 100%;
        cursor: pointer;
        margin-top: 20px;
    }

    /* Campo de comentarios */
    .comment-box {
        width: 100%;
        min-height: 80px;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        font-size: 14px;
        resize: vertical;
        margin-top: 10px;
    }

    .comment-box:focus {
        border-color: #1a237e;
        outline: none;
    }

    /* Info del equipo en detalle */
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

    /* Botón back */
    .btn-back {
        background: transparent;
        color: white;
        border: 2px solid white;
        padding: 8px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    /* Ocultar elementos de Streamlit por defecto */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* Tabs personalizados */
    .custom-tabs {
        display: flex;
        gap: 0;
        background: white;
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .custom-tab {
        flex: 1;
        padding: 12px;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        border: none;
        background: white;
        color: #666;
        transition: all 0.2s;
    }

    .custom-tab.active {
        background: #1a237e;
        color: white;
    }

    .custom-tab:hover:not(.active) {
        background: #e8eaf6;
    }

    /* Search bar */
    .search-bar {
        width: 100%;
        padding: 12px 16px;
        border: 2px solid #e0e0e0;
        border-radius: 25px;
        font-size: 14px;
        margin-bottom: 16px;
        background: white;
    }

    .search-bar:focus {
        border-color: #1a237e;
        outline: none;
    }

    /* Técnico asignado badge */
    .tecnico-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #e3f2fd;
        color: #1565c0;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .table-header, .table-row {
            grid-template-columns: 60px 50px 1fr 80px 80px;
            font-size: 12px;
        }
        .big-counter { font-size: 60px; }
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
    """Carga el archivo Excel con los datos de mantenimiento"""
    try:
        df = pd.read_excel("MANTENIMIENTO/Formato de mantenimiento preventivo.xlsx", sheet_name="Inicial")
        df = df[df['UN'] != 'UN'].reset_index(drop=True)
        # Asegurar que tenemos las columnas necesarias
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
        return df
    except Exception as e:
        st.error(f"⚠️ No se encontró el archivo de mantenimiento. Error: {e}")
        return pd.DataFrame()

@st.cache_data
def cargar_excel_tecnicos():
    """Carga el archivo Excel con los técnicos por actividad"""
    try:
        df = pd.read_excel("MANTENIMIENTO/tecnico.xlsx", sheet_name="query")
        df = df[df['ACTIVIDAD'] != 'ACTIVIDAD'].reset_index(drop=True)
        df['TECNICOS'] = df['TECNICOS'].str.strip()
        df['ESPE'] = df['ESPE'].str.strip()
        return df
    except Exception as e:
        st.error(f"⚠️ No se encontró el archivo de técnicos. Error: {e}")
        return pd.DataFrame()

def obtener_tecnicos_por_nodo(nodo, especialidad):
    """Obtiene los técnicos disponibles para un nodo y especialidad"""
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
    """Obtiene todos los técnicos de una especialidad"""
    if especialidad == 'ELE':
        return TECNICOS_ELE
    elif especialidad == 'MEC':
        return TECNICOS_MEC
    return TECNICOS_ELE + TECNICOS_MEC

def limpiar_nombre_equipo(nombre):
    """Quita prefijos para mostrar solo el equipo base"""
    nombre = str(nombre).strip().upper()
    prefijos = ['MOTOR ', 'REDUCTOR ', 'MOTOREDUCTOR ', 'SERVOMOTOR ', 'CAJA DE ', 
                'TABLERO ', 'BORNEA ', 'AIRE ACONDICIONADO ', 'AIRE ACOND  ', 
                'SISTEMA DE ', 'ESTACION DE ', 'SISTEMA ']
    for prefijo in prefijos:
        if nombre.startswith(prefijo):
            return nombre.replace(prefijo, "")
    return nombre

def calcular_progreso(df):
    """Calcula los porcentajes de progreso"""
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
    """Devuelve la clase CSS para el estado"""
    estados = {
        'Ejecutado': 'estado-ejecutado',
        'Verificado': 'estado-verificado',
        'Cerrada': 'estado-cerrada',
        'Pendiente': 'estado-pendiente'
    }
    return estados.get(estado, 'estado-pendiente')

# ==================== BOTÓN VOLVER AL INICIO (REUTILIZABLE) ====================

def boton_volver_inicio(key_suffix=""):
    """Muestra un botón para volver a la pantalla de inicio desde cualquier pantalla"""
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

# ==================== PANTALLA DE INICIO (HOME) ====================

def pantalla_home():
    df = st.session_state.df_mantenimientos

    # Header tipo tablet
    st.markdown("""
    <div class="tablet-header">
        🔧 App Tablet Mtto Preventivo
    </div>
    """, unsafe_allow_html=True)

    # Contador grande de órdenes
    total_ordenes = len(df)

    st.markdown(f"""
    <div class="home-screen">
        <div class="counter-label">ÓRDENES PREVENTIVAS</div>
        <div class="big-counter">{total_ordenes}</div>
        <div class="counter-label">Total de órdenes activas</div>
    </div>
    """, unsafe_allow_html=True)

    # Filtros rápidos tipo chips
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

    # Filtro por máquina
    maquinas = ['Todas'] + sorted(df['Ubicación'].dropna().unique().tolist()) if not df.empty else ['Todas']
    maquina_sel = st.selectbox("🏭 Máquina / Ubicación", maquinas, 
                               index=maquinas.index(st.session_state.filtro_maquina) if st.session_state.filtro_maquina in maquinas else 0)
    st.session_state.filtro_maquina = maquina_sel

    # Botones principales
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

    # Resumen rápido
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

    # Header tipo tablet con botón back
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>← Órdenes Preventivas</span>
        <span style="font-size: 14px; opacity: 0.8;">{}</span>
    </div>
    """.format(st.session_state.filtro_especialidad), unsafe_allow_html=True)

    # ===== BOTÓN VOLVER AL INICIO =====
    boton_volver_inicio("ordenes_top")

    # Barra de búsqueda
    busqueda = st.text_input("🔍 Buscar ID OT, equipo o descripción...", 
                            value=st.session_state.busqueda,
                            placeholder="Escribe para buscar...")
    st.session_state.busqueda = busqueda

    # Indicadores de progreso
    pct_ejec, pct_pdte, pct_verif = calcular_progreso(df)

    st.markdown(f"""
    <div class="progress-bar-container">
        <div class="progress-item">
            <div class="progress-value progress-ejec">{pct_ejec}%</div>
            <div class="progress-label">✅ Ejecutado</div>
        </div>
        <div class="progress-item">
            <div class="progress-value progress-pdte">{pct_pdte}%</div>
            <div class="progress-label">⏳ Pendiente</div>
        </div>
        <div class="progress-item">
            <div class="progress-value progress-verif">{pct_verif}%</div>
            <div class="progress-label">🔍 Verificado</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Filtrar datos
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

    # Tabla de órdenes
    st.subheader(f"📋 Órdenes ({len(df_filtrado)})")

    # Header de tabla
    st.markdown("""
    <div class="orders-table">
        <div class="table-header">
            <div>ID OT</div>
            <div>Tipo</div>
            <div>Descripción</div>
            <div>Estado</div>
            <div>Técnico</div>
        </div>
    """, unsafe_allow_html=True)

    # Filas de la tabla
    for idx, row in df_filtrado.iterrows():
        id_ot = str(row.get('ID OT', ''))
        tipo = str(row.get('Especialidad', ''))
        descripcion = str(row.get('Descripción de procedimiento', ''))[:50] + "..." if len(str(row.get('Descripción de procedimiento', ''))) > 50 else str(row.get('Descripción de procedimiento', ''))
        estado = str(row.get('Estado', 'Pendiente'))
        tecnico = str(row.get('Tecnico_Asignado', ''))[:15] + "..." if len(str(row.get('Tecnico_Asignado', ''))) > 15 else str(row.get('Tecnico_Asignado', ''))
        if not tecnico:
            tecnico = "Sin asignar"

        estado_clase = obtener_estado_visual(estado)

        # Crear un contenedor clickable
        cols = st.columns([1, 1, 4, 1, 1])
        with cols[0]:
            st.write(f"**{id_ot}**")
        with cols[1]:
            st.write(f"🔹 {tipo}")
        with cols[2]:
            st.write(descripcion)
        with cols[3]:
            st.markdown(f'<span class="estado-badge {estado_clase}">{estado}</span>', unsafe_allow_html=True)
        with cols[4]:
            st.write(tecnico)

        # Botón para seleccionar esta orden
        if st.button(f"📋 Ver", key=f"btn_ver_{idx}"):
            st.session_state.orden_seleccionada = row.to_dict()
            st.session_state.orden_seleccionada['index'] = idx
            st.session_state.pagina = 'detalle'
            st.rerun()

        st.divider()

    st.markdown("</div>", unsafe_allow_html=True)

    # ===== BOTÓN VOLVER AL INICIO (también al final) =====
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

    # Header tipo tablet
    st.markdown(f"""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>← Orden {orden.get('ID OT', '')}</span>
        <span style="font-size: 14px; opacity: 0.8;">{orden.get('Especialidad', '')}</span>
    </div>
    """, unsafe_allow_html=True)

    # ===== BOTÓN VOLVER AL INICIO =====
    boton_volver_inicio("detalle_top")

    # Panel de detalle
    st.markdown("<div class='detail-panel'>", unsafe_allow_html=True)

    # Info del equipo
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

    # Info general en columnas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
            <div style="font-size: 12px; color: #666;">ID OT</div>
            <div style="font-size: 18px; font-weight: 700; color: #1a237e;">{orden.get('ID OT', '')}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        estado_actual = str(orden.get('Estado', 'Pendiente'))
        estado_clase = obtener_estado_visual(estado_actual)
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
            <div style="font-size: 12px; color: #666;">Estado</div>
            <div class="estado-badge {estado_clase}">{estado_actual}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        tecnico_actual = str(orden.get('Tecnico_Asignado', ''))
        if not tecnico_actual:
            tecnico_actual = "Sin asignar"
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background: #f5f5f5; border-radius: 8px;">
            <div style="font-size: 12px; color: #666;">Técnico</div>
            <div style="font-size: 14px; font-weight: 600;">{tecnico_actual}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Descripción del procedimiento
    st.subheader("📝 Descripción")
    st.write(orden.get('Descripción de procedimiento', 'Sin descripción'))

    # Actividades con checkboxes
    st.subheader("✅ Actividades a Realizar")

    # Obtener actividades del equipo/nodo
    df_actividades = df[
        (df['Equipo'] == orden.get('Equipo', '')) & 
        (df['Ubicación'] == orden.get('Ubicación', '')) &
        (df['Nodo'] == nodo)
    ].copy()

    actividades_hechas = str(orden.get('Actividades_Hechas', '')).split(',') if orden.get('Actividades_Hechas') else []
    actividades_hechas = [a.strip() for a in actividades_hechas if a.strip()]

    # Checkbox para marcar actividades
    actividades_marcadas = []

    if len(df_actividades) > 0:
        for i, (_, act) in enumerate(df_actividades.iterrows()):
            act_desc = str(act.get('Actividades', act.get('Descripción de procedimiento', f'Actividad {i+1}')))
            act_key = f"act_{idx}_{i}"

            # Verificar si ya estaba marcada
            default_checked = act_key in st.session_state.actividades_check or act_desc in actividades_hechas

            checked = st.checkbox(
                f"📌 {act_desc}",
                value=default_checked,
                key=act_key
            )

            if checked:
                actividades_marcadas.append(act_desc)
                st.session_state.actividades_check[act_key] = True
            else:
                st.session_state.actividades_check[act_key] = False
    else:
        # Si no hay actividades específicas, mostrar la descripción como actividad principal
        act_desc = str(orden.get('Descripción de procedimiento', 'Verificación general'))
        act_key = f"act_{idx}_main"
        default_checked = act_key in st.session_state.actividades_check or act_desc in actividades_hechas

        checked = st.checkbox(
            f"📌 {act_desc}",
            value=default_checked,
            key=act_key
        )

        if checked:
            actividades_marcadas.append(act_desc)

    st.divider()

    # Formulario de actualización
    st.subheader("✏️ Actualizar Orden")

    with st.form("form_actualizar"):
        # Seleccionar técnico
        tecnicos_nodo = obtener_tecnicos_por_nodo(nodo, especialidad)
        tecnicos_opciones = tecnicos_nodo if tecnicos_nodo else obtener_tecnicos_por_especialidad(especialidad)

        tecnico_actual = str(orden.get('Tecnico_Asignado', ''))
        tecnico_index = 0
        if tecnico_actual and tecnico_actual in tecnicos_opciones:
            tecnico_index = tecnicos_opciones.index(tecnico_actual) + 1

        tecnico_sel = st.selectbox(
            "👷 Asignar Técnico", 
            ["-- Seleccionar --"] + tecnicos_opciones,
            index=tecnico_index
        )

        # Estado
        estados = ["Pendiente", "En Proceso", "Ejecutado", "Verificado", "Cerrada", "Cancelada"]
        estado_actual = str(orden.get('Estado', 'Pendiente'))
        estado_index = estados.index(estado_actual) if estado_actual in estados else 0

        nuevo_estado = st.selectbox("📊 Estado", estados, index=estado_index)

        # Fechas y horas
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_ejec = st.date_input("📅 Fecha Ejecución", value=datetime.now())
        with col_f2:
            horas_trab = st.number_input("⏱️ Horas", min_value=0.0, max_value=24.0, value=0.0, step=0.5)

        # Comentarios
        comentarios_actuales = str(orden.get('Comentarios', ''))
        comentarios = st.text_area("💬 Comentarios / Observaciones", 
                                   value=comentarios_actuales,
                                   placeholder="Escribe tus observaciones aquí...")

        # Botón guardar
        submitted = st.form_submit_button("💾 GUARDAR", use_container_width=True)

        if submitted:
            if tecnico_sel == "-- Seleccionar --":
                st.error("⚠️ Por favor selecciona un técnico")
            else:
                # Actualizar DataFrame
                mask = (df.index == idx)

                df.loc[mask, 'Estado'] = nuevo_estado
                df.loc[mask, 'Tecnico_Asignado'] = tecnico_sel
                df.loc[mask, 'Comentarios'] = comentarios
                df.loc[mask, 'Actividades_Hechas'] = ','.join(actividades_marcadas)
                df.loc[mask, 'Fecha_Ejecucion'] = fecha_ejec.strftime('%Y-%m-%d')
                df.loc[mask, 'Hora_Inicio'] = str(horas_trab)

                st.session_state.df_mantenimientos = df

                # Guardar en Excel
                try:
                    with pd.ExcelWriter("Formato de mantenimiento preventivo.xlsx", 
                                       engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df.to_excel(writer, sheet_name='Inicial_Actualizado', index=False)
                    st.success(f"✅ Guardado correctamente!")
                    st.balloons()
                except Exception as e:
                    st.warning(f"⚠️ Guardado en memoria. Error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ===== BOTÓN VOLVER AL INICIO (también al final) =====
    boton_volver_inicio("detalle_bottom")

    # Botón volver a órdenes (opcional, si quieres mantenerlo)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅️ VOLVER A ÓRDENES", use_container_width=True):
        st.session_state.orden_seleccionada = None
        st.session_state.pagina = 'ordenes'
        st.rerun()

# ==================== PANTALLA DE ASIGNACIÓN ====================

def pantalla_asignacion():
    """Pantalla para asignar técnicos a actividades por nodo"""
    df = st.session_state.df_mantenimientos
    df_tec = st.session_state.df_tecnicos

    # Header tipo tablet
    st.markdown("""
    <div class="tablet-header" style="display: flex; align-items: center; justify-content: space-between;">
        <span>📝 Asignación de Técnicos</span>
        <span style="font-size: 14px; opacity: 0.8;">Asignación</span>
    </div>
    """, unsafe_allow_html=True)

    # ===== BOTÓN VOLVER AL INICIO =====
    boton_volver_inicio("asignacion_top")

    # --- DATOS DE ASIGNACIÓN (simulados basados en la imagen) ---
    # En producción esto vendría de tu Excel de asignación
    datos_asignacion = [
        {"id": 1, "desc": "BANDAS TRANSPORTADORAS", "nodo": "BT01", "cant": 1, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Transporte"},
        {"id": 2, "desc": "BRAZO PENDULO", "nodo": "BP01", "cant": 1, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Manipulación"},
        {"id": 3, "desc": "CONVEYOR", "nodo": "CR01", "cant": 2, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Transporte"},
        {"id": 4, "desc": "DESEMBOBINADOR", "nodo": "DE01", "cant": 5, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Procesamiento"},
        {"id": 5, "desc": "EMBOBINADOR DE SCRAP", "nodo": "EB01", "cant": 2, "tecnico": "Guerra Arlex D.", "especialidad": "MEC", "maquina": "Procesamiento"},
        {"id": 6, "desc": "ESTACION DE APILADO", "nodo": "EA01", "cant": 4, "tecnico": "Sanchez Jair E.", "especialidad": "MEC", "maquina": "Almacenamiento"},
        {"id": 7, "desc": "FORMADORA", "nodo": "FM01", "cant": 7, "tecnico": "Sanchez Jair E.", "especialidad": "MEC", "maquina": "Procesamiento"},
        {"id": 8, "desc": "HORNO ELECTRICO", "nodo": "HE01", "cant": 3, "tecnico": "Ramirez Fabrianis", "especialidad": "ELE", "maquina": "Tratamiento"},
        {"id": 9, "desc": "MECANISMO RIELES", "nodo": "MR01", "cant": 6, "tecnico": "Valencia Carlos", "especialidad": "MEC", "maquina": "Transporte"},
        {"id": 10, "desc": "CORTADORA", "nodo": "CT01", "cant": 2, "tecnico": "", "especialidad": "MEC", "maquina": "Procesamiento"},
        {"id": 11, "desc": "PUNZONADORA", "nodo": "PZ01", "cant": 3, "tecnico": "", "especialidad": "MEC", "maquina": "Procesamiento"},
        {"id": 12, "desc": "SISTEMA HIDRAULICO", "nodo": "SH01", "cant": 1, "tecnico": "", "especialidad": "MEC", "maquina": "Auxiliar"},
        {"id": 13, "desc": "MOTOR PRINCIPAL", "nodo": "MP01", "cant": 2, "tecnico": "", "especialidad": "ELE", "maquina": "Procesamiento"},
        {"id": 14, "desc": "TABLERO CONTROL", "nodo": "TC01", "cant": 1, "tecnico": "", "especialidad": "ELE", "maquina": "Control"},
        {"id": 15, "desc": "AIRE ACONDICIONADO", "nodo": "AA01", "cant": 2, "tecnico": "", "especialidad": "ELE", "maquina": "Climatización"},
    ]

    df_asig = pd.DataFrame(datos_asignacion)

    # --- FILTROS SUPERIORES ---
    st.markdown("<br>", unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns([1, 1, 1])

    with col_f1:
        filtro_esp_asig = st.selectbox(
            "⚡ Filtrar por Especialidad",
            ["Todas", "ELE", "MEC"],
            index=["Todas", "ELE", "MEC"].index(st.session_state.get('filtro_esp_asig', 'Todas'))
        )
        st.session_state.filtro_esp_asig = filtro_esp_asig

    with col_f2:
        maquinas_asig = ["Todas"] + sorted(df_asig['maquina'].unique().tolist())
        filtro_maq_asig = st.selectbox(
            "🏭 Filtrar por Máquina / Ubicación",
            maquinas_asig,
            index=maquinas_asig.index(st.session_state.get('filtro_maq_asig', 'Todas')) if st.session_state.get('filtro_maq_asig', 'Todas') in maquinas_asig else 0
        )
        st.session_state.filtro_maq_asig = filtro_maq_asig

    with col_f3:
        filtro_estado_asig = st.selectbox(
            "📊 Filtrar por Estado",
            ["Todos", "Asignado", "Pendiente"],
            index=["Todos", "Asignado", "Pendiente"].index(st.session_state.get('filtro_estado_asig', 'Todos'))
        )
        st.session_state.filtro_estado_asig = filtro_estado_asig

    # --- ESTADÍSTICAS ---
    total_asig = len(df_asig)
    asignadas = len(df_asig[df_asig['tecnico'] != ''])
    pendientes = total_asig - asignadas
    pct_asig = round((asignadas / total_asig) * 100, 1) if total_asig > 0 else 0
    pct_pend = round((pendientes / total_asig) * 100, 1) if total_asig > 0 else 0

    st.markdown(f"""
    <div style="display: flex; gap: 20px; justify-content: center; margin: 20px 0; padding: 15px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <div style="text-align: center;">
            <div style="font-size: 28px; font-weight: 800; color: #28a745;">{pct_asig}%</div>
            <div style="font-size: 12px; color: #666;">✅ Asignadas ({asignadas})</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 28px; font-weight: 800; color: #dc3545;">{pct_pend}%</div>
            <div style="font-size: 12px; color: #666;">⏳ Pendientes ({pendientes})</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 28px; font-weight: 800; color: #1a237e;">{total_asig}</div>
            <div style="font-size: 12px; color: #666;">📋 Total Actividades</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- APLICAR FILTROS ---
    df_filtrado_asig = df_asig.copy()

    if filtro_esp_asig != "Todas":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['especialidad'] == filtro_esp_asig]

    if filtro_maq_asig != "Todas":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['maquina'] == filtro_maq_asig]

    if filtro_estado_asig == "Asignado":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['tecnico'] != '']
    elif filtro_estado_asig == "Pendiente":
        df_filtrado_asig = df_filtrado_asig[df_filtrado_asig['tecnico'] == '']

    # --- TABLA DE ASIGNACIÓN ---
    st.subheader(f"📋 Actividades ({len(df_filtrado_asig)})")

    # Header de tabla
    st.markdown("""
    <div class="orders-table">
        <div class="table-header" style="grid-template-columns: 2fr 80px 60px 1.5fr 100px;">
            <div>Descripción</div>
            <div>Nodo</div>
            <div style="text-align:center">Cant</div>
            <div>Técnico Asignado</div>
            <div>Estado</div>
        </div>
    """, unsafe_allow_html=True)

    # Lista de técnicos disponibles según especialidad filtrada
    if filtro_esp_asig == "ELE":
        tecnicos_disponibles = TECNICOS_ELE
    elif filtro_esp_asig == "MEC":
        tecnicos_disponibles = TECNICOS_MEC
    else:
        tecnicos_disponibles = TECNICOS_ELE + TECNICOS_MEC

    # Filas de la tabla
    for idx, row in df_filtrado_asig.iterrows():
        desc = row['desc']
        nodo = row['nodo']
        cant = row['cant']
        tecnico_actual = row['tecnico']
        especialidad = row['especialidad']
        is_asignado = tecnico_actual != ''

        estado_texto = "✅ Asignado" if is_asignado else "⏳ Pendiente"
        estado_clase = "estado-ejecutado" if is_asignado else "estado-pendiente"
        border_color = "#28a745" if is_asignado else "#dc3545"

        # Contenedor de fila con borde de estado
        with st.container():
            st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; padding: 12px 16px; 
                        background: white; border-radius: 0 8px 8px 0; 
                        margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: grid; grid-template-columns: 2fr 80px 60px 1.5fr 100px; gap: 12px; align-items: center;">
                    <div style="font-weight: 600; font-size: 14px; color: #1f2937;">{desc}</div>
                    <div><span style="display: inline-block; padding: 4px 10px; background: #eef2ff; color: #1a237e; border-radius: 6px; font-weight: 700; font-size: 13px; font-family: monospace;">{nodo}</span></div>
                    <div style="text-align: center;"><span style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; background: #f3f4f6; color: #374151; border-radius: 50%; font-weight: 700; font-size: 14px;">{cant}</span></div>
                    <div><span class="estado-badge {estado_clase}">{estado_texto}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Selector de técnico
            tecnico_key = f"tecnico_asig_{row['id']}"

            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                opciones_tec = ["-- Sin asignar --"] + tecnicos_disponibles
                tec_index = 0
                if tecnico_actual and tecnico_actual in tecnicos_disponibles:
                    tec_index = tecnicos_disponibles.index(tecnico_actual) + 1

                nuevo_tecnico = st.selectbox(
                    f"👷 Asignar técnico",
                    opciones_tec,
                    index=tec_index,
                    key=tecnico_key,
                    label_visibility="collapsed"
                )

            with col_t2:
                if st.button(f"💾 Guardar", key=f"btn_guardar_asig_{row['id']}"):
                    # Actualizar en el DataFrame
                    if nuevo_tecnico != "-- Sin asignar --":
                        df_asig.loc[df_asig['id'] == row['id'], 'tecnico'] = nuevo_tecnico
                    else:
                        df_asig.loc[df_asig['id'] == row['id'], 'tecnico'] = ''

                    st.success(f"✅ Asignación guardada para {desc}")
                    st.rerun()

        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # --- BOTÓN GUARDAR TODO ---
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 GUARDAR TODAS LAS ASIGNACIONES", use_container_width=True, type="primary"):
        st.success("✅ Todas las asignaciones han sido guardadas")
        st.balloons()

    # ===== BOTÓN VOLVER AL INICIO (también al final) =====
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
