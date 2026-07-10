import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuracion de la pagina - MODO TABLET
st.set_page_config(
    page_title="App Tablet Mtto Preventivo",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== ESTILOS CSS - DISENO TABLET COMPACTO ====================
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f5;
        max-width: 100vw;
        overflow-x: hidden;
    }

    /* Fix para tablet - evitar scroll horizontal */
    .main .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 100% !important;
    }

    /* Asegurar que el contenido no se desborde */
    div[data-testid="stVerticalBlock"] {
        gap: 0.3rem !important;
    }

    .tablet-header {
        background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 0 0 16px 16px;
        text-align: center;
        font-size: 18px;
        font-weight: 700;
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 4px 15px rgba(26,35,158,0.3);
        position: sticky;
        top: 0;
        z-index: 100;
        width: 100%;
        box-sizing: border-box;
        word-wrap: break-word;
    }

    .home-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
        min-height: auto;
        text-align: center;
        padding: 10px;
        width: 100%;
        box-sizing: border-box;
    }

    .big-counter {
        font-size: 60px;
        font-weight: 900;
        color: #1a237e;
        line-height: 1;
        margin: 10px 0;
        word-wrap: break-word;
    }

    .counter-label {
        font-size: 18px;
        color: #666;
        margin-bottom: 30px;
    }

    .estado-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        text-align: center;
        white-space: nowrap;
    }

    .estado-ejecutado { background-color: #d4edda; color: #155724; }
    .estado-pendiente { background-color: #fff3cd; color: #856404; }
    .estado-verificado { background-color: #cce5ff; color: #004085; }
    .estado-cerrada { background-color: #d1ecf1; color: #0c5460; }

    .progress-bar-container {
        display: flex;
        gap: 15px;
        justify-content: center;
        margin: 15px 0;
        padding: 12px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .progress-item {
        text-align: center;
    }

    .progress-value {
        font-size: 22px;
        font-weight: 800;
