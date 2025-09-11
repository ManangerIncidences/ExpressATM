# ExpressATM - Actualizador de ChromeDriver PowerShell
# Versión más robusta para sistemas modernos

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ExpressATM - Actualización ChromeDriver" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Crear directorio drivers si no existe
if (!(Test-Path "drivers")) {
    New-Item -ItemType Directory -Path "drivers" | Out-Null
}

Write-Host "🔍 Detectando versión de Chrome instalada..." -ForegroundColor Yellow

# Buscar Chrome en ubicaciones comunes
$chromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe", 
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromePath = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromePath = $path
        break
    }
}

if (-not $chromePath) {
    Write-Host "❌ Google Chrome no encontrado" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 SOLUCIÓN:" -ForegroundColor Yellow
    Write-Host "1. Instalar Google Chrome desde: https://www.google.com/chrome/"
    Write-Host "2. Ejecutar este script nuevamente"
    Write-Host ""
    Read-Host "Presiona Enter para continuar"
    exit 1
}

Write-Host "✅ Chrome encontrado en: $chromePath" -ForegroundColor Green

try {
    # Obtener versión de Chrome
    $chromeVersion = (Get-ItemProperty $chromePath).VersionInfo.ProductVersion
    Write-Host "✅ Versión de Chrome detectada: $chromeVersion" -ForegroundColor Green
    
    $chromeMajor = $chromeVersion.Split('.')[0]
    Write-Host "📍 Versión principal: $chromeMajor" -ForegroundColor Cyan
    
} catch {
    Write-Host "⚠️ No se pudo detectar la versión de Chrome automáticamente" -ForegroundColor Yellow
    Write-Host "💡 Usando versión más reciente disponible..." -ForegroundColor Yellow
    $chromeMajor = "119"
}

Write-Host ""
Write-Host "📥 Descargando ChromeDriver compatible..." -ForegroundColor Yellow

try {
    # URL de la API de ChromeDriver
    $latestUrl = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$chromeMajor"
    
    Write-Host "🔄 Obteniendo versión exacta de ChromeDriver..." -ForegroundColor Cyan
    $latestVersion = Invoke-RestMethod -Uri $latestUrl -ErrorAction Stop
    Write-Host "📌 Versión ChromeDriver: $latestVersion" -ForegroundColor Green
    
    # URL de descarga
    $downloadUrl = "https://chromedriver.storage.googleapis.com/$latestVersion/chromedriver_win32.zip"
    $zipPath = "drivers\chromedriver.zip"
    
    Write-Host "🔄 Descargando de: $downloadUrl" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -ErrorAction Stop
    Write-Host "✅ Descarga completada" -ForegroundColor Green
    
} catch {
    Write-Host "❌ Error descargando ChromeDriver automáticamente: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 DESCARGA MANUAL:" -ForegroundColor Yellow
    Write-Host "1. Ir a: https://chromedriver.chromium.org/downloads"
    Write-Host "2. Descargar versión compatible con Chrome $chromeMajor"
    Write-Host "3. Extraer chromedriver.exe en carpeta: drivers\"
    Write-Host ""
    Read-Host "Presiona Enter para continuar"
    exit 1
}

Write-Host ""
Write-Host "📂 Extrayendo ChromeDriver..." -ForegroundColor Yellow

try {
    # Eliminar chromedriver existente
    if (Test-Path "drivers\chromedriver.exe") {
        Remove-Item "drivers\chromedriver.exe" -Force
    }
    
    # Extraer archivo ZIP
    Expand-Archive -Path "drivers\chromedriver.zip" -DestinationPath "drivers\" -Force
    Write-Host "✅ Extracción completada" -ForegroundColor Green
    
    # Limpiar archivo ZIP
    Remove-Item "drivers\chromedriver.zip" -Force
    
} catch {
    Write-Host "❌ Error extrayendo archivo ZIP: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Extrae manualmente chromedriver.zip en carpeta drivers\" -ForegroundColor Yellow
    Read-Host "Presiona Enter para continuar"
    exit 1
}

# Verificar instalación
if (Test-Path "drivers\chromedriver.exe") {
    Write-Host ""
    Write-Host "✅ ChromeDriver instalado exitosamente" -ForegroundColor Green
    Write-Host "📍 Ubicación: drivers\chromedriver.exe" -ForegroundColor Cyan
    
    # Verificar versión de ChromeDriver
    Write-Host ""
    Write-Host "🔍 Verificando versión de ChromeDriver..." -ForegroundColor Yellow
    try {
        $chromedriverVersion = & "drivers\chromedriver.exe" --version 2>$null
        Write-Host "✅ $chromedriverVersion" -ForegroundColor Green
        Write-Host "✅ ChromeDriver funcional" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ ChromeDriver instalado pero puede tener problemas" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Error: ChromeDriver no se instaló correctamente" -ForegroundColor Red
    Read-Host "Presiona Enter para continuar"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ CHROMEDRIVER ACTUALIZADO EXITOSAMENTE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "🎉 ExpressATM ya puede realizar scraping" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Para probar:" -ForegroundColor Cyan
Write-Host "   run.bat" -ForegroundColor White
Write-Host ""
Read-Host "Presiona Enter para continuar"
