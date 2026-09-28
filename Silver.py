import os
import pandas as pd
import logging
from datetime import datetime

# Configuración del sistema de logs
os.makedirs('logs/silver', exist_ok=True)
log_filename = f"logs/silver/silver_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.info("=== Iniciando procesamiento idempotente de Capa Silver ===")
os.makedirs('Silver', exist_ok=True)

try:
    logging.info("Leyendo archivos desde la Capa Bronze...")
    df_pasajeros = pd.read_csv('Bronze/ventas_pasajeros_bronze.csv')
    df_paqueteria = pd.read_csv('Bronze/ventas_paqueteria_bronze.csv')
    df_gps = pd.read_csv('Bronze/registros_gps_operacion_bronze.csv')
    df_abordajes = pd.read_csv('Bronze/check_in_abordajes_bronze.csv')
    df_unidades = pd.read_csv('Bronze/catalogo_unidades_bronze.csv')
    logging.info("Archivos leídos exitosamente.")
except Exception as e:
    logging.error(f"Error al leer los archivos Bronze: {e}")
    raise e

# 1. Limpieza y estandarización de ventas de pasajeros
logging.info(f"Procesando ventas de pasajeros ({len(df_pasajeros)} filas)...")
df_pasajeros.columns = [col.strip().lower() for col in df_pasajeros.columns]
df_pasajeros = df_pasajeros.drop_duplicates(subset=['id_pasajero']).copy()
df_pasajeros['fecha_salida'] = pd.to_datetime(df_pasajeros['fecha_salida'])
df_pasajeros['origen'] = df_pasajeros['origen'].str.upper().str.strip()
df_pasajeros['destino'] = df_pasajeros['destino'].str.upper().str.strip()
df_pasajeros = df_pasajeros.dropna(subset=['id_pasajero', 'total_venta'])
df_pasajeros.to_csv('Silver/ventas_pasajeros_silver.csv', index=False)

# 2. Limpieza y estandarización de ventas de paquetería
logging.info(f"Procesando ventas de paquetería ({len(df_paqueteria)} filas)...")
df_paqueteria.columns = [col.strip().lower() for col in df_paqueteria.columns]
df_paqueteria = df_paqueteria.drop_duplicates(subset=['id_paquete']).copy()
df_paqueteria = df_paqueteria.rename(columns={'total_venta': 'ingreso_paqueteria'})
df_paqueteria['fecha'] = pd.to_datetime(df_paqueteria['fecha'])
df_paqueteria['origen'] = df_paqueteria['origen'].str.upper().str.strip()
df_paqueteria['destino'] = df_paqueteria['destino'].str.upper().str.strip()
df_paqueteria = df_paqueteria.dropna(subset=['id_paquete', 'ingreso_paqueteria'])
df_paqueteria.to_csv('Silver/ventas_paqueteria_silver.csv', index=False)

# 3. Procesamiento y enriquecimiento de GPS (Conservando el id_chofer)
logging.info(f"Procesando registros GPS y unidades ({len(df_gps)} filas)...")
df_gps.columns = [col.strip().lower() for col in df_gps.columns]
df_unidades.columns = [col.strip().lower() for col in df_unidades.columns]
df_unidades = df_unidades.drop_duplicates(subset=['id_unidad'])

df_gps = df_gps.drop_duplicates(subset=['id_viaje']).copy()

# Limpiar las fechas para asegurarnos que tengan el formato correcto
df_gps['fecha_partida'] = pd.to_datetime(df_gps['fecha_partida']).dt.strftime('%Y-%m-%d')
df_gps['fecha_llegada'] = pd.to_datetime(df_gps['fecha_llegada']).dt.strftime('%Y-%m-%d')

df_gps_enriquecido = df_gps.merge(df_unidades, on='id_unidad', how='left')

# Seleccionamos las columnas limpias (incluyendo id_chofer para los KPIs de la Capa Gold)
columnas_gps_limpias = [
    'id_viaje', 'id_unidad', 'id_chofer', 'placa', 'serie', 'timestamp_mantenimiento',
    'fecha_partida', 'hora_partida', 'fecha_llegada', 'hora_llegada',
    'kms_recorridos', 'consumo_combustible'
]
df_gps_enriquecido = df_gps_enriquecido[columnas_gps_limpias]
df_gps_enriquecido.to_csv('Silver/registros_gps_silver.csv', index=False)

# 4. Limpieza de registros de abordaje y check-in
logging.info(f"Procesando check-in / abordajes ({len(df_abordajes)} filas)...")
df_abordajes.columns = [col.strip().lower() for col in df_abordajes.columns]
df_abordajes = df_abordajes.drop_duplicates(subset=['id_viaje', 'id_pasajero', 'id_paqueteria']).copy()
df_abordajes['fecha_partida'] = pd.to_datetime(df_abordajes['fecha_partida']).dt.strftime('%Y-%m-%d')
df_abordajes['origen'] = df_abordajes['origen'].str.upper().str.strip()
df_abordajes['destino'] = df_abordajes['destino'].str.upper().str.strip()
df_abordajes.to_csv('Silver/check_in_abordajes_silver.csv', index=False)

logging.info("=== Capa Silver procesada con éxito")