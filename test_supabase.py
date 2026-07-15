from supabase_client import supabase

# Probar conexión
response = supabase.table('ordenes_trabajo').select('count', count='exact').execute()
print(f"✅ Conexión exitosa! Registros en tabla: {response.count}")
