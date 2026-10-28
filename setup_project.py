import getpass
import logging
import secrets
import string
import sys
from pathlib import Path

import mysql.connector
from serial.tools import list_ports


PROJECT_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = PROJECT_DIR / "schema.sql"
ENV_FILE = PROJECT_DIR / ".env"
DB_NAME = "meteorologia"
DB_HOST = "127.0.0.1"
DB_PORT = 3306

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def ask_serial_port():
    ports = list(list_ports.comports())
    if ports:
        print("\nPuertos serial detectados:")
        for port in ports:
            print(f"  {port.device}: {port.description}")
        default = ports[0].device
    else:
        print("\nNo se detectó una placa serial. Se puede configurar luego en .env.")
        default = "COM3"

    answer = input(f"Puerto serial [{default}]: ").strip()
    return answer or default


def create_database_and_app_user(admin_password):
    connection = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user="root",
        password=admin_password,
        charset="utf8mb4",
    )
    try:
        cursor = connection.cursor()
        for statement in SCHEMA_FILE.read_text(encoding="utf-8").split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)

        app_user = f"meteo_{secrets.token_hex(4)}"
        alphabet = string.ascii_letters + string.digits + "-_"
        app_password = "".join(secrets.choice(alphabet) for _ in range(40))
        cursor.execute(
            f"CREATE USER '{app_user}'@'{DB_HOST}' IDENTIFIED BY %s",
            (app_password,),
        )
        cursor.execute(
            f"GRANT SELECT, INSERT ON {DB_NAME}.* TO '{app_user}'@'{DB_HOST}'"
        )
        cursor.close()
    finally:
        connection.close()

    test_connection = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=app_user,
        password=app_password,
        database=DB_NAME,
        charset="utf8mb4",
    )
    try:
        cursor = test_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM mediciones")
        cursor.fetchone()
        cursor.close()
    finally:
        test_connection.close()
    return app_user, app_password


def main():
    if not SCHEMA_FILE.is_file():
        logger.error("No se encontró el esquema MySQL: %s", SCHEMA_FILE)
        return 1

    if ENV_FILE.exists():
        answer = input(
            "Ya existe .env. ¿Desea reemplazarlo? Escriba S para continuar: "
        ).strip()
        if answer.lower() != "s":
            print("No se realizaron cambios.")
            return 0

    print(
        "Se conectará a MySQL local como root para crear la base y un usuario "
        "limitado de la aplicación."
    )
    print("La contraseña se solicita solo aquí y no se guarda en el proyecto.")
    admin_password = getpass.getpass("Contraseña local de MySQL para root: ")

    try:
        app_user, app_password = create_database_and_app_user(admin_password)
    except mysql.connector.Error:
        logger.exception(
            "No se pudo configurar MySQL. Verifique la contraseña de root "
            "y que MySQL80 esté en ejecución."
        )
        return 1
    except OSError:
        logger.exception("No se pudo leer el esquema de MySQL.")
        return 1
    finally:
        admin_password = ""

    serial_port = ask_serial_port()
    env_values = {
        "DB_HOST": DB_HOST,
        "DB_PORT": str(DB_PORT),
        "DB_USER": app_user,
        "DB_PASSWORD": app_password,
        "DB_NAME": DB_NAME,
        "SERIAL_PORT": serial_port,
        "SERIAL_BAUDRATE": "9600",
        "WEB_HOST": "127.0.0.1",
        "WEB_PORT": "5000",
        "LOG_LEVEL": "INFO",
    }

    try:
        ENV_FILE.write_text(
            "".join(f"{key}={value}\n" for key, value in env_values.items()),
            encoding="utf-8",
        )
    except OSError:
        logger.exception(
            "No se pudo guardar .env. El usuario MySQL %s ya fue creado; "
            "no comparta su contraseña.",
            app_user,
        )
        return 1

    print("\nMySQL quedó configurado y la conexión de la aplicación fue verificada.")
    print(f"Base de datos: {DB_NAME}")
    print(f"Usuario limitado de la aplicación: {app_user}")
    print(f"Configuración guardada en: {ENV_FILE}")
    print(
        f"Puerto serial configurado: {serial_port}. "
        "Conecte la placa y confirme que use 9600 baudios."
    )
    print("\nEn dos terminales, ejecute:")
    print("  .\\.venv\\Scripts\\python.exe serial_reader.py")
    print("  .\\.venv\\Scripts\\python.exe app.py")
    print("Luego abra http://127.0.0.1:5000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
