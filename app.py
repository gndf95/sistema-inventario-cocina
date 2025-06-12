from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os
import qrcode
from io import BytesIO
import base64
import pandas as pd
import io

# Configuración de la aplicación
app = Flask(__name__)

# 🔧 CONFIGURACIÓN PARA RAILWAY Y POSTGRESQL
# Detectar si estamos en Railway o desarrollo local
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Configuración para Railway (Producción)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        # Railway usa postgres:// pero SQLAlchemy necesita postgresql://
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'postgresql://localhost/inventario'
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'railway-secret-key-default')
    app.config['FLASK_ENV'] = os.environ.get('FLASK_ENV', 'production')
    app.config['DEBUG'] = False

    # Variables específicas de Railway
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

    print(f"🚀 MODO RAILWAY DETECTADO")
    print(f"📊 DATABASE_URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "❌ DATABASE_URL no encontrada")
    print(f"🔑 SECRET_KEY configurado: {'✅' if app.config['SECRET_KEY'] else '❌'}")

else:
    # Configuración para desarrollo local
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
    app.config['SECRET_KEY'] = 'tu-clave-secreta-cambiar-esto'
    app.config['FLASK_ENV'] = 'development'
    app.config['DEBUG'] = True
    ADMIN_PASSWORD = 'admin123'
    print("🏠 MODO DESARROLLO LOCAL")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['QR_FOLDER'] = 'static/qr_codes'

# Crear carpetas si no existen (solo en desarrollo local)
if not os.environ.get('RAILWAY_ENVIRONMENT'):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['QR_FOLDER'], exist_ok=True)

# Inicializar extensiones
from models import db, Usuario, TipoEquipo, Prestamo, DetallePrestamo, Ubicacion, Categoria

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# Función auxiliar para generar QR
def generar_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)

    return base64.b64encode(buffered.getvalue()).decode()


# 🔄 INICIALIZACIÓN DE BASE DE DATOS MEJORADA
def init_database():
    """Inicializar base de datos con manejo de errores mejorado"""
    try:
        print("🔄 Inicializando base de datos...")

        # Crear todas las tablas
        db.create_all()
        print("✅ Tablas creadas/verificadas")

        # Verificar si ya existe un usuario admin
        admin_existente = Usuario.query.filter_by(username='admin').first()

        if not admin_existente:
            print("👤 Creando usuario administrador...")

            # Crear usuario admin
            admin = Usuario(
                username='admin',
                nombre='Administrador',
                email='admin@sistema.local',
                rol='admin',
                area='Administración'
            )
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)
            print(f"✅ Admin creado con usuario: admin / contraseña: {ADMIN_PASSWORD}")

        else:
            print("✅ Usuario admin ya existe")

        # Crear ubicaciones por defecto si no existen
        if Ubicacion.query.count() == 0:
            print("📍 Creando ubicaciones por defecto...")
            ubicaciones = [
                Ubicacion(nombre='Almacén Principal', descripcion='Almacén central de equipo'),
                Ubicacion(nombre='Cocina Principal', descripcion='Área de producción'),
                Ubicacion(nombre='Área de Eventos', descripcion='Equipo para eventos')
            ]
            for u in ubicaciones:
                db.session.add(u)
            print("✅ 3 ubicaciones creadas")

        # Crear categorías por defecto si no existen
        if Categoria.query.count() == 0:
            print("🏷️ Creando categorías por defecto...")
            categorias_default = [
                ('Ollas y Sartenes', 'Equipo de cocción'),
                ('Utensilios', 'Cucharas, espátulas, pinzas, etc.'),
                ('Equipo de Corte', 'Cuchillos, tablas, mandolinas'),
                ('Contenedores', 'Recipientes, bandejas, bowls'),
                ('Equipo de Medición', 'Básculas, tazas medidoras'),
                ('Equipo de Servicio', 'Platos, charolas, pinzas de servicio')
            ]

            for nombre, desc in categorias_default:
                categoria = Categoria(nombre=nombre, descripcion=desc)
                db.session.add(categoria)
            print("✅ 6 categorías creadas")

        # Guardar todos los cambios
        db.session.commit()
        print("💾 Base de datos inicializada correctamente!")

        # Mostrar estadísticas
        total_usuarios = Usuario.query.count()
        total_categorias = Categoria.query.count()
        total_ubicaciones = Ubicacion.query.count()
        print(
            f"📊 ESTADÍSTICAS: {total_usuarios} usuarios, {total_categorias} categorías, {total_ubicaciones} ubicaciones")

        return True

    except Exception as e:
        print(f"❌ ERROR al inicializar base de datos: {str(e)}")
        db.session.rollback()
        return False


# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            usuario = Usuario.query.filter_by(username=username).first()

            if usuario and usuario.check_password(password):
                login_user(usuario)
                flash('Inicio de sesión exitoso!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Usuario o contraseña incorrectos', 'danger')

        except Exception as e:
            print(f"❌ Error en login: {str(e)}")
            flash('Error del sistema. Intenta nuevamente.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Ruta de salud para Railway
@app.route('/health')
def health():
    """Endpoint de salud para Railway"""
    try:
        # Verificar conexión a base de datos
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Ruta principal - Dashboard
@app.route('/')
@login_required
def index():
    try:
        # Estadísticas para el dashboard
        total_tipos = TipoEquipo.query.filter_by(activo=True).count()
        total_unidades = db.session.query(db.func.sum(TipoEquipo.cantidad_total)).scalar() or 0
        unidades_disponibles = sum(e.cantidad_disponible for e in TipoEquipo.query.filter_by(activo=True).all())
        prestamos_activos = Prestamo.query.filter(Prestamo.estado.in_(['activo', 'parcial'])).count()

        # Equipos con alerta de stock
        equipos_alerta = TipoEquipo.query.filter_by(activo=True).all()
        equipos_alerta = [e for e in equipos_alerta if e.alerta_stock]

        # Préstamos vencidos
        prestamos_vencidos = Prestamo.query.filter(
            Prestamo.estado.in_(['activo', 'parcial']),
            Prestamo.fecha_devolucion_esperada < datetime.now()
        ).all()

        # Préstamos recientes
        prestamos_recientes = Prestamo.query.order_by(
            Prestamo.fecha_prestamo.desc()
        ).limit(5).all()

        return render_template('index.html',
                               total_tipos=total_tipos,
                               total_unidades=total_unidades,
                               unidades_disponibles=unidades_disponibles,
                               prestamos_activos=prestamos_activos,
                               equipos_alerta=equipos_alerta,
                               prestamos_vencidos=prestamos_vencidos,
                               prestamos_recientes=prestamos_recientes,
                               datetime=datetime)
    except Exception as e:
        print(f"❌ Error en dashboard: {str(e)}")
        flash('Error al cargar el dashboard', 'danger')
        return render_template('login.html')


# [RESTO DE LAS RUTAS SE MANTIENEN IGUAL - Solo agregamos manejo de errores]

# Rutas de Equipos
@app.route('/equipos')
@login_required
def equipos():
    try:
        equipos = TipoEquipo.query.filter_by(activo=True).all()
        categorias = Categoria.query.all()
        return render_template('equipos/lista.html', equipos=equipos, categorias=categorias)
    except Exception as e:
        print(f"❌ Error en equipos: {str(e)}")
        flash('Error al cargar equipos', 'danger')
        return redirect(url_for('index'))


# [Continúa con el resto de las rutas... mantener todas las rutas existentes]

# 🚀 INICIALIZACIÓN Y ARRANQUE
if __name__ == '__main__':
    # Crear contexto de aplicación
    with app.app_context():
        # Inicializar base de datos
        success = init_database()

        if not success:
            print("❌ FALLO AL INICIALIZAR LA BASE DE DATOS")
            exit(1)

    # Configurar puerto para Railway
    port = int(os.environ.get('PORT', 5000))

    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # Configuración para Railway (Producción)
        print(f"🚀 INICIANDO EN RAILWAY - Puerto: {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Configuración para desarrollo local
        print(f"🏠 INICIANDO EN DESARROLLO LOCAL - Puerto: {port}")
        app.run(host='0.0.0.0', port=port, debug=True)