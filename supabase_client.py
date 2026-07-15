from supabase import create_client
import streamlit as st

# Leer credenciales de forma segura desde st.secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://cpazmoebqbsrahviifvp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY no configurada. Revisa tu secrets.toml o variables de entorno.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
