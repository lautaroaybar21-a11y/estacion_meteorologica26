$ErrorActionPreference = "Stop"

$base = "C:\Program Files\MySQL\MySQL Server 8.0"
$data = Join-Path $env:LOCALAPPDATA "MeteorologiaMySQL\data"
$mysqld = Join-Path $base "bin\mysqld.exe"
$port = 3307

if (-not (Test-Path $mysqld)) {
    throw "No se encontró MySQL Server en $mysqld."
}
if (-not (Test-Path (Join-Path $data "mysql"))) {
    throw "No se encontró el directorio de datos de la estación: $data"
}

$connection = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
if ($connection.TcpTestSucceeded) {
    Write-Output "MySQL de meteorologia ya está activo en 127.0.0.1:$port."
    exit 0
}

$stdout = Join-Path $env:LOCALAPPDATA "MeteorologiaMySQL\server.out.log"
$stderr = Join-Path $env:LOCALAPPDATA "MeteorologiaMySQL\server.err.log"
$arguments = @(
    "--no-defaults",
    "--basedir=`"$base`"",
    "--datadir=`"$data`"",
    "--port=$port",
    "--bind-address=127.0.0.1",
    "--mysqlx=0"
)

$process = Start-Process `
    -FilePath $mysqld `
    -ArgumentList $arguments `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Seconds 1
    if ($process.HasExited) {
        $details = if (Test-Path $stderr) { Get-Content $stderr -Raw } else { "Sin detalles adicionales." }
        throw "MySQL terminó al iniciar. $details"
    }

    $connection = Test-NetConnection 127.0.0.1 -Port $port -WarningAction SilentlyContinue
    if ($connection.TcpTestSucceeded) {
        Write-Output "MySQL de meteorologia activo en 127.0.0.1:$port."
        exit 0
    }
}

throw "MySQL sigue ejecutándose (PID $($process.Id)), pero el puerto $port no respondió. Revise $stderr."
