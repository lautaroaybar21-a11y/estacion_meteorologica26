# Estación meteorológica

Aplicación local que recibe las lecturas de una placa por puerto serial, las guarda en MySQL y muestra el historial y su evolución en una página web.

## Datos guardados

- Temperatura del sensor BMP (°C)
- Presión atmosférica (hPa)
- Temperatura del sensor DHT (°C)
- Humedad relativa del aire (%)
- Humedad del suelo RAW y su conversión a porcentaje
- Fecha y hora informadas por la placa

La conversión de humedad del suelo usa la calibración indicada:

```text
humedad (%) = (1023 - RAW) * 100 / (1023 - 300)
```

El resultado se limita al intervalo 0–100 %. Por ejemplo, RAW 1023 equivale a 0 % y RAW 300 a 100 %.

## Requisitos

- Python 3.10 o superior
- MySQL Server local
- La placa conectada por USB/serial

## Instalación en Windows

1. Abra PowerShell en esta carpeta y cree un entorno virtual:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Ejecute el asistente de configuración:

   ```powershell
   .\.venv\Scripts\python.exe setup_project.py
   ```

   El asistente solicita la contraseña local de `root` sin mostrarla ni guardarla. Crea la base y la tabla a partir de `schema.sql`, genera un usuario MySQL limitado a leer e insertar mediciones, verifica ese acceso y escribe sus credenciales en `.env` (archivo ignorado por Git). Si la placa está conectada, selecciona un puerto serial detectado; si todavía no lo está, usa `COM3` como valor inicial para cambiarlo después.

   El ejemplo usa `9600` baudios; debe coincidir con la configuración del microcontrolador. El servidor MySQL, el equipo que ejecuta la aplicación y la placa deben usar la misma hora local para alinear los gráficos.

## Ejecución

Abra dos terminales en la carpeta del proyecto, active el entorno virtual en ambas y ejecute:

```powershell
python serial_reader.py
```

En la segunda terminal:

```powershell
python app.py
```

Luego visite <http://127.0.0.1:5000>. Mantenga abierta la terminal del lector serial mientras quiera registrar datos. El lector reintenta la conexión serial si el puerto se desconecta y reintenta tres veces cada escritura de MySQL; los fallos se muestran en la consola.

En este equipo se creó una instancia MySQL independiente en el puerto `3307`; no reemplaza ni modifica el servicio MySQL existente del puerto `3306`. La contraseña administrativa `123` se configuró solo para esa instancia local, que escucha únicamente en `127.0.0.1`. La aplicación usa otro usuario, con permiso limitado a leer e insertar mediciones. La base está en `%LOCALAPPDATA%\MeteorologiaMySQL\data` y el `.env` contiene las credenciales de la aplicación.

Si MySQL no está activo después de reiniciar Windows, inicie la instancia de la estación con:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_mysql.ps1
```

El esquema y el acceso de la aplicación ya se crearon y verificaron. El directorio de datos está fuera del repositorio y no se sincroniza con Git. Antes de ejecutar `setup_project.py` para otra instalación, tenga en cuenta que el asistente configura un servidor MySQL ya accesible; no es necesario ejecutarlo para la instancia creada en este equipo.

## Formato serial

El lector espera bloques con los rótulos `Fecha`, `Hora`, `Temperatura BMP`, `Presion`, `Temperatura DHT`, `Humedad del aire` y `Humedad suelo RAW`, como en el ejemplo proporcionado. Una lectura se guarda cuando están presentes todos esos campos.

## Panel web

- Cinco tarjetas muestran la última lectura guardada y la fecha de esa lectura.
- Historial paginado de 25 mediciones por página.
- Un gráfico permite seleccionar cualquiera de las cinco variables medidas.
- Selector de últimas 24 horas, 7 días, 30 días o todo el historial.
- El gráfico muestra como máximo las 1000 mediciones más recientes del período seleccionado.
- El historial y los gráficos se actualizan automáticamente cada 30 segundos.
- Si no hay datos, el panel lo informa claramente en vez de dibujar escalas vacías.
- Los gráficos cargan Chart.js desde un CDN y requieren conexión a Internet en el navegador.

## Pruebas

```powershell
python -m unittest
```
