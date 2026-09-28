import os
import pandas as pd
import logging
from datetime import datetime

# Configuración de logs independientes para la Capa Gold
os.makedirs('logs/gold', exist_ok=True)
log_filename = f"logs/gold/gold_etl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logging.info("=== Iniciando procesamiento idempotente de Capa Gold ===")
os.makedirs('Gold', exist_ok=True)

try:
    logging.info("Leyendo datos limpios desde la Capa Silver...")
    df_gps = pd.read_csv('Silver/registros_gps_silver.csv')
    df_abordajes = pd.read_csv('Silver/check_in_abordajes_silver.csv')
    df_pasajeros = pd.read_csv('Silver/ventas_pasajeros_silver.csv')
    df_paquetes = pd.read_csv('Silver/ventas_paqueteria_silver.csv')
    logging.info("Datos de Capa Silver leídos con éxito.")
except Exception as e:
    logging.error(f"Error al leer archivos Silver: {e}")
    raise e

# 1. Procesar métricas operativas e ingresos por viaje
logging.info("Calculando agregaciones y rendimiento por viaje...")

pax_abordados = df_abordajes[df_abordajes['id_pasajero'].notna()].groupby('id_viaje').size().reset_index(name='total_pasajeros')
pkg_abordados = df_abordajes[df_abordajes['id_paqueteria'].notna()].groupby('id_viaje').size().reset_index(name='total_paquetes')

ingreso_pax = df_abordajes[df_abordajes['id_pasajero'].notna()].merge(df_pasajeros, on='id_pasajero', how='inner')
ingresos_pasajeros = ingreso_pax.groupby('id_viaje')['total_venta'].sum().reset_index(name='ingresos_pasajeros')

ingreso_pkg = df_abordajes[df_abordajes['id_paqueteria'].notna()].merge(df_paquetes, left_on='id_paqueteria', right_on='id_paquete', how='inner')
ingresos_paqueteria = ingreso_pkg.groupby('id_viaje')['ingreso_paqueteria'].sum().reset_index(name='ingresos_paqueteria')

origen_destino_viaje = df_abordajes[['id_viaje', 'origen', 'destino']].drop_duplicates(subset=['id_viaje'])

df_gold_viajes = df_gps.copy()
if 'origen' in df_gold_viajes.columns:
    df_gold_viajes = df_gold_viajes.drop(columns=['origen', 'destino'], errors='ignore')
df_gold_viajes = df_gold_viajes.merge(origen_destino_viaje, on='id_viaje', how='left')

df_gold_viajes = df_gold_viajes.merge(pax_abordados, on='id_viaje', how='left').fillna({'total_pasajeros': 0})
df_gold_viajes = df_gold_viajes.merge(pkg_abordados, on='id_viaje', how='left').fillna({'total_paquetes': 0})
df_gold_viajes = df_gold_viajes.merge(ingresos_pasajeros, on='id_viaje', how='left').fillna({'ingresos_pasajeros': 0})
df_gold_viajes = df_gold_viajes.merge(ingresos_paqueteria, on='id_viaje', how='left').fillna({'ingresos_paqueteria': 0})

# Cálculo de Indicadores de Negocio y KPIs Financieros Avanzados
df_gold_viajes['ingreso_total'] = df_gold_viajes['ingresos_pasajeros'] + df_gold_viajes['ingresos_paqueteria']
df_gold_viajes['km_por_litro'] = round(df_gold_viajes['kms_recorridos'] / df_gold_viajes['consumo_combustible'], 2)

# Nuevos KPIS de rentabilidad
df_gold_viajes['ingreso_por_km'] = round(df_gold_viajes['ingreso_total'] / df_gold_viajes['kms_recorridos'].replace(0, 1), 2)
df_gold_viajes['yield_pasajero_km'] = df_gold_viajes.apply(
    lambda row: round(row['ingreso_total'] / (row['total_pasajeros'] * row['kms_recorridos']), 4) 
    if row['total_pasajeros'] > 0 and row['kms_recorridos'] > 0 else 0.0, axis=1
)

