import base64
import os
import tempfile
from datetime import datetime
from io import BytesIO
# Agregar import necesario al inicio del archivo
from datetime import timedelta

import qrcode
from flask import Flask, render_template, redirect, url_for, flash, request, send_file, jsonify, make_response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

# Configuración de la aplicación
app = Flask(__name__)
from datetime import datetime

# Hacer datetime disponible en todos los templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

# Configuración de seguridad
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-super-secreta-feedbit-2024!')

# Configuración de base de datos para Railway
# 🔧 CONFIGURACIÓN PARA RAILWAY Y POSTGRESQL
if os.environ.get('RAILWAY_ENVIRONMENT'):
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'postgresql://localhost/inventario'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    print(f"🚀 MODO RAILWAY DETECTADO")
    print(f"📊 DATABASE_URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "❌ DATABASE_URL no encontrada")
    print(f"🔑 SECRET_KEY configurado: {'✅' if app.config['SECRET_KEY'] else '❌'}")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
    ADMIN_PASSWORD = 'admin123'
    print("🏠 MODO DESARROLLO LOCAL")
    # Desarrollo local - SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['QR_FOLDER'] = 'static/qr_codes'

# Crear carpetas si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['QR_FOLDER'], exist_ok=True)

# Inicializar extensiones
from models import db, Usuario, TipoEquipo, Prestamo, DetallePrestamo, Ubicacion, Categoria

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

# Constantes para las áreas
ALMACENES_DISPONIBLES = [
    'Almacén Compras',
    'Almacén Calidad e Higiene',
    'Almacén Equipo Especial'
]

AREAS_OPERATIVAS = [
    'Cocina Fría',
    'Almacén',
    'Cocina Caliente',
    'Repostería',
    'Panadería',
    'Logística',
    'Ventas'
]


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


# Función para generar PDF completo
def generar_pdf_prestamo(prestamo):
    """Genera un PDF completo para el préstamo"""

    buffer = BytesIO()

    # Configurar el documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )

    elements = []
    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.darkblue,
        alignment=1  # Centrado
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )

    # Título principal
    titulo = Paragraph("COMPROBANTE DE PRÉSTAMO DE EQUIPO", title_style)
    elements.append(titulo)
    elements.append(Spacer(1, 12))

    # Información del préstamo
    info_prestamo = [
        ["Folio:", prestamo.folio or f"PRE-{prestamo.id}"],
        ["Fecha de préstamo:", prestamo.fecha_prestamo.strftime('%d/%m/%Y %H:%M')],
        ["Fecha de devolución:", prestamo.fecha_devolucion_esperada.strftime('%d/%m/%Y')],
        ["Estado:", prestamo.estado.upper()]
    ]

    tabla_info = Table(info_prestamo, colWidths=[2 * inch, 3 * inch])
    tabla_info.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
        ('BACKGROUND', (1, 0), (1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(tabla_info)
    elements.append(Spacer(1, 20))

    # Información del responsable
    subtitulo_responsable = Paragraph("DATOS DEL RESPONSABLE", subtitle_style)
    elements.append(subtitulo_responsable)

    info_responsable = [
        ["Nombre:", prestamo.responsable_nombre],
        ["Área:", prestamo.responsable_area or "No especificada"],
        ["Teléfono:", prestamo.responsable_telefono or "No proporcionado"],
        ["Motivo:", prestamo.motivo or "No especificado"]
    ]

    if prestamo.evento:
        info_responsable.append(["Evento/Descripción:", prestamo.evento])

    tabla_responsable = Table(info_responsable, colWidths=[2 * inch, 4 * inch])
    tabla_responsable.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(tabla_responsable)
    elements.append(Spacer(1, 20))

    # Detalle de equipos
    subtitulo_equipos = Paragraph("DETALLE DE EQUIPOS PRESTADOS", subtitle_style)
    elements.append(subtitulo_equipos)

    # Encabezados de la tabla de equipos
    data_equipos = [["Código", "Equipo", "Cantidad", "Estado"]]

    # Agregar cada equipo
    for detalle in prestamo.detalles:
        estado_item = "Devuelto" if detalle.devuelto_completo else f"Pendiente ({detalle.pendiente})"

        data_equipos.append([
            detalle.tipo_equipo.codigo,
            detalle.tipo_equipo.nombre,
            str(detalle.cantidad),
            estado_item
        ])

    # Agregar fila de totales
    total_items = sum(d.cantidad for d in prestamo.detalles)
    items_pendientes = prestamo.items_pendientes

    data_equipos.append([
        "TOTAL",
        f"{prestamo.detalles.count()} tipos de equipo",
        str(total_items),
        f"Pendientes: {items_pendientes}"
    ])

    tabla_equipos = Table(data_equipos, colWidths=[1.5 * inch, 3 * inch, 1 * inch, 1.5 * inch])
    tabla_equipos.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),

        # Contenido
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),

        # Fila de totales
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

        # Alternar colores de filas
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightblue])
    ]))

    elements.append(tabla_equipos)
    elements.append(Spacer(1, 30))

    # Firmas
    firmas_data = [
        ["", ""],
        ["_" * 30, "_" * 30],
        ["Entregó", "Recibió"],
        [prestamo.usuario_prestamo.nombre if prestamo.usuario_prestamo else "", prestamo.responsable_nombre]
    ]

    tabla_firmas = Table(firmas_data, colWidths=[3 * inch, 3 * inch])
    tabla_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(tabla_firmas)

    # Pie de página
    elements.append(Spacer(1, 20))
    footer = Paragraph(
        f"Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | Sistema de Inventario",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
    )
    elements.append(footer)

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


