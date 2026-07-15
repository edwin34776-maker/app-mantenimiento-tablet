from supabase import create_client

# Tu URL de Supabase
SUPABASE_URL = "https://cpazmoebqbsrahviifvp.supabase.co"

# Tu ANON KEY
SUPABASE_KEY = "sb_publishable_UAJPuKcM42lrD0rXJ8c4AA_JNATpTc_"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
