@echo off
chcp 65001 >nul
echo ================================================
echo   Setup GitHub + Railway - Sistema Inventario
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

echo Creando archivos necesarios para Railway...
echo.

REM Crear .gitignore ACTUALIZADO para Railway
echo # Base de datos local ^(no subir datos reales^) > .gitignore
echo *.db >> .gitignore
echo *.sqlite >> .gitignore
echo *.sqlite3 >> .gitignore
echo inventario.db >> .gitignore
echo. >> .gitignore
echo # Variables de entorno >> .gitignore
echo .env >> .gitignore
echo. >> .gitignore
echo # Archivos subidos ^(no subir datos de usuarios^) >> .gitignore
echo static/uploads/* >> .gitignore
echo !static/uploads/.gitkeep >> .gitignore
echo. >> .gitignore
echo # Códigos QR generados >> .gitignore
echo static/qr_codes/* >> .gitignore
echo !static/qr_codes/.gitkeep >> .gitignore
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
echo # Archivos temporales >> .gitignore
echo *.tmp >> .gitignore
echo *.temp >> .gitignore
echo *.bak >> .gitignore
echo *.backup >> .gitignore

echo ✅ Archivo .gitignore actualizado para Railway

REM Crear carpetas necesarias y archivos .gitkeep
mkdir static\uploads 2>nul
mkdir static\qr_codes 2>nul
echo. > static\uploads\.gitkeep
echo. > static\qr_codes\.gitkeep
echo ✅ Carpetas y archivos .gitkeep creados

REM Crear runtime.txt
echo python-3.11.6 > runtime.txt
echo ✅ runtime.txt creado

REM Crear .env.example
echo SECRET_KEY=tu-clave-secreta-super-segura-aqui > .env.example
echo DATABASE_URL=postgresql://usuario:password@host:puerto/database >> .env.example
echo FLASK_ENV=production >> .env.example
echo ADMIN_PASSWORD=contraseña-admin-segura >> .env.example
echo ✅ .env.example creado

REM Crear railway.json
echo { > railway.json
echo   "$schema": "https://railway.app/railway.schema.json", >> railway.json
echo   "build": { >> railway.json
echo     "builder": "NIXPACKS" >> railway.json
echo   }, >> railway.json
echo   "deploy": { >> railway.json
echo     "startCommand": "gunicorn app:app", >> railway.json
echo     "healthcheckPath": "/login", >> railway.json
echo     "healthcheckTimeout": 100, >> railway.json
echo     "restartPolicyType": "ON_FAILURE", >> railway.json
echo     "restartPolicyMaxRetries": 10 >> railway.json
echo   } >> railway.json
echo } >> railway.json
echo ✅ railway.json creado

REM Verificar requirements.txt actualizado
if exist "requirements.txt" (
    echo ✅ requirements.txt ya existe - verificando contenido...
    findstr /C:"gunicorn==23.0.0" requirements.txt >nul
    if %errorlevel% == 0 (
        echo ✅ requirements.txt está actualizado para Railway
    ) else (
        echo ⚠️ requirements.txt necesita actualizarse manualmente
    )
) else (
    echo ❌ requirements.txt no existe - debe crearse manualmente
)

REM Crear README actualizado
echo # 🍳 Sistema de Inventario y Préstamo de Equipo Menor de Cocina > README.md
echo. >> README.md
echo Sistema web desarrollado en Flask para gestionar el inventario, préstamos y devoluciones de equipo menor de cocina en entornos profesionales. >> README.md
echo. >> README.md
echo ## 🚀 Instalación Local >> README.md
echo. >> README.md
echo 1. Clonar el repositorio >> README.md
echo 2. Instalar dependencias: `pip install -r requirements.txt` >> README.md
echo 3. Ejecutar: `python app.py` >> README.md
echo 4. Abrir navegador en: `http://localhost:5000` >> README.md
echo. >> README.md
echo ## 🌐 Deploy en Railway >> README.md
echo. >> README.md
echo 1. Fork este repositorio >> README.md
echo 2. Conectar con Railway ^(railway.app^) >> README.md
echo 3. Agregar base de datos PostgreSQL >> README.md
echo 4. Configurar variables de entorno >> README.md
echo 5. Deploy automático >> README.md
echo. >> README.md
echo ## 📱 Características >> README.md
echo. >> README.md
echo - ✅ Gestión de inventario con códigos QR >> README.md
echo - ✅ Sistema de préstamos y devoluciones >> README.md
echo - ✅ Dashboard responsivo para móviles >> README.md
echo - ✅ Alertas de stock bajo y préstamos vencidos >> README.md
echo - ✅ 3 almacenes especializados preconfigurados >> README.md
echo - ✅ Compatible con PostgreSQL ^(Railway^) >> README.md
echo. >> README.md
echo ## 👥 Usuarios de Prueba >> README.md
echo. >> README.md
echo - admin / admin123 ^(Administrador^) >> README.md
echo - supervisor / 123456 ^(Supervisor^) >> README.md
echo - almacen_compras / 123456 >> README.md
echo - almacen_calidad / 123456 >> README.md
echo - almacen_especial / 123456 >> README.md

echo ✅ README.md actualizado

echo.
echo ================================================
echo   Archivos preparados para Railway
echo ================================================
echo.
echo Archivos creados/actualizados:
echo ✅ .gitignore ^(compatible con Railway^)
echo ✅ runtime.txt
echo ✅ .env.example
echo ✅ railway.json
echo ✅ static/uploads/.gitkeep
echo ✅ static/qr_codes/.gitkeep
echo ✅ README.md ^(con instrucciones de Railway^)
echo.

REM Limpiar archivos innecesarios antes de subir
if exist "inventario.db" (
    echo Eliminando base de datos local...
    del inventario.db
    echo ✅ inventario.db eliminado
)

if exist "__pycache__" (
    echo Eliminando caché de Python...
    rmdir /s /q __pycache__
    echo ✅ __pycache__ eliminado
)

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
echo Creando commit para Railway...
git commit -m "Preparar para Railway: PostgreSQL + Gunicorn + Archivos de configuración"
echo ✅ Commit creado

echo.
echo ================================================
echo      CONFIGURACIÓN DEL REPOSITORIO REMOTO
echo ================================================
echo.
echo IMPORTANTE: Necesitas crear el repositorio en GitHub primero
echo.
echo 1. Ve a: https://github.com
echo 2. Haz clic en el botón verde "New" ^(nuevo repositorio^)
echo 3. Nombre del repositorio: sistema-inventario-cocina
echo 4. Descripción: Sistema de inventario y préstamo de equipo menor de cocina
echo 5. Selecciona "Public"
echo 6. NO marques "Add a README file" ^(ya tenemos uno^)
echo 7. Haz clic en "Create repository"
echo 8. Copia la URL que aparece
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
    echo 🚀 PRÓXIMOS PASOS PARA RAILWAY:
    echo 1. Ve a: https://railway.app
    echo 2. Sign up with GitHub
    echo 3. New Project ^-^> Deploy from GitHub repo
    echo 4. Seleccionar tu repositorio
    echo 5. Agregar PostgreSQL ^(+ New Service ^-^> Database^)
    echo 6. Configurar variables de entorno:
    echo    - SECRET_KEY=tu-clave-segura
    echo    - FLASK_ENV=production
    echo    - ADMIN_PASSWORD=contraseña-admin
    echo 7. Deploy automático
    echo.
    echo ✅ Tu app estará en: https://tu-proyecto.railway.app
    echo.
) else (
    echo.
    echo ❌ ERROR: No se pudo subir a GitHub.
    echo Verifica la URL y tus credenciales.
    echo.
)

echo.
echo Presiona cualquier tecla para finalizar...
pause >nul