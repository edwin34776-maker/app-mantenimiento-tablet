from supabase import create_client

# Tu URL de Supabase
SUPABASE_URL = "https://cpazmoebqbsrahviifvp.supabase.co"

# Tu ANON KEY - LA ENCUENTRAS EN SUPABASE → Settings → API → "anon public"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNwYXptb2VicWJzcmFodmlpZnZwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDE5ODI0MDAsImV4cCI6MjA1NzU1ODQwMH0."  # <-- REEMPLAZA CON TU ANON KEY REAL

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
