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
$existingPortableModels = Join-Path $projectRoot 'dist\HorariosUABCPortable\instance\ollama_models'
$preservedModelsDir = Join-Path $projectRoot '.tmp_portable_ollama_models'
if (Test-Path $preservedModelsDir) { Remove-Item $preservedModelsDir -Recurse -Force }
if (Test-Path $existingPortableModels) {
    Move-Item $existingPortableModels $preservedModelsDir
}
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
$portableOllamaDir = Join-Path $portableOutputDir 'ollama'
$portableInstanceDir = Join-Path $portableOutputDir 'instance\ollama_models'

New-Item -ItemType Directory -Force -Path $portableOllamaDir | Out-Null
New-Item -ItemType Directory -Force -Path $portableInstanceDir | Out-Null

if (Test-Path $preservedModelsDir) {
    Copy-Item (Join-Path $preservedModelsDir '*') $portableInstanceDir -Recurse -Force
    Remove-Item $preservedModelsDir -Recurse -Force
    Write-Host "Modelos portables preservados en: $portableInstanceDir"
}

$localOllamaExe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
if (Test-Path $localOllamaExe) {
    Copy-Item $localOllamaExe (Join-Path $portableOllamaDir 'ollama.exe') -Force
    Write-Host "Ollama copiado al paquete portable: $portableOllamaDir\\ollama.exe"
} else {
    Write-Warning 'No se encontro ollama.exe local; el paquete portable requerira copiarlo manualmente en dist\HorariosUABCPortable\ollama\ollama.exe'
}

$portableSetupScript = Join-Path $projectRoot 'portable_ai_setup.ps1'
if (Test-Path $portableSetupScript) {
    Copy-Item $portableSetupScript (Join-Path $portableOutputDir 'portable_ai_setup.ps1') -Force
}

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
