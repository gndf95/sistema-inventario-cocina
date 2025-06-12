@echo off
chcp 65001 >nul
echo ================================================
echo   Setup GitHub - Sistema de Inventario Cocina
echo ================================================
echo.

cd /d "%~dp0"

echo ✅ Git detectado: 
git --version
echo.

echo Verificando configuración de Git...
git config --global user.name >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  Git no está configurado. Vamos a configurarlo:
    echo.
    set /p git_name="Ingresa tu nombre completo: "
    set /p git_email="Ingresa tu email: "
    
    git config --global user.name "!git_name!"
    git config --global user.email "!git_email!"
    
    echo ✅ Git configurado correctamente
    echo.
)

echo Configuración actual de Git:
echo Nombre: 
git config --global user.name
echo Email: 
git config --global user.email
echo.

echo Creando archivos necesarios para GitHub...
echo.

REM Crear .gitignore
echo # Base de datos (no subir datos reales^) > .gitignore
echo *.db >> .gitignore
echo *.sqlite >> .gitignore
echo *.sqlite3 >> .gitignore
echo. >> .gitignore
echo # Archivos de Python >> .gitignore
echo __pycache__/ >> .gitignore
echo *.py[cod] >> .gitignore
echo *$py.class >> .gitignore
echo *.so >> .gitignore
echo .Python >> .gitignore
echo build/ >> .gitignore
echo develop-eggs/ >> .gitignore
echo dist/ >> .gitignore
echo downloads/ >> .gitignore
echo eggs/ >> .gitignore
echo .eggs/ >> .gitignore
echo lib/ >> .gitignore
echo lib64/ >> .gitignore
echo parts/ >> .gitignore
echo sdist/ >> .gitignore
echo var/ >> .gitignore
echo wheels/ >> .gitignore
echo *.egg-info/ >> .gitignore
echo .installed.cfg >> .gitignore
echo *.egg >> .gitignore
echo. >> .gitignore
echo # Entornos virtuales >> .gitignore
echo venv/ >> .gitignore
echo env/ >> .gitignore
echo ENV/ >> .gitignore
echo .venv/ >> .gitignore
echo. >> .gitignore
echo # Archivos del sistema >> .gitignore
echo .DS_Store >> .gitignore
echo Thumbs.db >> .gitignore
echo *.log >> .gitignore
echo. >> .gitignore
echo # Configuraciones locales >> .gitignore
echo config_local.py >> .gitignore
echo .env >> .gitignore
echo. >> .gitignore
echo # Archivos temporales >> .gitignore
echo *.tmp >> .gitignore
echo *.temp >> .gitignore
echo. >> .gitignore
echo # Carpetas de imágenes QR generadas >> .gitignore
echo qr_codes/ >> .gitignore
echo uploads/ >> .gitignore
echo. >> .gitignore
echo # Archivos de backup >> .gitignore
echo *.bak >> .gitignore
echo *.backup >> .gitignore

echo ✅ Archivo .gitignore creado

REM Verificar si requirements.txt ya existe
if exist "requirements.txt" (
    echo ✅ requirements.txt ya existe - mantiendo el archivo actual
    echo Contenido actual:
    type requirements.txt
) else (
    echo Creando requirements.txt...
    echo Flask==2.3.2 > requirements.txt
    echo Flask-SQLAlchemy==3.0.5 >> requirements.txt
    echo Flask-Login==0.6.2 >> requirements.txt
    echo Flask-WTF==1.1.1 >> requirements.txt
    echo qrcode[pil]==7.4.2 >> requirements.txt
    echo python-dotenv==1.0.0 >> requirements.txt
    echo Werkzeug==2.3.6 >> requirements.txt
    echo reportlab==4.0.4 >> requirements.txt
    echo ✅ Archivo requirements.txt creado
)