df_gold_viajes.to_csv('Gold/rendimiento_viajes_gold.csv', index=False)
logging.info(f"Tabla maestra guardada: {len(df_gold_viajes)} registros de viajes.")

# 2. Generar tabla de totales por Unidad
logging.info("Agregando KPIs por Unidad...")
df_kpis_unidades = df_gold_viajes.groupby(['id_unidad', 'placa', 'serie']).agg(
    total_viajes=('id_viaje', 'count'),
    kms_totales=('kms_recorridos', 'sum'),
    combustible_total=('consumo_combustible', 'sum'),
    pasajeros_totales=('total_pasajeros', 'sum'),
    ingresos_totales=('ingreso_total', 'sum')
).reset_index()

df_kpis_unidades['eficiencia_promedio_km_l'] = round(df_kpis_unidades['kms_totales'] / df_kpis_unidades['combustible_total'], 2)
df_kpis_unidades['ingreso_promedio_por_km'] = round(df_kpis_unidades['ingresos_totales'] / df_kpis_unidades['kms_totales'].replace(0, 1), 2)
df_kpis_unidades.to_csv('Gold/kpis_unidades_gold.csv', index=False)
logging.info(f"KPIs por unidad generados: {len(df_kpis_unidades)} unidades.")

# 3. Generar KPIs por Ruta (Origen -> Destino)
logging.info("Agregando KPIs por Ruta...")
df_kpis_rutas = df_gold_viajes.groupby(['origen', 'destino']).agg(
    viajes_realizados=('id_viaje', 'count'),
    pasajeros_totales=('total_pasajeros', 'sum'),
    paquetes_totales=('total_paquetes', 'sum'),
    ingreso_total_acumulado=('ingreso_total', 'sum'),
    kms_promedio=('kms_recorridos', 'mean'),
    combustible_promedio=('consumo_combustible', 'mean')
).reset_index()

df_kpis_rutas['ingreso_promedio_por_km_ruta'] = round(df_kpis_rutas['ingreso_total_acumulado'] / (df_kpis_rutas['viajes_realizados'] * df_kpis_rutas['kms_promedio']), 2)
df_kpis_rutas = df_kpis_rutas.sort_values(by='ingreso_total_acumulado', ascending=False)
df_kpis_rutas.to_csv('Gold/kpis_rutas_gold.csv', index=False)
logging.info(f"KPIs de rutas generados: {len(df_kpis_rutas)} rutas consolidadas.")

# 4. Top de Viajes con mayor ocupación
logging.info("Generando ranking de top viajes con mayor ocupación...")
df_top_ocupacion = df_gold_viajes.sort_values(by='total_pasajeros', ascending=False).head(10)
df_top_ocupacion.to_csv('Gold/top_viajes_ocupacion_gold.csv', index=False)

# 5. Generar KPIs de Fatiga y Rendimiento por Chofer (Horas Semanales - HOS)
logging.info("Calculando horas de servicio (HOS) por chofer a la semana...")

df_gps['inicio_viaje'] = pd.to_datetime(df_gps['fecha_partida'] + ' ' + df_gps['hora_partida'])
df_gps['fin_viaje'] = pd.to_datetime(df_gps['fecha_llegada'] + ' ' + df_gps['hora_llegada'])

# Diferencia en horas
df_gps['duracion_horas'] = (df_gps['fin_viaje'] - df_gps['inicio_viaje']).dt.total_seconds() / 3600.0
# Extraer la semana del año
df_gps['semana_del_anio'] = df_gps['inicio_viaje'].dt.isocalendar().week

df_kpis_choferes = df_gps.groupby(['id_chofer', 'semana_del_anio']).agg(
    total_horas_manejadas=('duracion_horas', 'sum'),
    viajes_realizados=('id_viaje', 'count'),
    kms_totales_manejados=('kms_recorridos', 'sum')
).reset_index()

df_kpis_choferes['total_horas_manejadas'] = round(df_kpis_choferes['total_horas_manejadas'], 2)
df_kpis_choferes.to_csv('Gold/kpis_choferes_gold.csv', index=False)
logging.info(f"KPIs de choferes generados: {len(df_kpis_choferes)} registros semanales consolidados.")

logging.info("=== Capa Gold procesada con éxito ")