# Crear tablas y usuario admin
def init_database():
        with app.app_context():
            try:
                # Intentar crear todas las tablas
                db.create_all()
                print("✅ Tablas creadas/verificadas")

                # Verificar si ya hay usuarios
                if Usuario.query.first():
                    print("✅ Base de datos ya tiene datos")
                    return

                print("🔄 Inicializando datos por defecto...")

                # Resto de tu código existente de init_database()...
                # (todo lo que tienes después de db.create_all())

            except Exception as e:
                print(f"❌ Error en base de datos: {e}")
                # En Railway, reintentamos la conexión
                try:
                    print("🔄 Reintentando inicialización...")
                    db.session.rollback()
                    db.create_all()
                    print("✅ Segundo intento exitoso")
                except Exception as e2:
                    print(f"❌ Error crítico: {e2}")
                    # No fallar completamente, dejar que Railway maneje
                    pass

        # Crear usuario admin si no existe
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                nombre='Administrador',
                email='admin@feedbit.net',
                rol='admin',
                area='Administración',
                area_trabajo='Todas',
                puede_prestar_todas_areas=True
            )
            admin.set_password(ADMIN_PASSWORD)
            db.session.add(admin)

            # Crear ubicaciones para los 3 almacenes
            if not Ubicacion.query.first():
                ubicaciones = [
                    Ubicacion(nombre='Almacén Compras',
                              descripcion='Almacén de utensilios generales y herramientas básicas',
                              responsable='Área de Compras'),
                    Ubicacion(nombre='Almacén Calidad e Higiene',
                              descripcion='Almacén de instrumentos de control y medición',
                              responsable='Calidad e Higiene'),
                    Ubicacion(nombre='Almacén Equipo Especial',
                              descripcion='Almacén de maquinaria y herramientas especializadas',
                              responsable='Equipo Especial'),
                    Ubicacion(nombre='Almacén General', descripcion='Equipos compartidos entre almacenes',
                              responsable='Administración')
                ]
                for u in ubicaciones:
                    db.session.add(u)

            # Crear categorías específicas para cada almacén
            categorias_por_almacen = [
                # ALMACÉN COMPRAS
                ('Utensilios Básicos', 'Cucharas, espátulas, pinzas, batidores manuales'),
                ('Cuchillos y Herramientas de Corte', 'Cuchillos básicos, peladores, cortadores'),
                ('Contenedores y Recipientes', 'Bowls, recipientes, bandejas, contenedores'),
                ('Equipo de Medición Básico', 'Tazas medidoras, básculas básicas, jarras'),
                ('Herramientas de Preparación', 'Coladores, ralladores, prensas, abridores'),

                # ALMACÉN CALIDAD E HIGIENE
                ('Instrumentos de Medición', 'Termómetros, medidores de pH, higrómetros'),
                ('Balanzas de Precisión', 'Básculas digitales de alta precisión'),
                ('Equipo de Muestreo', 'Herramientas para toma de muestras y análisis'),
                ('Equipo de Limpieza Especializada', 'Materiales y herramientas de higiene industrial'),
                ('Instrumentos de Control', 'Equipos de verificación y calibración'),

                # ALMACÉN EQUIPO ESPECIAL
                ('Maquinaria Menor', 'Batidoras industriales, procesadores, licuadoras'),
                ('Herramientas Especializadas', 'Mandolinas profesionales, cortadoras eléctricas'),
                ('Equipo Electrónico', 'Equipos con componentes electrónicos especiales'),
                ('Equipo de Vacío y Sellado', 'Selladoras al vacío, bombas, equipos de empaque'),
                ('Maquinaria de Repostería', 'Batidoras planetarias, amasadoras, laminadoras')
            ]

            for nombre, desc in categorias_por_almacen:
                if not Categoria.query.filter_by(nombre=nombre).first():
                    categoria = Categoria(nombre=nombre, descripcion=desc)
                    db.session.add(categoria)

            db.session.commit()

            # Crear usuarios para los 3 almacenes
            usuarios_almacenes = [
                {
                    'username': 'almacen_compras',
                    'nombre': 'Responsable Almacén Compras',
                    'email': 'compras@feedbit.net',
                    'area_trabajo': 'Almacén Compras',
                    'area': 'Compras',
                    'rol': 'usuario'
                },
                {
                    'username': 'almacen_calidad',
                    'nombre': 'Responsable Almacén Calidad',
                    'email': 'calidad@feedbit.net',
                    'area_trabajo': 'Almacén Calidad e Higiene',
                    'area': 'Calidad e Higiene',
                    'rol': 'usuario'
                },
                {
                    'username': 'almacen_especial',
                    'nombre': 'Responsable Almacén Especial',
                    'email': 'especial@feedbit.net',
                    'area_trabajo': 'Almacén Equipo Especial',
                    'area': 'Equipo Especial',
                    'rol': 'usuario'
                },
                {
                    'username': 'supervisor',
                    'nombre': 'Supervisor General',
                    'email': 'supervisor@feedbit.net',
                    'area_trabajo': 'Supervisión',
                    'area': 'Supervisión',
                    'rol': 'supervisor',
                    'puede_prestar_todas_areas': True
                }
            ]

            for user_data in usuarios_almacenes:
                if not Usuario.query.filter_by(username=user_data['username']).first():
                    user = Usuario(
                        username=user_data['username'],
                        nombre=user_data['nombre'],
                        email=user_data['email'],
                        area=user_data['area'],
                        area_trabajo=user_data['area_trabajo'],
                        rol=user_data['rol'],
                        puede_prestar_todas_areas=user_data.get('puede_prestar_todas_areas', False)
                    )
                    user.set_password('123456')  # Contraseña temporal
                    db.session.add(user)

            db.session.commit()

            # Crear equipos de ejemplo para cada almacén
            equipos_ejemplo = [
                # ALMACÉN COMPRAS - Utensilios generales
                {
                    'codigo': 'COMP-CUCH-001',
                    'nombre': 'Cuchillo Chef 8"',
                    'descripcion': 'Cuchillo básico para preparación general',
                    'categoria': 'Cuchillos y Herramientas de Corte',
                    'ubicacion': 'Almacén Compras',
                    'cantidad_total': 15,
                    'cantidad_minima': 5
                },
                {
                    'codigo': 'COMP-ESP-001',
                    'nombre': 'Set Espátulas de Silicón',
                    'descripcion': 'Juego de 3 espátulas resistentes al calor',
                    'categoria': 'Utensilios Básicos',
                    'ubicacion': 'Almacén Compras',
                    'cantidad_total': 12,
                    'cantidad_minima': 3
                },
                {
                    'codigo': 'COMP-BOWL-001',
                    'nombre': 'Bowls de Acero Inoxidable',
                    'descripcion': 'Set de bowls de diferentes tamaños',
                    'categoria': 'Contenedores y Recipientes',
                    'ubicacion': 'Almacén Compras',
                    'cantidad_total': 20,
                    'cantidad_minima': 6
                },
                {
                    'codigo': 'COMP-TABLA-001',
                    'nombre': 'Tabla de Corte Plástica',
                    'descripcion': 'Tabla de corte color blanco para uso general',
                    'categoria': 'Cuchillos y Herramientas de Corte',
                    'ubicacion': 'Almacén Compras',
                    'cantidad_total': 25,
                    'cantidad_minima': 8
                },

                # ALMACÉN CALIDAD E HIGIENE - Instrumentos de control
                {
                    'codigo': 'CAL-TERM-001',
                    'nombre': 'Termómetro Digital Infrarrojo',
                    'descripcion': 'Termómetro sin contacto para control de temperatura',
                    'categoria': 'Instrumentos de Medición',
                    'ubicacion': 'Almacén Calidad e Higiene',
                    'cantidad_total': 6,
                    'cantidad_minima': 2
                },
                {
                    'codigo': 'CAL-BAL-001',
                    'nombre': 'Balanza Digital 5kg',
                    'descripcion': 'Balanza de precisión 0.1g para control de calidad',
                    'categoria': 'Balanzas de Precisión',
                    'ubicacion': 'Almacén Calidad e Higiene',
                    'cantidad_total': 4,
                    'cantidad_minima': 1
                },
                {
                    'codigo': 'CAL-PH-001',
                    'nombre': 'Medidor de pH Digital',
                    'descripcion': 'pHmetro digital para control de acidez',
                    'categoria': 'Instrumentos de Medición',
                    'ubicacion': 'Almacén Calidad e Higiene',
                    'cantidad_total': 3,
                    'cantidad_minima': 1
                },

                # ALMACÉN EQUIPO ESPECIAL - Maquinaria especializada
                {
                    'codigo': 'ESP-BAT-001',
                    'nombre': 'Batidora Planetaria 20L',
                    'descripcion': 'Batidora industrial para grandes volúmenes',
                    'categoria': 'Maquinaria de Repostería',
                    'ubicacion': 'Almacén Equipo Especial',
                    'cantidad_total': 2,
                    'cantidad_minima': 1
                },
                {
                    'codigo': 'ESP-MAN-001',
                    'nombre': 'Mandolina Profesional',
                    'descripcion': 'Cortadora profesional con múltiples cuchillas',
                    'categoria': 'Herramientas Especializadas',
                    'ubicacion': 'Almacén Equipo Especial',
                    'cantidad_total': 3,
                    'cantidad_minima': 1
                },
                {
                    'codigo': 'ESP-VAC-001',
                    'nombre': 'Selladora al Vacío Profesional',
                    'descripcion': 'Máquina selladora al vacío para conservación',
                    'categoria': 'Equipo de Vacío y Sellado',
                    'ubicacion': 'Almacén Equipo Especial',
                    'cantidad_total': 2,
                    'cantidad_minima': 1
                }
            ]

            for equipo_data in equipos_ejemplo:
                if not TipoEquipo.query.filter_by(codigo=equipo_data['codigo']).first():
                    categoria = Categoria.query.filter_by(nombre=equipo_data['categoria']).first()
                    ubicacion = Ubicacion.query.filter_by(nombre=equipo_data['ubicacion']).first()

                    if categoria and ubicacion:
                        nuevo_equipo = TipoEquipo(
                            codigo=equipo_data['codigo'],
                            nombre=equipo_data['nombre'],
                            descripcion=equipo_data['descripcion'],
                            categoria_id=categoria.id,
                            ubicacion_id=ubicacion.id,
                            cantidad_total=equipo_data['cantidad_total'],
                            cantidad_minima=equipo_data['cantidad_minima']
                        )

                        db.session.add(nuevo_equipo)
                        db.session.commit()

                        # Generar QR
                        qr_data = f"EQUIPO:{nuevo_equipo.id}:{nuevo_equipo.codigo}"
                        nuevo_equipo.codigo_qr = generar_qr(qr_data)

                        db.session.commit()

            print("Base de datos inicializada con 3 almacenes, 7 áreas operativas y 10 equipos de ejemplo!")


# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        usuario = Usuario.query.filter_by(username=username).first()

        if usuario and usuario.check_password(password):
            login_user(usuario)
            flash('Inicio de sesión exitoso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Ruta principal - Dashboard
@app.route('/')
@login_required
def index():
    # Estadísticas para el dashboard (filtradas por almacén si es necesario)
    if current_user.rol in ['admin', 'supervisor']:
        # Admin y supervisor ven todo
        equipos_query = TipoEquipo.query.filter_by(activo=True)
        prestamos_query = Prestamo.query
    else:
        # Usuario normal ve solo su almacén
        if current_user.area_trabajo:
            ubicacion = Ubicacion.query.filter_by(nombre=current_user.area_trabajo).first()
            if ubicacion:
                equipos_query = TipoEquipo.query.filter_by(activo=True, ubicacion_id=ubicacion.id)
                # Para préstamos, puede ver todos los que ha realizado él
                prestamos_query = Prestamo.query
            else:
                equipos_query = TipoEquipo.query.filter_by(activo=True)
                prestamos_query = Prestamo.query
        else:
            equipos_query = TipoEquipo.query.filter_by(activo=True)
            prestamos_query = Prestamo.query

    equipos = equipos_query.all()

    total_tipos = len(equipos)
    total_unidades = sum(e.cantidad_total for e in equipos)
    unidades_disponibles = sum(e.cantidad_disponible for e in equipos)
    prestamos_activos = prestamos_query.filter(Prestamo.estado.in_(['activo', 'parcial'])).count()

    # Equipos con alerta de stock
    equipos_alerta = [e for e in equipos if e.alerta_stock]

    # Préstamos vencidos
    prestamos_vencidos = prestamos_query.filter(
        Prestamo.estado.in_(['activo', 'parcial']),
        Prestamo.fecha_devolucion_esperada < datetime.now()
    ).all()

    # Préstamos por vencer (próximos 3 días)
    prestamos_por_vencer = prestamos_query.filter(
        Prestamo.estado.in_(['activo', 'parcial']),
        Prestamo.fecha_devolucion_esperada >= datetime.now(),
        Prestamo.fecha_devolucion_esperada <= datetime.now() + timedelta(days=3)
    ).all()

    # Préstamos recientes
    prestamos_recientes = prestamos_query.order_by(
        Prestamo.fecha_prestamo.desc()
    ).limit(10).all()

    # Mis préstamos recientes (los que hizo el usuario actual)
    mis_prestamos_recientes = Prestamo.query.filter_by(
        usuario_prestamo_id=current_user.id
    ).order_by(Prestamo.fecha_prestamo.desc()).limit(6).all()

    return render_template('index.html',
                           total_tipos=total_tipos,
                           total_unidades=total_unidades,
                           unidades_disponibles=unidades_disponibles,
                           prestamos_activos=prestamos_activos,
                           equipos_alerta=equipos_alerta,
                           prestamos_vencidos=prestamos_vencidos,
                           prestamos_por_vencer=prestamos_por_vencer,
                           prestamos_recientes=prestamos_recientes,
                           mis_prestamos_recientes=mis_prestamos_recientes,
                           datetime=datetime)


# Rutas de Equipos
@app.route('/equipos')
@login_required
def equipos():
    equipos = TipoEquipo.query.filter_by(activo=True).all()
    categorias = Categoria.query.all()
    return render_template('equipos/lista.html', equipos=equipos, categorias=categorias)


@app.route('/equipos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_equipo():
    if request.method == 'POST':
        equipo = TipoEquipo(
            codigo=request.form.get('codigo'),
            nombre=request.form.get('nombre'),
            descripcion=request.form.get('descripcion'),
            categoria_id=request.form.get('categoria_id'),
            ubicacion_id=request.form.get('ubicacion_id'),
            cantidad_total=int(request.form.get('cantidad_total', 1)),
            cantidad_minima=int(request.form.get('cantidad_minima', 1))
        )

        db.session.add(equipo)
        db.session.commit()

        # Generar QR para el equipo
        qr_data = f"EQUIPO:{equipo.id}:{equipo.codigo}"
        equipo.codigo_qr = generar_qr(qr_data)
        db.session.commit()

        flash('Equipo agregado exitosamente!', 'success')
        return redirect(url_for('equipos'))

    categorias = Categoria.query.all()
    ubicaciones = Ubicacion.query.all()
    return render_template('equipos/nuevo.html',
                           categorias=categorias,
                           ubicaciones=ubicaciones)


@app.route('/equipos/<int:id>')
@login_required
def ver_equipo(id):
    equipo = TipoEquipo.query.get_or_404(id)
    # Historial de préstamos
    historial = DetallePrestamo.query.filter_by(tipo_equipo_id=id).join(Prestamo).order_by(
        Prestamo.fecha_prestamo.desc()).all()
    return render_template('equipos/ver.html', equipo=equipo, historial=historial)


@app.route('/equipos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_equipo(id):
    equipo = TipoEquipo.query.get_or_404(id)

    if request.method == 'POST':
        equipo.nombre = request.form.get('nombre')
        equipo.descripcion = request.form.get('descripcion')
        equipo.categoria_id = request.form.get('categoria_id')
        equipo.ubicacion_id = request.form.get('ubicacion_id')
        equipo.cantidad_total = int(request.form.get('cantidad_total', 1))
        equipo.cantidad_minima = int(request.form.get('cantidad_minima', 1))

        db.session.commit()
        flash('Equipo actualizado exitosamente!', 'success')
        return redirect(url_for('ver_equipo', id=id))

    categorias = Categoria.query.all()
    ubicaciones = Ubicacion.query.all()
    return render_template('equipos/editar.html',
                           equipo=equipo,
                           categorias=categorias,
                           ubicaciones=ubicaciones)


# Rutas de Préstamos
# Busca esta función en tu app.py (alrededor de la línea 654)
# Reemplaza toda la función prestamos() en tu app.py
@app.route('/prestamos')
@login_required
def prestamos():
    prestamos = Prestamo.query.order_by(Prestamo.fecha_prestamo.desc()).all()

    # Agregar datetime para los templates
    from datetime import datetime

    # Calcular estadísticas básicas
    prestamos_activos_count = len([p for p in prestamos if p.estado == 'activo'])
    prestamos_vencidos_count = len([p for p in prestamos if p.vencido])
    prestamos_devueltos_count = len([p for p in prestamos if p.estado == 'devuelto'])

    # Obtener usuarios que han hecho préstamos (CORREGIDO)
    # En lugar de join, usamos una consulta más específica
    usuarios_ids = db.session.query(Prestamo.usuario_prestamo_id).distinct().all()
    usuarios_prestamos = Usuario.query.filter(
        Usuario.id.in_([uid[0] for uid in usuarios_ids if uid[0] is not None])
    ).all()

    return render_template('prestamos/lista.html',
                           prestamos=prestamos,
                           datetime=datetime,
                           prestamos_activos_count=prestamos_activos_count,
                           prestamos_vencidos_count=prestamos_vencidos_count,
                           prestamos_devueltos_count=prestamos_devueltos_count,
                           usuarios_prestamos=usuarios_prestamos)
@app.route('/prestamos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_prestamo():
    if request.method == 'POST':
        # Crear el préstamo
        prestamo = Prestamo(
            usuario_prestamo_id=current_user.id,
            responsable_nombre=request.form.get('responsable_nombre'),
            responsable_area=request.form.get('responsable_area'),
            responsable_telefono=request.form.get('responsable_telefono'),
            motivo=request.form.get('motivo'),
            evento=request.form.get('evento'),
            fecha_devolucion_esperada=datetime.strptime(
                request.form.get('fecha_devolucion'), '%Y-%m-%d'
            )
        )
        prestamo.generar_folio()

        # Agregar los detalles del préstamo
        equipos_ids = request.form.getlist('equipo_id[]')
        cantidades = request.form.getlist('cantidad[]')

        for equipo_id, cantidad in zip(equipos_ids, cantidades):
            if equipo_id and int(cantidad) > 0:
                equipo = TipoEquipo.query.get(equipo_id)
                if equipo and equipo.cantidad_disponible >= int(cantidad):
                    detalle = DetallePrestamo(
                        tipo_equipo_id=equipo_id,
                        cantidad=int(cantidad)
                    )
                    prestamo.detalles.append(detalle)

        if prestamo.detalles.count() > 0:
            # Generar QR del préstamo
            qr_data = f"PRESTAMO:{prestamo.folio}"
            prestamo.codigo_qr_prestamo = generar_qr(qr_data)

            db.session.add(prestamo)
            db.session.commit()

            flash('Préstamo registrado exitosamente!', 'success')
            return redirect(url_for('ver_prestamo', id=prestamo.id))
        else:
            flash('No se pudo crear el préstamo. Verifica las cantidades disponibles.', 'danger')

    # Obtener equipos disponibles según el área del usuario
    equipos_disponibles = TipoEquipo.query.filter_by(activo=True).all()
    # Por ahora mostrar todos, más adelante filtrar por almacén del usuario
    equipos_disponibles = [e for e in equipos_disponibles if e.cantidad_disponible > 0]

    return render_template('prestamos/nuevo.html',
                           equipos=equipos_disponibles,
                           area_usuario=getattr(current_user, 'area_trabajo', None))


@app.route('/prestamos/<int:id>')
@login_required
def ver_prestamo(id):
    prestamo = Prestamo.query.get_or_404(id)
    return render_template('prestamos/ver.html', prestamo=prestamo)


@app.route('/prestamos/<int:id>/pdf')
@login_required
def descargar_pdf_prestamo(id):
    prestamo = Prestamo.query.get_or_404(id)
    pdf = generar_pdf_prestamo(prestamo)

    response = make_response(pdf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=prestamo_{prestamo.folio}.pdf'

    return response


@app.route('/prestamos/<int:id>/devolver', methods=['GET', 'POST'])
@login_required
def devolver_prestamo(id):
    prestamo = Prestamo.query.get_or_404(id)

    if request.method == 'POST':
        # Procesar devolución por cada item
        for detalle in prestamo.detalles:
            cantidad_devuelta = int(request.form.get(f'cantidad_{detalle.id}', 0))
            if cantidad_devuelta > 0:
                detalle.cantidad_devuelta += cantidad_devuelta
                detalle.estado_devolucion = request.form.get(f'estado_{detalle.id}')
                detalle.observaciones = request.form.get(f'obs_{detalle.id}')
                detalle.fecha_devolucion = datetime.now()

        # Actualizar estado del préstamo
        if all(d.devuelto_completo for d in prestamo.detalles):
            prestamo.estado = 'devuelto'
            prestamo.fecha_devolucion_real = datetime.now()
        elif any(d.cantidad_devuelta > 0 for d in prestamo.detalles):
            prestamo.estado = 'parcial'

        prestamo.usuario_devolucion_id = current_user.id
        prestamo.observaciones_devolucion = request.form.get('observaciones_generales')

        db.session.commit()
        flash('Devolución registrada exitosamente!', 'success')
        return redirect(url_for('ver_prestamo', id=id))

    return render_template('prestamos/devolver.html', prestamo=prestamo)


# Rutas de Reportes
@app.route('/reportes')
@login_required
def reportes():
    # Estadísticas principales
    total_prestamos = Prestamo.query.count()
    prestamos_este_mes = Prestamo.query.filter(
        Prestamo.fecha_prestamo >= datetime.now().replace(day=1)
    ).count()

    total_tipos_equipo = TipoEquipo.query.filter_by(activo=True).count()

    # Calcular disponibles
    equipos = TipoEquipo.query.filter_by(activo=True).all()
    total_disponibles = sum(e.cantidad_disponible for e in equipos)

    # Préstamos por estado
    prestamos_vencidos_count = Prestamo.query.filter(
        Prestamo.estado.in_(['activo', 'parcial']),
        Prestamo.fecha_devolucion_esperada < datetime.now()
    ).count()

    prestamos_por_vencer = Prestamo.query.filter(
        Prestamo.estado.in_(['activo', 'parcial']),
        Prestamo.fecha_devolucion_esperada >= datetime.now(),
        Prestamo.fecha_devolucion_esperada <= datetime.now() + timedelta(days=3)
    ).count()

    prestamos_activos_count = Prestamo.query.filter(
        Prestamo.estado.in_(['activo', 'parcial'])
    ).count()

    prestamos_devueltos_count = Prestamo.query.filter_by(estado='devuelto').count()

    # Calcular tasa de devolución
    if total_prestamos > 0:
        tasa_devolucion = round((prestamos_devueltos_count / total_prestamos) * 100, 1)
    else:
        tasa_devolucion = 0

    # Calcular promedio de días de préstamo
    prestamos_con_devolucion = Prestamo.query.filter(
        Prestamo.fecha_devolucion_real.isnot(None)
    ).all()

    if prestamos_con_devolucion:
        total_dias = sum(p.dias_prestamo for p in prestamos_con_devolucion)
        promedio_dias = round(total_dias / len(prestamos_con_devolucion), 1)
    else:
        promedio_dias = 0

    # Top equipo más prestado
    top_equipo = None
    if total_prestamos > 0:
        from sqlalchemy import func
        resultado = db.session.query(
            TipoEquipo,
            func.count(DetallePrestamo.id).label('veces_prestado')
        ).join(DetallePrestamo).group_by(TipoEquipo.id).order_by(
            func.count(DetallePrestamo.id).desc()
        ).first()

        if resultado:
            top_equipo = {
                'nombre': resultado[0].nombre,
                'veces_prestado': resultado[1]
            }

    # Top usuario más activo
    top_usuario = None
    if total_prestamos > 0:
        resultado_usuario = db.session.query(
            Usuario,
            func.count(Prestamo.id).label('total_prestamos')
        ).join(Prestamo, Usuario.id == Prestamo.usuario_prestamo_id).group_by(Usuario.id).order_by(
            func.count(Prestamo.id).desc()
        ).first()

        if resultado_usuario:
            top_usuario = {
                'nombre': resultado_usuario[0].nombre,
                'total_prestamos': resultado_usuario[1]
            }

    # Usuarios activos totales
    total_usuarios_activos = Usuario.query.filter_by(activo=True).count()

    return render_template('reportes/index.html',
                           total_prestamos=total_prestamos,
                           prestamos_este_mes=prestamos_este_mes,
                           total_tipos_equipo=total_tipos_equipo,
                           total_disponibles=total_disponibles,
                           prestamos_vencidos_count=prestamos_vencidos_count,
                           prestamos_por_vencer=prestamos_por_vencer,
                           prestamos_activos_count=prestamos_activos_count,
                           prestamos_devueltos_count=prestamos_devueltos_count,
                           tasa_devolucion=tasa_devolucion,
                           promedio_dias=promedio_dias,
                           top_equipo=top_equipo,
                           top_usuario=top_usuario,
                           total_usuarios_activos=total_usuarios_activos)

@app.route('/reportes/historial')
@login_required
def historial_completo():
    # Filtros
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    equipo_id = request.args.get('equipo_id')
    responsable = request.args.get('responsable')

    query = Prestamo.query

    if fecha_inicio:
        query = query.filter(Prestamo.fecha_prestamo >= datetime.strptime(fecha_inicio, '%Y-%m-%d'))
    if fecha_fin:
        query = query.filter(Prestamo.fecha_prestamo <= datetime.strptime(fecha_fin, '%Y-%m-%d'))
    if responsable:
        query = query.filter(Prestamo.responsable_nombre.contains(responsable))

    prestamos = query.order_by(Prestamo.fecha_prestamo.desc()).all()
    equipos = TipoEquipo.query.all()

    return render_template('reportes/historial.html',
                           prestamos=prestamos,
                           equipos=equipos)


# Rutas de Configuración
@app.route('/configuracion')
@login_required
def configuracion():
    if current_user.rol != 'admin':
        flash('No tienes permisos para acceder a esta sección', 'danger')
        return redirect(url_for('index'))

    # Obtener datos dinámicos del sistema
    usuarios = Usuario.query.all()
    ubicaciones = Ubicacion.query.all()
    categorias = Categoria.query.all()

    # Estadísticas del sistema para el tab Sistema
    total_equipos = TipoEquipo.query.filter_by(activo=True).count()
    total_prestamos = Prestamo.query.count()
    prestamos_activos = Prestamo.query.filter(Prestamo.estado.in_(['activo', 'parcial'])).count()
    prestamos_vencidos = Prestamo.query.filter(
        Prestamo.estado.in_(['activo', 'parcial']),
        Prestamo.fecha_devolucion_esperada < datetime.now()
    ).count()

    # Alertas del sistema
    equipos_stock_bajo = TipoEquipo.query.filter_by(activo=True).all()
    equipos_alerta = [e for e in equipos_stock_bajo if e.alerta_stock]

    # Usuarios activos
    usuarios_activos = Usuario.query.filter_by(activo=True).count()

    # Calcular espacio usado (simulado)
    import os
    try:
        db_size = os.path.getsize('inventario.db') / (1024 * 1024)  # MB
    except:
        db_size = 0

    estadisticas_sistema = {
        'total_equipos': total_equipos,
        'total_prestamos': total_prestamos,
        'prestamos_activos': prestamos_activos,
        'prestamos_vencidos': prestamos_vencidos,
        'equipos_alerta': len(equipos_alerta),
        'usuarios_activos': usuarios_activos,
        'db_size_mb': round(db_size, 2),
        'version': '1.0.0'
    }

    return render_template('configuracion/index.html',
                           usuarios=usuarios,
                           ubicaciones=ubicaciones,
                           categorias=categorias,
                           datetime=datetime,
                           estadisticas=estadisticas_sistema)


@app.route('/configuracion/usuarios/nuevo', methods=['POST'])
@login_required
def nuevo_usuario():
    if current_user.rol != 'admin':
        return jsonify({'error': 'Sin permisos'}), 403

    usuario = Usuario(
        username=request.form.get('username'),
        nombre=request.form.get('nombre'),
        email=request.form.get('email'),
        rol=request.form.get('rol'),
        area=request.form.get('area'),
        area_trabajo=request.form.get('area_trabajo'),
        puede_prestar_todas_areas=bool(request.form.get('puede_prestar_todas_areas'))
    )
    usuario.set_password(request.form.get('password'))

    db.session.add(usuario)
    db.session.commit()

    flash('Usuario creado exitosamente!', 'success')
    return redirect(url_for('configuracion'))


@app.route('/configuracion/categorias/nueva', methods=['POST'])
@login_required
def nueva_categoria():
    if current_user.rol != 'admin':
        return jsonify({'error': 'Sin permisos'}), 403

    categoria = Categoria(
        nombre=request.form.get('nombre'),
        descripcion=request.form.get('descripcion')
    )

    db.session.add(categoria)
    db.session.commit()

    flash('Categoría creada exitosamente!', 'success')
    return redirect(url_for('configuracion'))


@app.route('/configuracion/ubicaciones/nueva', methods=['POST'])
@login_required
def nueva_ubicacion():
    if current_user.rol != 'admin':
        return jsonify({'error': 'Sin permisos'}), 403

    ubicacion = Ubicacion(
        nombre=request.form.get('nombre'),
        descripcion=request.form.get('descripcion'),
        responsable=request.form.get('responsable')
    )

    db.session.add(ubicacion)
    db.session.commit()

    flash('Ubicación creada exitosamente!', 'success')
    return redirect(url_for('configuracion'))


# API endpoints para funcionalidad AJAX
@app.route('/api/equipo/<int:id>/disponibilidad')
@login_required
def verificar_disponibilidad(id):
    equipo = TipoEquipo.query.get_or_404(id)
    return jsonify({
        'disponible': equipo.cantidad_disponible,
        'total': equipo.cantidad_total,
        'prestado': equipo.cantidad_prestada
    })


# AGREGAR ESTAS FUNCIONES AL FINAL DE TU app.py (antes del if __name__ == '__main__':)

import pandas as pd
import io
from flask import send_file
from werkzeug.utils import secure_filename
import os


# REEMPLAZAR las funciones de Excel en app.py con estas versiones mejoradas:

@app.route('/equipos/plantilla-excel')
@login_required
def descargar_plantilla_excel():
    """Descarga la plantilla de Excel para importar equipos - Compatible con almacenes"""
    try:
        # Crear un DataFrame con las columnas necesarias
        df = pd.DataFrame(columns=[
            'codigo',
            'nombre',
            'descripcion',
            'categoria',
            'almacen',  # Cambié de 'ubicacion' a 'almacen'
            'cantidad_total',
            'cantidad_minima',
            'fecha_adquisicion',
            'observaciones'
        ])

        # Obtener almacenes disponibles según el usuario
        if current_user.rol in ['admin', 'supervisor']:
            # Admin y supervisor ven todos los almacenes
            ubicaciones_disponibles = Ubicacion.query.all()
        else:
            # Usuario normal solo ve su almacén asignado
            if current_user.area_trabajo:
                ubicaciones_disponibles = Ubicacion.query.filter_by(nombre=current_user.area_trabajo).all()
            else:
                ubicaciones_disponibles = []

        # Agregar ejemplos según los almacenes disponibles
        ejemplos_data = []

        if ubicaciones_disponibles:
            primer_almacen = ubicaciones_disponibles[0].nombre

            ejemplos_data = [
                {
                    'codigo': 'SART-28',
                    'nombre': 'Sartén 28cm',
                    'descripcion': 'Sartén antiadherente de 28cm diámetro',
                    'categoria': 'Ollas y Sartenes',
                    'almacen': primer_almacen,
                    'cantidad_total': 10,
                    'cantidad_minima': 3,
                    'fecha_adquisicion': '2024-01-15',
                    'observaciones': 'Marca XYZ'
                },
                {
                    'codigo': 'CUCH-CHEF-10',
                    'nombre': 'Cuchillo Chef 10"',
                    'descripcion': 'Cuchillo de chef profesional 10 pulgadas',
                    'categoria': 'Equipo de Corte',
                    'almacen': primer_almacen,
                    'cantidad_total': 5,
                    'cantidad_minima': 2,
                    'fecha_adquisicion': '2024-02-20',
                    'observaciones': 'Acero inoxidable'
                }
            ]

        if ejemplos_data:
            ejemplos = pd.DataFrame(ejemplos_data)
            df = pd.concat([df, ejemplos], ignore_index=True)

        # Crear el archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Hoja principal con ejemplos
            df.to_excel(writer, sheet_name='Equipos', index=False)

            # Hoja de instrucciones actualizada
            instrucciones_data = [
                '1. Complete los datos en la hoja "Equipos"',
                '2. El código debe ser único para cada tipo de equipo',
                '3. Las categorías deben coincidir exactamente con las del sistema',
                '4. Los almacenes deben coincidir exactamente con los disponibles',
                '5. Las cantidades deben ser números enteros',
                '6. La fecha debe estar en formato YYYY-MM-DD',
                '7. Puede dejar vacías las columnas de descripción y observaciones',
                '8. Elimine las filas de ejemplo antes de importar'
            ]

            # Agregar restricciones según el rol del usuario
            if current_user.rol not in ['admin', 'supervisor']:
                instrucciones_data.append('9. IMPORTANTE: Solo puede importar equipos para su almacén asignado')
                if current_user.area_trabajo:
                    instrucciones_data.append(f'10. Su almacén asignado es: {current_user.area_trabajo}')

            instrucciones = pd.DataFrame({'Instrucciones': instrucciones_data})
            instrucciones.to_excel(writer, sheet_name='Instrucciones', index=False)

            # Hoja con categorías válidas
            categorias = Categoria.query.all()
            df_categorias = pd.DataFrame({
                'Categorías Válidas': [cat.nombre for cat in categorias],
                'Descripción': [cat.descripcion or 'Sin descripción' for cat in categorias]
            })
            df_categorias.to_excel(writer, sheet_name='Categorias_Validas', index=False)

            # Hoja con almacenes disponibles para este usuario
            almacenes_info = []
            for ub in ubicaciones_disponibles:
                almacenes_info.append({
                    'Almacén': ub.nombre,
                    'Descripción': ub.descripcion or 'Sin descripción',
                    'Responsable': ub.responsable or 'Sin responsable'
                })

            if almacenes_info:
                df_almacenes = pd.DataFrame(almacenes_info)
                df_almacenes.to_excel(writer, sheet_name='Almacenes_Disponibles', index=False)

            # Formatear el Excel
            workbook = writer.book
            worksheet = writer.sheets['Equipos']

            # Formato para encabezados
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            # Aplicar formato a encabezados
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 20)

        output.seek(0)

        # Nombre del archivo según el usuario
        if current_user.rol in ['admin', 'supervisor']:
            filename = 'plantilla_importar_equipos_todos_almacenes.xlsx'
        else:
            almacen_name = current_user.area_trabajo.replace(' ', '_') if current_user.area_trabajo else 'sin_almacen'
            filename = f'plantilla_importar_equipos_{almacen_name}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Error al generar plantilla: {str(e)}', 'danger')
        return redirect(url_for('equipos'))


@app.route('/equipos/importar', methods=['GET', 'POST'])
@login_required
def importar_equipos():
    """Importar equipos desde Excel - Compatible con sistema de almacenes"""

    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)

        archivo = request.files['archivo']

        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)

        if archivo and archivo.filename.endswith(('.xlsx', '.xls')):
            try:
                # Leer el archivo Excel
                df = pd.read_excel(archivo, sheet_name='Equipos')

                # Validar columnas requeridas (actualizado para almacenes)
                columnas_requeridas = ['codigo', 'nombre', 'categoria', 'almacen',
                                       'cantidad_total', 'cantidad_minima']

                for col in columnas_requeridas:
                    if col not in df.columns:
                        flash(f'Falta la columna requerida: {col}', 'danger')
                        return redirect(request.url)

                # Obtener almacenes permitidos para este usuario
                if current_user.rol in ['admin', 'supervisor']:
                    almacenes_permitidos = [ub.nombre for ub in Ubicacion.query.all()]
                else:
                    if current_user.area_trabajo:
                        almacenes_permitidos = [current_user.area_trabajo]
                    else:
                        flash('No tienes un almacén asignado. Contacta al administrador.', 'danger')
                        return redirect(request.url)

                # Procesar cada fila
                equipos_creados = 0
                equipos_actualizados = 0
                errores = []

                for index, row in df.iterrows():
                    try:
                        # Validar permisos de almacén
                        almacen_solicitado = str(row['almacen'])
                        if almacen_solicitado not in almacenes_permitidos:
                            if current_user.rol in ['admin', 'supervisor']:
                                errores.append(
                                    f"Fila {index + 2}: Almacén '{almacen_solicitado}' no existe en el sistema")
                            else:
                                errores.append(
                                    f"Fila {index + 2}: No tienes permisos para el almacén '{almacen_solicitado}'. Solo puedes usar: {', '.join(almacenes_permitidos)}")
                            continue

                        # Verificar si el código ya existe
                        equipo_existente = TipoEquipo.query.filter_by(
                            codigo=str(row['codigo'])
                        ).first()

                        if equipo_existente:
                            # Validar permisos para actualizar
                            if current_user.rol not in ['admin', 'supervisor']:
                                if equipo_existente.ubicacion and equipo_existente.ubicacion.nombre != current_user.area_trabajo:
                                    errores.append(
                                        f"Fila {index + 2}: No tienes permisos para modificar el equipo '{row['codigo']}' (pertenece a otro almacén)")
                                    continue

                            # Actualizar equipo existente
                            equipo_existente.nombre = str(row['nombre'])
                            equipo_existente.descripcion = str(row.get('descripcion', ''))
                            equipo_existente.cantidad_total = int(row['cantidad_total'])
                            equipo_existente.cantidad_minima = int(row['cantidad_minima'])

                            if pd.notna(row.get('observaciones')):
                                equipo_existente.observaciones = str(row['observaciones'])

                            equipos_actualizados += 1
                        else:
                            # Buscar categoría y almacén
                            categoria = Categoria.query.filter_by(
                                nombre=str(row['categoria'])
                            ).first()

                            ubicacion = Ubicacion.query.filter_by(
                                nombre=almacen_solicitado
                            ).first()

                            if not categoria:
                                errores.append(f"Fila {index + 2}: Categoría '{row['categoria']}' no encontrada")
                                continue

                            if not ubicacion:
                                errores.append(f"Fila {index + 2}: Almacén '{almacen_solicitado}' no encontrado")
                                continue

                            # Crear nuevo equipo
                            nuevo_equipo = TipoEquipo(
                                codigo=str(row['codigo']),
                                nombre=str(row['nombre']),
                                descripcion=str(row.get('descripcion', '')),
                                categoria_id=categoria.id,
                                ubicacion_id=ubicacion.id,
                                cantidad_total=int(row['cantidad_total']),
                                cantidad_minima=int(row['cantidad_minima']),
                                observaciones=str(row.get('observaciones', '')) if pd.notna(
                                    row.get('observaciones')) else None
                            )

                            # Manejar fecha de adquisición si existe
                            if pd.notna(row.get('fecha_adquisicion')):
                                try:
                                    nuevo_equipo.fecha_adquisicion = pd.to_datetime(row['fecha_adquisicion']).date()
                                except:
                                    pass

                            db.session.add(nuevo_equipo)
                            equipos_creados += 1

                    except Exception as e:
                        errores.append(f"Fila {index + 2}: {str(e)}")

                # Guardar cambios
                if equipos_creados > 0 or equipos_actualizados > 0:
                    db.session.commit()

                    # Generar códigos QR para los nuevos equipos
                    nuevos_equipos = TipoEquipo.query.filter_by(codigo_qr=None).all()
                    for equipo in nuevos_equipos:
                        qr_data = f"EQUIPO:{equipo.id}:{equipo.codigo}"
                        equipo.codigo_qr = generar_qr(qr_data)

                    db.session.commit()

                # Mostrar resultados
                mensaje = f"Importación completada: {equipos_creados} equipos creados, {equipos_actualizados} actualizados"

                if errores:
                    mensaje += f". Errores: {len(errores)}"
                    for error in errores[:5]:  # Mostrar máximo 5 errores
                        flash(error, 'warning')

                flash(mensaje, 'success' if not errores else 'warning')
                return redirect(url_for('equipos'))

            except Exception as e:
                flash(f'Error al procesar el archivo: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Por favor sube un archivo Excel (.xlsx o .xls)', 'danger')
            return redirect(request.url)

    # Para GET - mostrar información del usuario
    context = {
        'usuario_almacen': current_user.area_trabajo,
        'es_admin': current_user.rol in ['admin', 'supervisor'],
        'almacenes_disponibles': Ubicacion.query.all() if current_user.rol in ['admin', 'supervisor'] else
        Ubicacion.query.filter_by(nombre=current_user.area_trabajo).all()
    }

    return render_template('equipos/importar.html', **context)


@app.route('/equipos/exportar')
@login_required
def exportar_equipos():
    """Exportar equipos a Excel - Filtrado por almacén según permisos"""
    try:
        # Filtrar equipos según permisos del usuario
        if current_user.rol in ['admin', 'supervisor']:
            # Admin y supervisor ven todos los equipos
            equipos = TipoEquipo.query.filter_by(activo=True).all()
            filename_suffix = "todos_almacenes"
        else:
            # Usuario normal solo ve equipos de su almacén
            if current_user.area_trabajo:
                ubicacion = Ubicacion.query.filter_by(nombre=current_user.area_trabajo).first()
                if ubicacion:
                    equipos = TipoEquipo.query.filter_by(activo=True, ubicacion_id=ubicacion.id).all()
                else:
                    equipos = []
                filename_suffix = current_user.area_trabajo.replace(' ', '_')
            else:
                flash('No tienes un almacén asignado. Contacta al administrador.', 'warning')
                return redirect(url_for('equipos'))

        if not equipos:
            flash('No hay equipos para exportar en tu almacén.', 'info')
            return redirect(url_for('equipos'))

        data = []
        for equipo in equipos:
            data.append({
                'codigo': equipo.codigo,
                'nombre': equipo.nombre,
                'descripcion': equipo.descripcion,
                'categoria': equipo.categoria.nombre if equipo.categoria else '',
                'almacen': equipo.ubicacion.nombre if equipo.ubicacion else '',
                'cantidad_total': equipo.cantidad_total,
                'cantidad_minima': equipo.cantidad_minima,
                'cantidad_disponible': equipo.cantidad_disponible,
                'cantidad_prestada': equipo.cantidad_prestada,
                'fecha_adquisicion': equipo.fecha_adquisicion.strftime('%Y-%m-%d') if equipo.fecha_adquisicion else '',
                'observaciones': equipo.observaciones or '',
                'estado_stock': 'CRÍTICO' if equipo.alerta_stock else 'NORMAL'
            })

        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Inventario_Actual', index=False)

            # Formatear
            workbook = writer.book
            worksheet = writer.sheets['Inventario_Actual']

            # Formato para encabezados
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            # Formato para alertas
            alerta_format = workbook.add_format({
                'bg_color': '#FFE6E6',
                'font_color': '#CC0000'
            })

            # Aplicar formato
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 20)

        output.seek(0)

        filename = f'inventario_equipos_{filename_suffix}_{datetime.now().strftime("%Y%m%d")}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Error al exportar: {str(e)}', 'danger')
        return redirect(url_for('equipos'))