REM Crear un README básico
echo # 🍳 Sistema de Inventario y Préstamo de Equipo Menor de Cocina > README.md
echo. >> README.md
echo Sistema web desarrollado en Flask para gestionar el inventario, préstamos y devoluciones de equipo menor de cocina. >> README.md
echo. >> README.md
echo ## 🚀 Instalación Rápida >> README.md
echo. >> README.md
echo 1. Clonar el repositorio >> README.md
echo 2. Instalar dependencias: `pip install -r requirements.txt` >> README.md
echo 3. Ejecutar: `python app.py` >> README.md
echo 4. Abrir navegador en: `http://localhost:5000` >> README.md
echo. >> README.md
echo ## 📱 Características >> README.md
echo. >> README.md
echo - ✅ Gestión de inventario con códigos QR >> README.md
echo - ✅ Sistema de préstamos y devoluciones >> README.md
echo - ✅ Dashboard responsivo para móviles >> README.md
echo - ✅ Alertas de stock bajo y préstamos vencidos >> README.md
echo - ✅ Funciona en red local >> README.md

echo ✅ Archivo README.md creado

echo.
echo ================================================
echo   Archivos preparados para GitHub
echo ================================================
echo.
echo Archivos creados:
echo ✅ .gitignore
echo ✅ requirements.txt  
echo ✅ README.md
echo.
echo SIGUIENTE PASO:
echo 1. Ve a GitHub.com e inicia sesión
echo 2. Crea un nuevo repositorio llamado: sistema-inventario-cocina
echo 3. Copia la URL del repositorio
echo 4. Ejecuta el script: subir_a_github.bat
echo.
echo ¿Listo para continuar? Presiona cualquier tecla...
pause >nul

echo.
echo ================================================
echo        Subiendo proyecto a GitHub
echo ================================================
echo.

if not exist ".git" (
    echo Inicializando repositorio Git...
    git init
    echo ✅ Repositorio Git inicializado
    echo.
)

echo Agregando archivos al repositorio...
git add .
echo ✅ Archivos agregados

echo.
echo Creando primer commit...
git commit -m "Primera versión - Sistema de Inventario de Equipo de Cocina"
echo ✅ Commit creado

echo.
echo ================================================
echo      CONFIGURACIÓN DEL REPOSITORIO REMOTO
echo ================================================
echo.
echo IMPORTANTE: Necesitas crear el repositorio en GitHub primero
echo.
echo 1. Ve a: https://github.com
echo 2. Haz clic en el botón verde "New" (nuevo repositorio)
echo 3. Nombre del repositorio: sistema-inventario-cocina
echo 4. Descripción: Sistema de inventario y préstamo de equipo menor de cocina
echo 5. Selecciona "Public"
echo 6. NO marques "Add a README file" (ya tenemos uno)
echo 7. Haz clic en "Create repository"
echo 8. Copia la URL que aparece (ejemplo: https://github.com/usuario/sistema-inventario-cocina.git)
echo.
set /p repo_url="Pega aquí la URL de tu repositorio de GitHub: "

if "%repo_url%"=="" (
    echo ❌ ERROR: URL del repositorio requerida.
    echo Ejecuta este script nuevamente cuando tengas la URL.
    pause
    exit /b 1
)

echo.
echo Configurando repositorio remoto...
git remote remove origin 2>nul
git remote add origin %repo_url%
echo ✅ Repositorio remoto configurado

echo.
echo Configurando rama principal...
git branch -M main
echo ✅ Rama principal configurada

echo.
echo Subiendo archivos a GitHub...
echo (Se te pedirán tus credenciales de GitHub)
git push -u origin main

if %errorlevel% == 0 (
    echo.
    echo ================================================
    echo      🎉 ¡ÉXITO! PROYECTO SUBIDO A GITHUB
    echo ================================================
    echo.
    echo Tu proyecto ya está disponible en:
    echo %repo_url%
    echo.
    echo Próximos pasos:
    echo 1. Configurar el sistema para red local
    echo 2. Ejecutar: configurar_firewall.bat
    echo 3. Iniciar el sistema: iniciar_sistema.bat
    echo.
) else (
    echo.
    echo ❌ ERROR: No se pudo subir a GitHub.
    echo.
    echo Posibles causas:
    echo 1. URL del repositorio incorrecta
    echo 2. Credenciales de GitHub incorrectas
    echo 3. Problemas de conexión a Internet
    echo 4. El repositorio ya existe y tiene contenido
    echo.
    echo Soluciones:
    echo 1. Verifica la URL del repositorio
    echo 2. Asegúrate de tener acceso al repositorio
    echo 3. Ejecuta: git push -f origin main (forzar subida)
    echo.
)

echo.
echo Presiona cualquier tecla para finalizar...
pause >nul