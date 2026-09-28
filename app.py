from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

app = Flask(__name__)

# ==========================================
# RUTAS DEL PROYECTO
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOLD_DIR = os.path.join(BASE_DIR, "Gold")

# Verificación de rutas
print("BASE_DIR:", BASE_DIR)
print("GOLD_DIR:", GOLD_DIR)


@app.route("/")
def dashboard():

    try:

        # ==========================================
        # CARGAR DATOS DE LA CAPA GOLD
        # ==========================================

        df_viajes = pd.read_csv(
            os.path.join(
                GOLD_DIR,
                "rendimiento_viajes_gold.csv"
            )
        )

        df_unidades = pd.read_csv(
            os.path.join(
                GOLD_DIR,
                "kpis_unidades_gold.csv"
            )
        )

        df_rutas = pd.read_csv(
            os.path.join(
                GOLD_DIR,
                "kpis_rutas_gold.csv"
            )
        )

        df_top_pax = pd.read_csv(
            os.path.join(
                GOLD_DIR,
                "top_viajes_ocupacion_gold.csv"
            )
        )

    except Exception as e:

        return f"""
        <h2>Error al cargar los datos de la Capa Gold</h2>

        <p>
            <strong>Directorio buscado:</strong>
            {GOLD_DIR}
        </p>

        <p>
            <strong>Detalle:</strong>
            {e}
        </p>
        """


    # ==========================================
    # PREPARAR RUTAS
    # ==========================================

    # Crear nombre del trayecto
    # Ejemplo:
    # BUCERÍAS → GUADALAJARA

    df_rutas["ruta"] = (
        df_rutas["origen"].astype(str)
        + " → "
        + df_rutas["destino"].astype(str)
    )


    # Ordenar de mayor a menor ingreso

    df_rutas = df_rutas.sort_values(
        "ingreso_total_acumulado",
        ascending=False
    )


    # Convertir rutas a registros para JavaScript

    rutas_records = df_rutas[
        [
            "ruta",
            "origen",
            "destino",
            "viajes_realizados",
            "pasajeros_totales",
            "paquetes_totales",
            "ingreso_total_acumulado",
            "kms_promedio",
            "combustible_promedio",
            "ingreso_promedio_por_km_ruta"
        ]
    ].to_dict(
        orient="records"
    )


    # ==========================================
    # PREPARAR UNIDADES
    # ==========================================

    # Consumo promedio de combustible por viaje

    df_unidades["consumo_promedio_por_viaje"] = (
        df_unidades["combustible_total"]
        /
        df_unidades["total_viajes"]
    )


    # Ordenar de mayor a menor consumo

    df_unidades = df_unidades.sort_values(
        "consumo_promedio_por_viaje",
        ascending=False
    )


    # Convertir unidades a registros
    # para enviarlas al HTML

    unidades_records = df_unidades[
        [
            "id_unidad",
            "placa",
            "total_viajes",
            "combustible_total",
            "consumo_promedio_por_viaje",
            "eficiencia_promedio_km_l",
            "ingresos_totales"
        ]
    ].to_dict(
        orient="records"
    )


    # ==========================================
    # 1. KPIs GENERALES
    # ==========================================

    total_ingresos = float(
        df_viajes["ingreso_total"].sum()
    )


    total_pasajeros = int(
        df_viajes["total_pasajeros"].sum()
    )


    total_kms = float(
        df_viajes["kms_recorridos"].sum()
    )


    total_combustible = float(
        df_viajes["consumo_combustible"].sum()
    )


    eficiencia_global = (
        round(
            total_kms / total_combustible,
            2
        )
        if total_combustible > 0
        else 0.0
    )


    # ==========================================
    # 2. GRÁFICA DE RUTAS
    # ==========================================

    fig_rutas = px.bar(

        df_rutas.head(5),

        x="ingreso_total_acumulado",

        y="origen",

        color="destino",

        orientation="h",

        title="Top Rutas por Ingreso Acumulado ($)",

        labels={
            "ingreso_total_acumulado":
                "Ingreso Total ($)",

            "origen":
                "Origen"
        },

        template="plotly_white"
    )


    fig_rutas.update_layout(

        margin=dict(
            t=40,
            b=20,
            l=20,
            r=20
        ),

        height=350
    )


    graph_rutas_html = pio.to_html(

        fig_rutas,

        full_html=False
    )


    # ==========================================
    # 3. GRÁFICA DE EFICIENCIA
    # ==========================================

    fig_unidades = px.bar(

        df_unidades,

        x="id_unidad",

        y="eficiencia_promedio_km_l",

        color="eficiencia_promedio_km_l",

        title="Eficiencia Promedio (Km/L) por Unidad",

        labels={

            "id_unidad":
                "Unidad ID",

            "eficiencia_promedio_km_l":
                "Km / Litro"
        },

        template="plotly_white"
    )


    fig_unidades.update_layout(

        margin=dict(
            t=40,
            b=20,
            l=20,
            r=20
        ),

        height=350
    )


    graph_unidades_html = pio.to_html(

        fig_unidades,

        full_html=False
    )


    # ==========================================
    # 4. TOP 10 VIAJES
    # ==========================================

    top_viajes_records = df_top_pax[
        [
            "id_viaje",
            "id_unidad",
            "origen",
            "destino",
            "total_pasajeros",
            "ingreso_total",
            "km_por_litro"
        ]
    ].to_dict(
        orient="records"
    )


    # ==========================================
    # 5. ENVIAR TODO AL HTML
    # ==========================================

    return render_template(

        "index.html",

        # KPIs
        total_ingresos=
            f"${total_ingresos:,.2f}",

        total_pasajeros=
            f"{total_pasajeros:,}",

        total_kms=
            f"{total_kms:,.1f} km",

        eficiencia_global=
            f"{eficiencia_global} km/L",


        # Gráficas
        graph_rutas=
            graph_rutas_html,

        graph_unidades=
            graph_unidades_html,


        # Tabla
        top_viajes=
            top_viajes_records,


        # NUEVO:
        # Datos para dropdown de rutas
        rutas=
            rutas_records,


        # NUEVO:
        # Datos para dropdown de unidades
        unidades=
            unidades_records
    )


# ==========================================
# EJECUTAR FLASK
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000
    )