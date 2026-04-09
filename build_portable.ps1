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

# Copiar la base de datos actual al paquete portable
$sourceDb = Join-Path $projectRoot 'instance\horarios.db'
$destDb   = Join-Path $portableOutputDir 'instance\horarios.db'
if (Test-Path $sourceDb) {
    Copy-Item $sourceDb $destDb -Force
    Write-Host "Base de datos copiada al paquete portable: $destDb"
} else {
    Write-Warning "No se encontro instance\horarios.db en el proyecto; el ejecutable arrancara con DB vacia."
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
