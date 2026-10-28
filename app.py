import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import mysql.connector

from database import get_connection

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = Flask(__name__)

PAGE_SIZE = 25
CHART_LIMIT = 1000
PERIODS = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def serialize_measurement(row):
    row["medido_en"] = row["medido_en"].isoformat(sep=" ")
    for key, value in row.items():
        if isinstance(value, Decimal):
            row[key] = float(value)
    return row


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/mediciones")
def measurements():
    try:
        page = int(request.args.get("pagina", "1"))
    except ValueError:
        return jsonify({"error": "La página debe ser un número entero."}), 400

    if page < 1:
        return jsonify({"error": "La página debe ser mayor que cero."}), 400

    try:
        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT COUNT(*) AS total FROM mediciones")
            total = cursor.fetchone()["total"]
            cursor.execute(
                """
                SELECT medido_en, temperatura_bmp, temperatura_dht,
                       humedad_aire, presion_hpa, humedad_suelo_raw,
                       humedad_suelo_pct
                FROM mediciones
                ORDER BY medido_en DESC, id DESC
                LIMIT 1
                """
            )
            latest = cursor.fetchone()
            if latest is not None:
                latest = serialize_measurement(latest)
            cursor.execute(
                """
                SELECT id, medido_en, temperatura_bmp, temperatura_dht,
                       humedad_aire, presion_hpa, humedad_suelo_raw,
                       humedad_suelo_pct
                FROM mediciones
                ORDER BY medido_en DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (PAGE_SIZE, (page - 1) * PAGE_SIZE),
            )
            rows = [serialize_measurement(row) for row in cursor.fetchall()]
            cursor.close()
        finally:
            connection.close()
        return jsonify(
            {
                "mediciones": rows,
                "pagina": page,
                "por_pagina": PAGE_SIZE,
                "total": total,
                "paginas": (total + PAGE_SIZE - 1) // PAGE_SIZE,
                "ultima": latest,
            }
        )
    except mysql.connector.Error:
        logger.exception("No se pudo consultar el historial de mediciones.")
        return (
            jsonify(
                {
                    "error": (
                        "No se pudo conectar a MySQL. Verifique DB_HOST, DB_PORT, "
                        "DB_USER, DB_PASSWORD y DB_NAME en el archivo .env."
                    )
                }
            ),
            503,
        )


@app.get("/api/mediciones/grafico")
def chart_measurements():
    period = request.args.get("periodo", "24h")
    if period not in (*PERIODS.keys(), "todo"):
        return jsonify({"error": "Período inválido. Use 24h, 7d, 30d o todo."}), 400

    try:
        connection = get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            sql = """
                SELECT medido_en, temperatura_bmp, temperatura_dht,
                       humedad_aire, presion_hpa, humedad_suelo_pct
                FROM mediciones
            """
            params = ()
            if period != "todo":
                cutoff = datetime.now() - PERIODS[period]
                sql += " WHERE medido_en >= %s"
                params = (cutoff,)
            sql += " ORDER BY medido_en DESC LIMIT %s"
            cursor.execute(sql, (*params, CHART_LIMIT))
            rows = cursor.fetchall()
            cursor.close()
        finally:
            connection.close()
        rows.reverse()
        return jsonify(
            {
                "mediciones": [serialize_measurement(row) for row in rows],
                "maximo_puntos": CHART_LIMIT,
            }
        )
    except mysql.connector.Error:
        logger.exception("No se pudieron consultar los datos para el gráfico.")
        return (
            jsonify(
                {
                    "error": (
                        "No se pudo conectar a MySQL. Verifique DB_HOST, DB_PORT, "
                        "DB_USER, DB_PASSWORD y DB_NAME en el archivo .env."
                    )
                }
            ),
            503,
        )


if __name__ == "__main__":
    app.run(
        host=os.getenv("WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("WEB_PORT", "5000")),
        debug=False,
    )
