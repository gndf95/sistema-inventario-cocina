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

# Configuración de seguridad
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-super-secreta-feedbit-2024!')

# Configuración de base de datos
if os.environ.get('DATABASE_URL'):
    # Producción (Railway) - PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
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


# Función para generar PDF (simplificada por ahora)
def generar_pdf_prestamo(prestamo):
    # Por ahora retornamos un buffer vacío
    # Puedes implementar la generación de PDF más adelante
    buffer = BytesIO()
    buffer.write(b"PDF en construccion")
    buffer.seek(0)
    return buffer


# Crear tablas y usuario admin
def init_database():
    with app.app_context():
        db.create_all()

        # Crear usuario admin si no existe
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                nombre='Administrador',
                email='admin@feedbit.net',
                rol='admin',
                area='Administración'
            )
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'admin123'))
            db.session.add(admin)

            # Crear ubicación por defecto
            if not Ubicacion.query.first():
                ubicaciones = [
                    Ubicacion(nombre='Almacén Principal', descripcion='Almacén central de equipo'),
                    Ubicacion(nombre='Cocina Principal', descripcion='Área de producción'),
                    Ubicacion(nombre='Área de Eventos', descripcion='Equipo para eventos')
                ]
                for u in ubicaciones:
                    db.session.add(u)

            # Crear categorías por defecto
            categorias_default = [
                ('Ollas y Sartenes', 'Equipo de cocción'),
                ('Utensilios', 'Cucharas, espátulas, pinzas, etc.'),
                ('Equipo de Corte', 'Cuchillos, tablas, mandolinas'),
                ('Contenedores', 'Recipientes, bandejas, bowls'),
                ('Equipo de Medición', 'Básculas, tazas medidoras'),
                ('Equipo de Servicio', 'Platos, charolas, pinzas de servicio')
            ]

            for nombre, desc in categorias_default:
                if not Categoria.query.filter_by(nombre=nombre).first():
                    categoria = Categoria(nombre=nombre, descripcion=desc)
                    db.session.add(categoria)

            db.session.commit()
            print("Base de datos inicializada correctamente!")


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

    # Importar datetime para usarlo en el template
    return render_template('index.html',
                           total_tipos=total_tipos,
                           total_unidades=total_unidades,
                           unidades_disponibles=unidades_disponibles,
                           prestamos_activos=prestamos_activos,
                           equipos_alerta=equipos_alerta,
                           prestamos_vencidos=prestamos_vencidos,
                           prestamos_recientes=prestamos_recientes,
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
@app.route('/prestamos')
@login_required
def prestamos():
    prestamos = Prestamo.query.order_by(Prestamo.fecha_prestamo.desc()).all()
    return render_template('prestamos/lista.html', prestamos=prestamos)


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

    equipos_disponibles = TipoEquipo.query.filter_by(activo=True).all()
    # Filtrar solo los que tienen disponibilidad
    equipos_disponibles = [e for e in equipos_disponibles if e.cantidad_disponible > 0]

    return render_template('prestamos/nuevo.html', equipos=equipos_disponibles)


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
    return render_template('reportes/index.html')


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

    usuarios = Usuario.query.all()
    ubicaciones = Ubicacion.query.all()
    categorias = Categoria.query.all()

    return render_template('configuracion/index.html',
                           usuarios=usuarios,
                           ubicaciones=ubicaciones,
                           categorias=categorias,
                           datetime=datetime)


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
        area=request.form.get('area')
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


# Función para descargar plantilla de Excel
@app.route('/equipos/plantilla-excel')
@login_required
def descargar_plantilla_excel():
    """Descarga la plantilla de Excel para importar equipos"""

    # Crear un DataFrame con las columnas necesarias
    df = pd.DataFrame(columns=[
        'codigo',
        'nombre',
        'descripcion',
        'categoria',
        'ubicacion',
        'cantidad_total',
        'cantidad_minima',
        'fecha_adquisicion',
        'observaciones'
    ])

    # Agregar algunos ejemplos
    ejemplos = pd.DataFrame([
        {
            'codigo': 'SART-28',
            'nombre': 'Sartén 28cm',
            'descripcion': 'Sartén antiadherente de 28cm diámetro',
            'categoria': 'Ollas y Sartenes',
            'ubicacion': 'Almacén Principal',
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
            'ubicacion': 'Cocina Principal',
            'cantidad_total': 5,
            'cantidad_minima': 2,
            'fecha_adquisicion': '2024-02-20',
            'observaciones': 'Acero inoxidable'
        }
    ])

    df = pd.concat([df, ejemplos], ignore_index=True)

    # Crear el archivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Hoja principal con ejemplos
        df.to_excel(writer, sheet_name='Equipos', index=False)

        # Hoja de instrucciones
        instrucciones = pd.DataFrame({
            'Instrucciones': [
                '1. Complete los datos en la hoja "Equipos"',
                '2. El código debe ser único para cada tipo de equipo',
                '3. Las categorías deben coincidir exactamente con las del sistema',
                '4. Las ubicaciones deben coincidir exactamente con las del sistema',
                '5. Las cantidades deben ser números enteros',
                '6. La fecha debe estar en formato YYYY-MM-DD',
                '7. Puede dejar vacías las columnas de descripción y observaciones',
                '8. Elimine las filas de ejemplo antes de importar'
            ]
        })
        instrucciones.to_excel(writer, sheet_name='Instrucciones', index=False)

        # Hoja con categorías válidas
        categorias = Categoria.query.all()
        df_categorias = pd.DataFrame({
            'Categorías Válidas': [cat.nombre for cat in categorias]
        })
        df_categorias.to_excel(writer, sheet_name='Categorias_Validas', index=False)

        # Hoja con ubicaciones válidas
        ubicaciones = Ubicacion.query.all()
        df_ubicaciones = pd.DataFrame({
            'Ubicaciones Válidas': [ub.nombre for ub in ubicaciones]
        })
        df_ubicaciones.to_excel(writer, sheet_name='Ubicaciones_Validas', index=False)

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

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='plantilla_importar_equipos.xlsx'
    )


