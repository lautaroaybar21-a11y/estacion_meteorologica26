import logging
import os
import re
import time
from datetime import datetime

import mysql.connector
import serial
from dotenv import load_dotenv

from database import get_connection

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

FIELD_PATTERNS = {
    "fecha_hora": re.compile(
        r"Fecha:\s*(\d{4}-\d{2}-\d{2})\s+Hora:\s*(\d{2}:\d{2}:\d{2})",
        re.IGNORECASE,
    ),
    "temperatura_bmp": re.compile(
        r"Temperatura BMP:\s*(-?\d+(?:[.,]\d+)?)\s*C", re.IGNORECASE
    ),
    "presion_hpa": re.compile(
        r"Presion:\s*(-?\d+(?:[.,]\d+)?)\s*hPa", re.IGNORECASE
    ),
    "temperatura_dht": re.compile(
        r"Temperatura DHT:\s*(-?\d+(?:[.,]\d+)?)\s*C", re.IGNORECASE
    ),
    "humedad_aire": re.compile(
        r"Humedad del aire:\s*(-?\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE
    ),
    "humedad_suelo_raw": re.compile(
        r"Humedad suelo RAW:\s*(\d+)", re.IGNORECASE
    ),
}
REQUIRED_FIELDS = set(FIELD_PATTERNS)


def soil_humidity_percent(raw_value):
    if not 0 <= raw_value <= 1023:
        raise ValueError("La lectura RAW del suelo debe estar entre 0 y 1023.")
    return round(max(0.0, min(100.0, (1023 - raw_value) * 100 / (1023 - 300))), 2)


def parse_reading_line(line, pending):
    if "NUEVA LECTURA" in line.upper():
        if pending:
            missing = REQUIRED_FIELDS.difference(pending)
            logger.warning(
                "Bloque serial incompleto; faltan los campos: %s",
                ", ".join(sorted(missing)),
            )
        pending.clear()
        return None

    for field, pattern in FIELD_PATTERNS.items():
        match = pattern.search(line)
        if not match:
            continue
        if field == "fecha_hora":
            pending[field] = datetime.strptime(
                f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H:%M:%S"
            )
        elif field == "humedad_suelo_raw":
            pending[field] = int(match.group(1))
        else:
            pending[field] = float(match.group(1).replace(",", "."))
        break

    if REQUIRED_FIELDS.issubset(pending):
        if not 0 <= pending["humedad_suelo_raw"] <= 1023:
            raise ValueError("La lectura RAW del suelo debe estar entre 0 y 1023.")
        reading = {
            **pending,
            "humedad_suelo_pct": soil_humidity_percent(
                pending["humedad_suelo_raw"]
            ),
        }
        pending.clear()
        return reading
    return None


def save_reading(reading):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO mediciones (
                medido_en, temperatura_bmp, presion_hpa, temperatura_dht,
                humedad_aire, humedad_suelo_raw, humedad_suelo_pct
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                reading["fecha_hora"],
                reading["temperatura_bmp"],
                reading["presion_hpa"],
                reading["temperatura_dht"],
                reading["humedad_aire"],
                reading["humedad_suelo_raw"],
                reading["humedad_suelo_pct"],
            ),
        )
        connection.commit()
        cursor.close()
    finally:
        connection.close()


def run():
    port = os.getenv("SERIAL_PORT", "COM3")
    baud_rate = int(os.getenv("SERIAL_BAUDRATE", "9600"))
    pending = {}
    logger.info("Escuchando el puerto serial %s a %s baudios.", port, baud_rate)

    while True:
        try:
            with serial.Serial(port, baud_rate, timeout=1) as device:
                logger.info("Puerto serial conectado.")
                while True:
                    line = device.readline().decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        reading = parse_reading_line(line, pending)
                    except (ValueError, OverflowError):
                        logger.exception("Lectura serial inválida: %s", line)
                        pending.clear()
                        continue
                    if reading:
                        for attempt in range(1, 4):
                            try:
                                save_reading(reading)
                                logger.info(
                                    "Medición guardada: %s (suelo %.2f%%).",
                                    reading["fecha_hora"],
                                    reading["humedad_suelo_pct"],
                                )
                                break
                            except mysql.connector.Error:
                                logger.exception(
                                    "Error guardando medición (intento %s/3).",
                                    attempt,
                                )
                                if attempt == 3:
                                    logger.error(
                                        "Medición descartada tras tres intentos: %s",
                                        reading["fecha_hora"],
                                    )
                                else:
                                    time.sleep(2)
        except (serial.SerialException, OSError) as error:
            logger.error("No se pudo leer %s: %s. Reintento en 5 segundos.", port, error)
            time.sleep(5)


if __name__ == "__main__":
    run()
