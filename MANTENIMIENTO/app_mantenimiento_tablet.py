# ============================================================
# APP MANTENIMIENTO PREVENTIVO - VERSION TABLET CON TARJETAS DASHBOARD
# Tarjetas blancas tipo dashboard para Tecnico y Admin
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client
import hashlib

# ============ CONFIGURACION ============
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://cpazmoebqbsrahviifvp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_KEY:
    st.error("SUPABASE_KEY no configurada.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============ TECNICOS ============
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

# ============ FUNCIONES AYUDA ============
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

def cargar_datos():
    try:
        response = supabase.table("ordenes_trabajo").select("*").order("id", desc=False).execute()
        data = response.data
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        mapeo = {
            "id": "ID", "id_ot": "ID OT", "descripcion_procedimiento": "Descripcion",
            "tecnico_asignado": "Tecnico", "estado": "Estado", "ejecutado": "Ejecutado",
            "actividades_hechas": "Actividades", "fecha_ejecucion": "Fecha",
            "hora_inicio": "Hora_Inicio", "hora_fin": "Hora_Fin",
            "equipo": "Equipo", "ubicacion": "Ubicacion", "especialidad": "Especialidad",
            "nodo": "Nodo", "comentarios": "Comentarios"
        }
        df = df.rename(columns={k: v for k, v in mapeo.items() if k in df.columns})
        for col, default in [("Ejecutado", False), ("Estado", "Pendiente"), ("Tecnico", "")]:
            if col not in df.columns:
                df[col] = default
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

def guardar_campo(id_interno, campo, valor):
    try:
        campo_snake = campo.lower().replace(" ", "_")
        supabase.table("ordenes_trabajo").update({campo_snake: valor}).eq("id", id_interno).execute()
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False

def gen_key(base, *parts):
    perfil = st.session_state.get("perfil", "none")
    pagina = st.session_state.get("pagina", "none")
    part_str = "_".join(str(p) for p in parts)
    raw = f"{base}_{perfil}_{pagina}_{part_str}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]

# ============ ESTILOS ============
st.set_page_config(page_title="Mantenimiento", page_icon="🔧", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f3f4f6; }
    .main .block-container { padding: 0.5rem !important; max-width: 100% !important; }

    /* BOTONES NORMALES */
    .stButton>button {
        font-size: 22px !important;
        font-weight: 700 !important;
        padding: 18px 24px !important;
        border-radius: 16px !important;
        min-height: 70px !important;
    }

    /* SELECTBOX */
    .stSelectbox label { font-size: 18px !important; color: #374151 !important; font-weight: 700 !important; }
    .stSelectbox div[data-baseweb="select"] { font-size: 18px !important; }

    /* TEXTOS */
    h1 { font-size: 32px !important; color: #111827 !important; }
    h2 { font-size: 26px !important; color: #111827 !important; }
    h3 { font-size: 22px !important; color: #111827 !important; }

    /* HEADER */
    .tablet-header {
        background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%);
        color: white; padding: 20px; text-align: center; font-size: 28px; font-weight: 800;
        border-radius: 0 0 20px 20px; margin: -1rem -1rem 1rem -1rem;
    }

    /* TARJETA ACTIVIDAD (modo oscuro) */
    .actividad-card {
        background: #1E293B;
        border: 2px solid #334155;
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .actividad-hecha {
        border-color: #22c55e !important;
        background: #064e3b !important;
    }
    .equipo-titulo {
        background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%);
        color: white;
        padding: 14px 18px;
        border-radius: 14px;
        font-size: 20px;
        font-weight: 800;
        margin-bottom: 12px;
    }
    .badge-ele { background: #fbbf24; color: #0f172a; padding: 4px 12px; border-radius: 8px; font-size: 14px; font-weight: 800; }
    .badge-mec { background: #22c55e; color: #0f172a; padding: 4px 12px; border-radius: 8px; font-size: 14px; font-weight: 800; }
    .contador-grande { font-size: 48px; font-weight: 900; color: #0ea5e9; }
    .contador-texto { font-size: 16px; color: #6b7280; }
    .barra-progreso {
        width: 100%; height: 20px; background: #e5e7eb; border-radius: 10px; margin-top: 8px;
    }
    .barra-progreso-fill {
        height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a);
        border-radius: 10px; transition: width 0.3s;
    }

    /* ============================================================
       TARJETAS DE MAQUINA - ESTILO DASHBOARD EXACTO
       ============================================================ */
    .tarjeta-maquina {
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
        padding: 24px 20px 16px 20px;
        text-align: center;
        margin-bottom: 0;
        border: 1px solid #f3f4f6;
    }
    .tarjeta-titulo {
        font-size: 12px;
        font-weight: 600;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .tarjeta-subtitulo {
        font-size: 13px;
        color: #9ca3af;
        margin-bottom: 12px;
    }
    .tarjeta-numero {
        font-size: 42px;
        font-weight: 800;
        color: #111827;
        line-height: 1;
        margin: 8px 0;
    }
    .tarjeta-stats {
        font-size: 13px;
        color: #6b7280;
        margin-top: 8px;
    }
    .tarjeta-barra {
        width: 100%;
        height: 6px;
        background: #e5e7eb;
        border-radius: 3px;
        margin-top: 10px;
        overflow: hidden;
    }
    .tarjeta-barra-fill {
        height: 100%;
        background: linear-gradient(90deg, #22c55e, #16a34a);
        border-radius: 3px;
    }
    .tarjeta-pct {
        font-size: 12px;
        color: #9ca3af;
        margin-top: 6px;
    }

    /* Boton integrado a la tarjeta */
    .btn-maquina .stButton {
        width: 100%;
    }
    .btn-maquina .stButton > button {
        width: 100% !important;
        border-radius: 0 0 12px 12px !important;
        margin-top: 0 !important;
        background: #f9fafb !important;
        color: #374151 !important;
        border: 1px solid #f3f4f6 !important;
        border-top: none !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        min-height: 48px !important;
        padding: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    .btn-maquina .stButton > button:hover {
        background: #f3f4f6 !important;
    }
    .btn-maquina .stButton > button:active {
        background: #e5e7eb !important;
    }

    /* Contador global */
    .contador-global {
        background: #ffffff;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        padding: 16px 20px;
        text-align: center;
        min-width: 100px;
    }
    .contador-global-num {
        font-size: 36px;
        font-weight: 800;
        color: #111827;
    }
    .contador-global-label {
        font-size: 12px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ============ SESSION STATE ============
if "perfil" not in st.session_state: st.session_state.perfil = None
if "pagina" not in st.session_state: st.session_state.pagina = "login"
if "tecnico" not in st.session_state: st.session_state.tecnico = ""
if "df" not in st.session_state: st.session_state.df = cargar_datos()
if "guardado_ok" not in st.session_state: st.session_state.guardado_ok = False
if "maquina_sel" not in st.session_state: st.session_state.maquina_sel = None
if "cambios" not in st.session_state: st.session_state.cambios = {}
if "admin_maquina_sel" not in st.session_state: st.session_state.admin_maquina_sel = None
if "admin_cambios" not in st.session_state: st.session_state.admin_cambios = {}

# ============ LOGIN ============
def pantalla_login():
    st.markdown('<div class="tablet-header">🔧 MANTENIMIENTO PREVENTIVO</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("👷 SOY TÉCNICO", use_container_width=True, type="primary"):
            st.session_state.perfil = "tecnico"
            st.session_state.pagina = "home"
            st.session_state.maquina_sel = None
            st.session_state.admin_maquina_sel = None
            st.rerun()
    with col2:
        if st.button("👤 SOY ADMIN", use_container_width=True, type="primary"):
            st.session_state.perfil = "admin"
            st.session_state.pagina = "home"
            st.session_state.maquina_sel = None
            st.session_state.admin_maquina_sel = None
            st.rerun()

# ============ TECNICO ============
def pantalla_tecnico():
    df = cargar_datos()
    st.session_state.df = df

    st.markdown('<div class="tablet-header">👷 TÉCNICO</div>', unsafe_allow_html=True)

    todos_tecnicos = sorted(TECNICOS_ELE + TECNICOS_MEC)
    idx = 0
    if st.session_state.tecnico and st.session_state.tecnico in todos_tecnicos:
        idx = todos_tecnicos.index(st.session_state.tecnico)

    tecnico = st.selectbox("SELECCIONA TU NOMBRE:", todos_tecnicos, index=idx, key=gen_key("sel_tec"))
    st.session_state.tecnico = tecnico

    if not tecnico:
        st.info("Selecciona tu nombre para ver tus actividades")
        return

    df_mio = df[df["Tecnico"] == tecnico].copy() if "Tecnico" in df.columns else pd.DataFrame()

    if df_mio.empty:
        st.info("No tienes actividades asignadas.")
        if st.button("🔄 ACTUALIZAR", use_container_width=True, key=gen_key("btn_refresh_tec")):
            st.rerun()
        return

    total = len(df_mio)
    hechas = len(df_mio[df_mio["Ejecutado"] == True]) if "Ejecutado" in df_mio.columns else 0
    faltan = total - hechas
    pct = round((hechas / total) * 100, 0) if total > 0 else 0

    # Contadores estilo dashboard
    st.markdown(f"""
    <div style="display: flex; gap: 12px; justify-content: center; margin: 16px 0; flex-wrap: wrap;">
        <div class="contador-global">
            <div class="contador-global-num">{total}</div>
            <div class="contador-global-label">Total</div>
        </div>
        <div class="contador-global">
            <div class="contador-global-num" style="color: #22c55e;">{hechas}</div>
            <div class="contador-global-label">Hechas</div>
        </div>
        <div class="contador-global">
            <div class="contador-global-num" style="color: #f59e0b;">{faltan}</div>
            <div class="contador-global-label">Faltan</div>
        </div>
    </div>
    <div style="text-align: center; margin-bottom: 16px;">
        <div class="barra-progreso" style="max-width: 400px; margin: 0 auto;">
            <div class="barra-progreso-fill" style="width: {pct}%;"></div>
        </div>
        <div style="font-size: 14px; color: #6b7280; margin-top: 6px;">{pct}% completado</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.guardado_ok:
        st.success("✅ CAMBIOS GUARDADOS CORRECTAMENTE")
        st.session_state.guardado_ok = False

    st.markdown("<br>", unsafe_allow_html=True)

    grupos = df_mio.groupby(["Equipo", "Ubicacion"])

    # --- NIVEL 1: TARJETAS DE MAQUINAS ---
    if st.session_state.maquina_sel is None:
        st.subheader("🏭 SELECCIONA UNA MÁQUINA")

        grupos_list = list(grupos)
        for i in range(0, len(grupos_list), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(grupos_list):
                    (equipo, ubicacion), grupo = grupos_list[i + j]
                    total_g = len(grupo)
                    hechas_g = len(grupo[grupo["Ejecutado"] == True]) if "Ejecutado" in grupo.columns else 0
                    faltan_g = total_g - hechas_g
                    pct_g = round((hechas_g / total_g) * 100, 0) if total_g > 0 else 0

                    with cols[j]:
                        # Tarjeta visual tipo dashboard
                        st.markdown(f"""
                        <div class="tarjeta-maquina">
                            <div class="tarjeta-titulo">{equipo}</div>
                            <div class="tarjeta-subtitulo">{ubicacion}</div>
                            <div class="tarjeta-numero">{total_g}</div>
                            <div class="tarjeta-stats">✅ {hechas_g} hechas · 🔴 {faltan_g} faltan</div>
                            <div class="tarjeta-barra">
                                <div class="tarjeta-barra-fill" style="width: {pct_g}%;"></div>
                            </div>
                            <div class="tarjeta-pct">{pct_g}% completado</div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Botón integrado debajo
                        st.markdown('<div class="btn-maquina">', unsafe_allow_html=True)
                        if st.button("📋 ABRIR MÁQUINA", use_container_width=True,
                                     key=gen_key("maq", equipo, ubicacion)):
                            st.session_state.maquina_sel = (equipo, ubicacion)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)

        col_r1, col_r2, col_r3 = st.columns([1, 2, 1])
        with col_r2:
            if st.button("🔄 ACTUALIZAR DATOS", use_container_width=True, key=gen_key("btn_refresh_tec2")):
                st.rerun()

    # --- NIVEL 2: ACTIVIDADES ---
    else:
        equipo_sel, ubicacion_sel = st.session_state.maquina_sel
        df_maquina = df_mio[(df_mio["Equipo"] == equipo_sel) & (df_mio["Ubicacion"] == ubicacion_sel)].copy()

        col_v1, col_v2 = st.columns([1, 4])
        with col_v1:
            if st.button("⬅️ VOLVER", use_container_width=True, key=gen_key("btn_volver")):
                st.session_state.maquina_sel = None
                st.session_state.cambios = {}
                st.rerun()
        with col_v2:
            total_m = len(df_maquina)
            hechas_m = len(df_maquina[df_maquina["Ejecutado"] == True]) if "Ejecutado" in df_maquina.columns else 0
            st.markdown(f"""
            <div class="equipo-titulo" style="margin-top: 0;">
                🔧 {equipo_sel} — {ubicacion_sel}<br>
                <span style="font-size: 14px; font-weight: 400;">✅ {hechas_m}/{total_m} actividades</span>
            </div>
            """, unsafe_allow_html=True)

        for idx, row in df_maquina.iterrows():
            internal_id = limpiar(row.get("ID"), "")
            desc = limpiar(row.get("Descripcion"), "Sin descripcion")
            esp = limpiar(row.get("Especialidad"), "")
            ejecutado = bool(row.get("Ejecutado", False))

            if internal_id in st.session_state.cambios:
                valor_checkbox = st.session_state.cambios[internal_id]
            else:
                valor_checkbox = ejecutado

            chk_key = gen_key("chk", internal_id, equipo_sel, ubicacion_sel)
            clase_card = "actividad-hecha" if valor_checkbox else ""
            badge = f'<span class="badge-{esp.lower()}">{esp}</span>' if esp else ""

            st.markdown(f'<div class="actividad-card {clase_card}">', unsafe_allow_html=True)
            col1, col2 = st.columns([0.15, 0.85])
            with col1:
                nuevo_valor = st.checkbox("", value=valor_checkbox, key=chk_key, label_visibility="collapsed")
            with col2:
                st.markdown(f"""
                <div style="font-size: 18px; font-weight: 600; color: #E0F2FE;">{desc}</div>
                <div style="margin-top: 6px;">{badge}</div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if nuevo_valor != ejecutado:
                st.session_state.cambios[internal_id] = nuevo_valor
            elif internal_id in st.session_state.cambios and nuevo_valor == ejecutado:
                del st.session_state.cambios[internal_id]

        st.markdown("<br>", unsafe_allow_html=True)
        hay_cambios = len(st.session_state.cambios) > 0
        col_g1, col_g2, col_g3 = st.columns([1, 3, 1])
        with col_g2:
            if st.button("💾 GUARDAR CAMBIOS", use_container_width=True, type="primary",
                         key=gen_key("btn_guardar_todo"), disabled=not hay_cambios):
                guardados = 0
                for internal_id, nuevo_valor in list(st.session_state.cambios.items()):
                    if guardar_campo(internal_id, "ejecutado", nuevo_valor):
                        guardados += 1
                        if nuevo_valor:
                            guardar_campo(internal_id, "estado", "Ejecutado")
                            guardar_campo(internal_id, "fecha_ejecucion", datetime.now().strftime("%Y-%m-%d"))
                            guardar_campo(internal_id, "hora_fin", datetime.now().strftime("%H:%M"))
                        else:
                            guardar_campo(internal_id, "estado", "Pendiente")
                st.session_state.cambios = {}
                if guardados > 0:
                    st.session_state.guardado_ok = True
                st.rerun()
            if not hay_cambios:
                st.caption("No hay cambios para guardar")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True, type="secondary", key=gen_key("btn_salir_tec")):
        st.session_state.perfil = None
        st.session_state.pagina = "login"
        st.session_state.tecnico = ""
        st.session_state.maquina_sel = None
        st.session_state.cambios = {}
        st.rerun()

# ============ ADMIN ============
def pantalla_admin():
    df = cargar_datos()
    st.session_state.df = df

    st.markdown('<div class="tablet-header">👤 ADMINISTRADOR</div>', unsafe_allow_html=True)

    if df.empty:
        st.error("No hay datos cargados")
        return

    total = len(df)
    ele = len(df[df["Especialidad"] == "ELE"]) if "Especialidad" in df.columns else 0
    mec = len(df[df["Especialidad"] == "MEC"]) if "Especialidad" in df.columns else 0
    hechas = len(df[df["Ejecutado"] == True]) if "Ejecutado" in df.columns else 0

    # Contadores estilo dashboard
    st.markdown(f"""
    <div style="display: flex; gap: 12px; justify-content: center; margin: 16px 0; flex-wrap: wrap;">
        <div class="contador-global">
            <div class="contador-global-num">{total}</div>
            <div class="contador-global-label">Total Actividades</div>
        </div>
        <div class="contador-global">
            <div class="contador-global-num" style="color: #f59e0b;">{ele}</div>
            <div class="contador-global-label">ELE</div>
        </div>
        <div class="contador-global">
            <div class="contador-global-num" style="color: #22c55e;">{mec}</div>
            <div class="contador-global-label">MEC</div>
        </div>
        <div class="contador-global">
            <div class="contador-global-num" style="color: #0ea5e9;">{hechas}</div>
            <div class="contador-global-label">Realizadas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.guardado_ok:
        st.success("✅ CAMBIOS GUARDADOS CORRECTAMENTE")
        st.session_state.guardado_ok = False

    st.markdown("<br>", unsafe_allow_html=True)

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_esp = st.selectbox("ESPECIALIDAD:", ["Todas", "ELE", "MEC"], key=gen_key("filtro_esp_admin"))
    with col_f2:
        buscar = st.text_input("BUSCAR:", placeholder="ID o equipo", key=gen_key("buscar_admin"))

    df_asig = df.copy()
    if filtro_esp != "Todas" and "Especialidad" in df_asig.columns:
        df_asig = df_asig[df_asig["Especialidad"] == filtro_esp]
    if buscar and "ID OT" in df_asig.columns:
        df_asig = df_asig[df_asig["ID OT"].astype(str).str.contains(buscar, na=False)]

    if df_asig.empty:
        st.info("No hay actividades con esos filtros.")
        return

    grupos = df_asig.groupby(["Equipo", "Ubicacion"])

    # --- NIVEL 1: TARJETAS DE MAQUINAS (ADMIN) ---
    if st.session_state.admin_maquina_sel is None:
        st.subheader(f"🏭 MÁQUINAS ({len(df_asig)} actividades)")

        grupos_list = list(grupos)
        for i in range(0, len(grupos_list), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(grupos_list):
                    (equipo, ubicacion), grupo = grupos_list[i + j]
                    total_g = len(grupo)
                    hechas_g = len(grupo[grupo["Ejecutado"] == True]) if "Ejecutado" in grupo.columns else 0
                    asignadas_g = len(grupo[grupo["Tecnico"] != ""]) if "Tecnico" in grupo.columns else 0
                    faltan_g = total_g - hechas_g
                    pct_g = round((hechas_g / total_g) * 100, 0) if total_g > 0 else 0

                    with cols[j]:
                        # Tarjeta visual tipo dashboard
                        st.markdown(f"""
                        <div class="tarjeta-maquina">
                            <div class="tarjeta-titulo">{equipo}</div>
                            <div class="tarjeta-subtitulo">{ubicacion}</div>
                            <div class="tarjeta-numero">{total_g}</div>
                            <div class="tarjeta-stats">✅ {hechas_g} hechas · 👤 {asignadas_g} asignadas · 🔴 {faltan_g} faltan</div>
                            <div class="tarjeta-barra">
                                <div class="tarjeta-barra-fill" style="width: {pct_g}%;"></div>
                            </div>
                            <div class="tarjeta-pct">{pct_g}% completado</div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Botón integrado debajo
                        st.markdown('<div class="btn-maquina">', unsafe_allow_html=True)
                        if st.button("📋 ASIGNAR TÉCNICOS", use_container_width=True,
                                     key=gen_key("adm_maq", equipo, ubicacion)):
                            st.session_state.admin_maquina_sel = (equipo, ubicacion)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)

        col_r1, col_r2, col_r3 = st.columns([1, 2, 1])
        with col_r2:
            if st.button("🔄 ACTUALIZAR DATOS", use_container_width=True, key=gen_key("btn_refresh_admin")):
                st.rerun()

    # --- NIVEL 2: ACTIVIDADES DE LA MAQUINA (ADMIN) ---
    else:
        equipo_sel, ubicacion_sel = st.session_state.admin_maquina_sel
        df_maquina = df_asig[(df_asig["Equipo"] == equipo_sel) & (df_asig["Ubicacion"] == ubicacion_sel)].copy()

        col_v1, col_v2 = st.columns([1, 4])
        with col_v1:
            if st.button("⬅️ VOLVER", use_container_width=True, key=gen_key("btn_volver_admin")):
                st.session_state.admin_maquina_sel = None
                st.session_state.admin_cambios = {}
                st.rerun()
        with col_v2:
            total_m = len(df_maquina)
            hechas_m = len(df_maquina[df_maquina["Ejecutado"] == True]) if "Ejecutado" in df_maquina.columns else 0
            st.markdown(f"""
            <div class="equipo-titulo" style="margin-top: 0;">
                🔧 {equipo_sel} — {ubicacion_sel}<br>
                <span style="font-size: 14px; font-weight: 400;">✅ {hechas_m}/{total_m} actividades</span>
            </div>
            """, unsafe_allow_html=True)

        todos_tecnicos = sorted(TECNICOS_ELE + TECNICOS_MEC)
        opciones_tec = ["Sin asignar"] + todos_tecnicos

        for idx, row in df_maquina.iterrows():
            internal_id = limpiar(row.get("ID"), "")
            id_ot = limpiar(row.get("ID OT"), "SIN ID")
            desc = limpiar(row.get("Descripcion"), "Sin descripcion")
            esp = limpiar(row.get("Especialidad"), "")
            tecnico_actual = limpiar(row.get("Tecnico"), "")
            ejecutado = bool(row.get("Ejecutado", False))

            if internal_id in st.session_state.admin_cambios:
                valor_tec = st.session_state.admin_cambios[internal_id]
            else:
                valor_tec = tecnico_actual

            sel_key = gen_key("adm_sel", internal_id, equipo_sel, ubicacion_sel)

            badge = f'<span class="badge-{esp.lower()}">{esp}</span>' if esp else ""
            estado_color = "#22c55e" if ejecutado else "#f59e0b"
            estado_texto = "✅ HECHA" if ejecutado else "⏳ PENDIENTE"

            st.markdown(f"""
            <div class="actividad-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 18px; font-weight: 700;">OT {id_ot}</div>
                    <div style="color: {estado_color}; font-weight: 700;">{estado_texto}</div>
                </div>
                <div style="font-size: 16px; margin: 8px 0;">{desc}</div>
                <div style="margin-top: 4px;">{badge}</div>
            </div>
            """, unsafe_allow_html=True)

            idx_tec = opciones_tec.index(valor_tec) if valor_tec in opciones_tec else 0
            nuevo_tec = st.selectbox("TÉCNICO:", opciones_tec, index=idx_tec, key=sel_key)

            if nuevo_tec != tecnico_actual:
                st.session_state.admin_cambios[internal_id] = nuevo_tec
            elif internal_id in st.session_state.admin_cambios and nuevo_tec == tecnico_actual:
                del st.session_state.admin_cambios[internal_id]

            st.markdown("<hr style='border-color: #334155; margin: 12px 0;'>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        hay_cambios = len(st.session_state.admin_cambios) > 0
        col_g1, col_g2, col_g3 = st.columns([1, 3, 1])
        with col_g2:
            if st.button("💾 GUARDAR ASIGNACIONES", use_container_width=True, type="primary",
                         key=gen_key("btn_guardar_admin"), disabled=not hay_cambios):
                guardados = 0
                for internal_id, nuevo_tec in list(st.session_state.admin_cambios.items()):
                    if nuevo_tec == "Sin asignar":
                        if guardar_campo(internal_id, "tecnico_asignado", None):
                            guardados += 1
                    else:
                        if guardar_campo(internal_id, "tecnico_asignado", nuevo_tec):
                            guardados += 1
                st.session_state.admin_cambios = {}
                if guardados > 0:
                    st.session_state.guardado_ok = True
                st.rerun()
            if not hay_cambios:
                st.caption("No hay cambios para guardar")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 CERRAR SESIÓN", use_container_width=True, type="secondary", key=gen_key("btn_salir_admin")):
        st.session_state.perfil = None
        st.session_state.pagina = "login"
        st.session_state.admin_maquina_sel = None
        st.session_state.admin_cambios = {}
        st.rerun()

# ============ ROUTER ============
if st.session_state.pagina == "login":
    pantalla_login()
elif st.session_state.pagina == "home":
    if st.session_state.perfil == "tecnico":
        pantalla_tecnico()
    elif st.session_state.perfil == "admin":
        pantalla_admin()
    else:
        st.session_state.pagina = "login"
        st.rerun()
else:
    st.session_state.pagina = "login"
    st.rerun()