@app.route('/equipos/importar', methods=['GET', 'POST'])
@login_required
def importar_equipos():
    """Importar equipos desde Excel"""

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

                # Validar columnas requeridas
                columnas_requeridas = ['codigo', 'nombre', 'categoria', 'ubicacion',
                                       'cantidad_total', 'cantidad_minima']

                for col in columnas_requeridas:
                    if col not in df.columns:
                        flash(f'Falta la columna requerida: {col}', 'danger')
                        return redirect(request.url)

                # Procesar cada fila
                equipos_creados = 0
                equipos_actualizados = 0
                errores = []

                for index, row in df.iterrows():
                    try:
                        # Verificar si el código ya existe
                        equipo_existente = TipoEquipo.query.filter_by(
                            codigo=str(row['codigo'])
                        ).first()

                        if equipo_existente:
                            # Actualizar equipo existente
                            equipo_existente.nombre = str(row['nombre'])
                            equipo_existente.descripcion = str(row.get('descripcion', ''))
                            equipo_existente.cantidad_total = int(row['cantidad_total'])
                            equipo_existente.cantidad_minima = int(row['cantidad_minima'])

                            if pd.notna(row.get('observaciones')):
                                equipo_existente.observaciones = str(row['observaciones'])

                            equipos_actualizados += 1
                        else:
                            # Buscar categoría y ubicación
                            categoria = Categoria.query.filter_by(
                                nombre=str(row['categoria'])
                            ).first()

                            ubicacion = Ubicacion.query.filter_by(
                                nombre=str(row['ubicacion'])
                            ).first()

                            if not categoria:
                                errores.append(f"Fila {index + 2}: Categoría '{row['categoria']}' no encontrada")
                                continue

                            if not ubicacion:
                                errores.append(f"Fila {index + 2}: Ubicación '{row['ubicacion']}' no encontrada")
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

    return render_template('equipos/importar.html')


@app.route('/equipos/exportar')
@login_required
def exportar_equipos():
    """Exportar todos los equipos a Excel"""

    equipos = TipoEquipo.query.filter_by(activo=True).all()

    data = []
    for equipo in equipos:
        data.append({
            'codigo': equipo.codigo,
            'nombre': equipo.nombre,
            'descripcion': equipo.descripcion,
            'categoria': equipo.categoria.nombre if equipo.categoria else '',
            'ubicacion': equipo.ubicacion.nombre if equipo.ubicacion else '',
            'cantidad_total': equipo.cantidad_total,
            'cantidad_minima': equipo.cantidad_minima,
            'cantidad_disponible': equipo.cantidad_disponible,
            'cantidad_prestada': equipo.cantidad_prestada,
            'fecha_adquisicion': equipo.fecha_adquisicion.strftime('%Y-%m-%d') if equipo.fecha_adquisicion else '',
            'observaciones': equipo.observaciones or ''
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

        # Aplicar formato
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)

    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'inventario_equipos_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )
if __name__ == '__main__':
    # Inicializar la base de datos
    init_database()

    # Configuración para Railway
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)