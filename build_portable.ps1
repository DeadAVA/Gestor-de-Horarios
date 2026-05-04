$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Error "No se encontro Python del entorno virtual en .venv\Scripts\python.exe"
}

& $python -m pip install --upgrade pip
& $python -m pip install pyinstaller waitress

$distDir = Join-Path $projectRoot 'dist'
$buildDir = Join-Path $projectRoot 'build'
if (Test-Path $distDir) { Remove-Item $distDir -Recurse -Force }
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }

$iconCandidates = @(
    (Join-Path $projectRoot 'app_ico.ico'),
    (Join-Path $projectRoot 'app_icon.ico')
)

$iconPath = $null
foreach ($candidate in $iconCandidates) {
    if (Test-Path $candidate) {
        $iconPath = $candidate
        break
    }
}

$pyInstallerArgs = @(
    '--noconfirm',
    '--clean',
    '--name', 'HorariosUABCPortable',
    '--onedir',
    '--add-data', 'app\templates;app\templates',
    '--add-data', 'app\assets;app\assets'
)

if ($iconPath) {
    $pyInstallerArgs += @('--icon', $iconPath)
    Write-Host "Usando icono: $iconPath"
} else {
    Write-Warning 'No se encontro app_ico.ico ni app_icon.ico; se generara sin icono personalizado.'
}

$pyInstallerArgs += 'portable_launcher.py'

& $python -m PyInstaller @pyInstallerArgs

$portableOutputDir = Join-Path $projectRoot 'dist\HorariosUABCPortable'

# Copiar la base de datos actual al paquete portable.
# Usamos backup de SQLite para obtener un snapshot consistente incluso con WAL.
$sourceDb = Join-Path $projectRoot 'instance\horarios.db'
$destDb   = Join-Path $portableOutputDir 'instance\horarios.db'
if (Test-Path $sourceDb) {
    $destInstanceDir = Split-Path -Parent $destDb
    if (-not (Test-Path $destInstanceDir)) {
        New-Item -ItemType Directory -Path $destInstanceDir -Force | Out-Null
    }

    $backupCode = @"
import sqlite3
from pathlib import Path

source_db = Path(r'''$sourceDb''')
dest_db = Path(r'''$destDb''')

if source_db.exists():
    if dest_db.exists():
        dest_db.unlink()

    source_conn = sqlite3.connect(source_db)
    try:
        source_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        dest_conn = sqlite3.connect(dest_db)
        try:
            source_conn.backup(dest_conn)
            dest_conn.commit()
        finally:
            dest_conn.close()
    finally:
        source_conn.close()
"@
    & $python -c $backupCode
    Write-Host "Base de datos copiada al paquete portable: $destDb"
} else {
    Write-Warning "No se encontro instance\horarios.db en el proyecto; el ejecutable arrancara con DB vacia."
}

$sourceLocks = Join-Path $projectRoot 'instance\candados.json'
$destLocks = Join-Path $portableOutputDir 'instance\candados.json'
if (Test-Path $sourceLocks) {
    Copy-Item $sourceLocks $destLocks -Force
    Write-Host "Candados copiados al paquete portable: $destLocks"
}

# Crear launcher VBScript (sin ventana CMD)
$vbsContent = @'
Set oShell = CreateObject("WScript.Shell")
Dim exePath
exePath = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")) & "HorariosUABCPortable.exe"
oShell.Run Chr(34) & exePath & Chr(34), 0, False
Set oShell = Nothing
'@
$vbsContent | Set-Content (Join-Path $portableOutputDir 'Iniciar_HorariosUABC.vbs') -Encoding UTF8

Write-Host "Build terminado. Ejecutable en dist\HorariosUABCPortable\HorariosUABCPortable.exe"
Write-Host "Usa Iniciar_HorariosUABC.vbs para abrir sin ventana CMD."