# AGREGAR ESTAS RUTAS AL FINAL DE TU app.py (antes del if __name__ == '__main__':)

# ============================================================================
# RUTAS DE GESTIÓN DE USUARIOS
# ============================================================================

@app.route('/configuracion/usuarios/editar', methods=['POST'])
@login_required
def editar_usuario():
    """Editar información completa de un usuario"""
    if current_user.rol != 'admin':
        flash('No tienes permisos para esta acción', 'danger')
        return redirect(url_for('configuracion'))

    try:
        usuario_id = request.form.get('usuario_id')
        usuario = Usuario.query.get_or_404(usuario_id)

        # Actualizar datos básicos
        usuario.username = request.form.get('username')
        usuario.nombre = request.form.get('nombre')
        usuario.email = request.form.get('email')
        usuario.rol = request.form.get('rol')
        usuario.area = request.form.get('area')
        usuario.area_trabajo = request.form.get('area_trabajo')

        # Manejar checkbox de permisos
        usuario.puede_prestar_todas_areas = 'puede_prestar_todas_areas' in request.form
        usuario.activo = 'activo' in request.form

        db.session.commit()
        flash(f'Usuario {usuario.nombre} actualizado exitosamente', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar usuario: {str(e)}', 'danger')

    return redirect(url_for('configuracion'))


@app.route('/configuracion/usuarios/cambiar-password', methods=['POST'])
@login_required
def cambiar_password_usuario():
    """Cambiar contraseña de un usuario"""
    if current_user.rol != 'admin':
        flash('No tienes permisos para esta acción', 'danger')
        return redirect(url_for('configuracion'))

    try:
        usuario_id = request.form.get('usuario_id')
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')

        if nueva_password != confirmar_password:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('configuracion'))

        if len(nueva_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('configuracion'))

        usuario = Usuario.query.get_or_404(usuario_id)
        usuario.set_password(nueva_password)

        db.session.commit()
        flash(f'Contraseña de {usuario.nombre} cambiada exitosamente', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al cambiar contraseña: {str(e)}', 'danger')

    return redirect(url_for('configuracion'))


# BUSCA esta función en tu app.py (línea 1582 aprox) y reemplázala:

@app.route('/configuracion/usuarios/<int:usuario_id>/toggle', methods=['POST'])
@login_required
def toggle_usuario(usuario_id):  # ← AGREGAR el parámetro usuario_id aquí
    """Activar/Desactivar usuario"""
    if current_user.rol != 'admin':
        return jsonify({'error': 'Sin permisos'}), 403

    try:
        usuario = Usuario.query.get_or_404(usuario_id)

        # No permitir que se desactive a sí mismo
        if usuario.id == current_user.id:
            return jsonify({'error': 'No puedes desactivarte a ti mismo'}), 400

        # Obtener el estado del JSON enviado
        data = request.get_json()
        nuevo_estado = data.get('activo', True)

        usuario.activo = nuevo_estado
        db.session.commit()

        accion = 'activado' if nuevo_estado else 'desactivado'
        return jsonify({
            'success': True,
            'message': f'Usuario {usuario.nombre} {accion} exitosamente'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
# BUSCA esta función en tu app.py (línea 1614 aprox) y reemplázala:

@app.route('/configuracion/usuarios/<int:usuario_id>/eliminar', methods=['POST'])
@login_required
def eliminar_usuario(usuario_id):  # ← AGREGAR el parámetro usuario_id aquí
    """Eliminar usuario del sistema"""
    if current_user.rol != 'admin':
        return jsonify({'error': 'Sin permisos'}), 403

    try:
        usuario = Usuario.query.get_or_404(usuario_id)

        # No permitir que se elimine a sí mismo
        if usuario.id == current_user.id:
            return jsonify({'error': 'No puedes eliminarte a ti mismo'}), 400

        # Verificar si el usuario tiene préstamos activos
        prestamos_activos = Prestamo.query.filter(
            Prestamo.usuario_prestamo_id == usuario.id,
            Prestamo.estado.in_(['activo', 'parcial'])
        ).count()

        if prestamos_activos > 0:
            return jsonify({
                'error': f'No se puede eliminar: el usuario tiene {prestamos_activos} préstamos activos'
            }), 400

        # Verificar si es el último administrador
        if usuario.rol == 'admin':
            admins_count = Usuario.query.filter_by(rol='admin', activo=True).count()
            if admins_count <= 1:
                return jsonify({
                    'error': 'No se puede eliminar al último administrador del sistema'
                }), 400

        nombre_usuario = usuario.nombre
        db.session.delete(usuario)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Usuario {nombre_usuario} eliminado exitosamente'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# RUTAS DE GESTIÓN DE CATEGORÍAS
# ============================================================================

@app.route('/configuracion/categorias/editar', methods=['POST'])
@login_required
def editar_categoria():
    """Editar información de una categoría"""
    if current_user.rol != 'admin':
        flash('No tienes permisos para esta acción', 'danger')
        return redirect(url_for('configuracion'))

    try:
        categoria_id = request.form.get('categoria_id')
        categoria = Categoria.query.get_or_404(categoria_id)

        # Verificar que el nuevo nombre no exista
        nuevo_nombre = request.form.get('nombre')
        if nuevo_nombre != categoria.nombre:
            categoria_existente = Categoria.query.filter_by(nombre=nuevo_nombre).first()
            if categoria_existente:
                flash(f'Ya existe una categoría con el nombre "{nuevo_nombre}"', 'danger')
                return redirect(url_for('configuracion'))

        categoria.nombre = nuevo_nombre
        categoria.descripcion = request.form.get('descripcion')

        db.session.commit()
        flash(f'Categoría "{categoria.nombre}" actualizada exitosamente', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar categoría: {str(e)}', 'danger')

    return redirect(url_for('configuracion'))


# BUSCA esta función en tu app.py (línea 1698 aprox) y reemplázala:

@app.route('/configuracion/categorias/<int:categoria_id>/eliminar', methods=['POST'])
@login_required
def eliminar_categoria(categoria_id):  # ← AGREGAR el parámetro categoria_id aquí
    """Eliminar categoría del sistema"""
    if current_user.rol != 'admin':
        return jsonify({'error': 'Sin permisos'}), 403

    try:
        categoria = Categoria.query.get_or_404(categoria_id)

        # Verificar si tiene equipos asociados
        equipos_count = TipoEquipo.query.filter_by(categoria_id=categoria.id).count()
        if equipos_count > 0:
            return jsonify({
                'error': f'No se puede eliminar: la categoría tiene {equipos_count} equipos asociados'
            }), 400

        nombre_categoria = categoria.nombre
        db.session.delete(categoria)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Categoría "{nombre_categoria}" eliminada exitosamente'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# RUTAS DE GESTIÓN DE UBICACIONES
# ============================================================================

@app.route('/configuracion/ubicaciones/editar', methods=['POST'])
@login_required
def editar_ubicacion():
    """Editar información de una ubicación"""
    if current_user.rol != 'admin':
        flash('No tienes permisos para esta acción', 'danger')
        return redirect(url_for('configuracion'))

    try:
        ubicacion_id = request.form.get('ubicacion_id')
        ubicacion = Ubicacion.query.get_or_404(ubicacion_id)

        # Verificar que el nuevo nombre no exista
        nuevo_nombre = request.form.get('nombre')
        if nuevo_nombre != ubicacion.nombre:
            ubicacion_existente = Ubicacion.query.filter_by(nombre=nuevo_nombre).first()
            if ubicacion_existente:
                flash(f'Ya existe una ubicación con el nombre "{nuevo_nombre}"', 'danger')
                return redirect(url_for('configuracion'))

        ubicacion.nombre = nuevo_nombre
        ubicacion.descripcion = request.form.get('descripcion')
        ubicacion.responsable = request.form.get('responsable')

        db.session.commit()
        flash(f'Ubicación "{ubicacion.nombre}" actualizada exitosamente', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar ubicación: {str(e)}', 'danger')

    return redirect(url_for('configuracion'))


# BUSCA esta función en tu app.py (línea 1767 aprox) y reemplázala:

@app.route('/configuracion/ubicaciones/<int:ubicacion_id>/eliminar', methods=['POST'])
@login_required
def eliminar_ubicacion(ubicacion_id):  # ← AGREGAR el parámetro ubicacion_id aquí
    """Eliminar ubicación del sistema"""
    if current_user.rol != 'admin':
        return jsonify({'error': 'Sin permisos'}), 403

    try:
        ubicacion = Ubicacion.query.get_or_404(ubicacion_id)

        # Verificar si tiene equipos asociados
        equipos_count = TipoEquipo.query.filter_by(ubicacion_id=ubicacion.id).count()
        if equipos_count > 0:
            return jsonify({
                'error': f'No se puede eliminar: la ubicación tiene {equipos_count} equipos asociados'
            }), 400

        # Verificar si hay usuarios asignados a esta ubicación
        usuarios_count = Usuario.query.filter_by(area_trabajo=ubicacion.nombre).count()
        if usuarios_count > 0:
            return jsonify({
                'error': f'No se puede eliminar: hay {usuarios_count} usuarios asignados a esta ubicación'
            }), 400

        nombre_ubicacion = ubicacion.nombre
        db.session.delete(ubicacion)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Ubicación "{nombre_ubicacion}" eliminada exitosamente'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/reportes/top-equipos')
@login_required
def api_top_equipos():
    """API para obtener top 10 equipos más prestados"""
    try:
        from sqlalchemy import func

        # Consulta para obtener equipos más prestados
        resultado = db.session.query(
            TipoEquipo.id,
            TipoEquipo.nombre,
            TipoEquipo.codigo,
            func.count(DetallePrestamo.id).label('veces_prestado'),
            func.sum(DetallePrestamo.cantidad).label('total_cantidad'),
            func.sum(
                func.julianday(func.coalesce(Prestamo.fecha_devolucion_real, func.date('now'))) -
                func.julianday(Prestamo.fecha_prestamo)
            ).label('dias_total')
        ).join(DetallePrestamo).join(Prestamo).group_by(TipoEquipo.id).order_by(
            func.count(DetallePrestamo.id).desc()
        ).limit(10).all()

        top_equipos = []
        for equipo in resultado:
            promedio_dias = round(equipo.dias_total / equipo.veces_prestado, 1) if equipo.veces_prestado > 0 else 0

            top_equipos.append({
                'nombre': equipo.nombre,
                'codigo': equipo.codigo,
                'veces_prestado': equipo.veces_prestado,
                'total_cantidad': equipo.total_cantidad,
                'dias_total': round(equipo.dias_total or 0, 1),
                'promedio_dias': promedio_dias
            })

        return jsonify(top_equipos)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reportes/top-usuarios')
@login_required
def api_top_usuarios():
    """API para obtener top 10 usuarios más activos"""
    try:
        from sqlalchemy import func

        # Consulta para obtener usuarios más activos
        resultado = db.session.query(
            Usuario.nombre,
            Usuario.area,
            func.count(Prestamo.id).label('total_prestamos'),
            func.sum(
                func.case(
                    (Prestamo.estado.in_(['activo', 'parcial']), 1),
                    else_=0
                )
            ).label('prestamos_activos'),
            func.sum(
                func.case(
                    (Prestamo.estado == 'devuelto', 1),
                    else_=0
                )
            ).label('prestamos_devueltos')
        ).join(Prestamo, Usuario.id == Prestamo.usuario_prestamo_id).group_by(Usuario.id).order_by(
            func.count(Prestamo.id).desc()
        ).limit(10).all()

        top_usuarios = []
        for usuario in resultado:
            total = usuario.total_prestamos
            devueltos = usuario.prestamos_devueltos or 0
            tasa_devolucion = round((devueltos / total) * 100, 1) if total > 0 else 0

            top_usuarios.append({
                'nombre': usuario.nombre,
                'area': usuario.area or 'Sin área',
                'total_prestamos': total,
                'prestamos_activos': usuario.prestamos_activos or 0,
                'tasa_devolucion': tasa_devolucion
            })

        return jsonify(top_usuarios)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/init-database')
def init_database_endpoint():
    """Endpoint para inicializar la base de datos manualmente en Railway"""
    try:
        print("🔄 Iniciando inicialización manual de base de datos...")
        init_database()
        return jsonify({
            'status': 'success',
            'message': 'Base de datos inicializada correctamente',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        print(f"❌ ERROR al inicializar base de datos: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
if __name__ == '__main__':
    # Inicializar la base de datos
    init_database()

    # Configuración optimizada para Railway
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'

    # Solo ejecutar Flask directamente en desarrollo
    # En producción, gunicorn se encarga del servidor
    if debug_mode:
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        # En producción, Railway usa gunicorn
        print(f"🚀 Aplicación lista para Railway en puerto {port}")
        app.run(host='0.0.0.0', port=port, debug=False)