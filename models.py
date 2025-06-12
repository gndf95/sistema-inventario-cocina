from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(50), default='usuario')  # admin, supervisor, usuario
    area = db.Column(db.String(100))  # Área general (para reportes)

    # NUEVOS CAMPOS PARA SISTEMA DE ÁREAS
    area_trabajo = db.Column(db.String(100))  # Área específica de trabajo
    puede_prestar_todas_areas = db.Column(db.Boolean, default=False)  # Override para admin/supervisores

    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    prestamos_realizados = db.relationship('Prestamo',
                                           foreign_keys='Prestamo.usuario_prestamo_id',
                                           backref='usuario_prestamo')
    devoluciones_recibidas = db.relationship('Prestamo',
                                             foreign_keys='Prestamo.usuario_devolucion_id',
                                             backref='usuario_devolucion')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)

    # Relación
    equipos = db.relationship('TipoEquipo', backref='categoria', lazy='dynamic')

    def __repr__(self):
        return f'<Categoria {self.nombre}>'


class Ubicacion(db.Model):
    __tablename__ = 'ubicaciones'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    responsable = db.Column(db.String(100))

    # Relación
    equipos = db.relationship('TipoEquipo', backref='ubicacion', lazy='dynamic')

    def __repr__(self):
        return f'<Ubicacion {self.nombre}>'


class TipoEquipo(db.Model):
    """Representa un tipo de equipo con cantidad total"""
    __tablename__ = 'tipos_equipo'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    ubicacion_id = db.Column(db.Integer, db.ForeignKey('ubicaciones.id'))

    # Cantidades
    cantidad_total = db.Column(db.Integer, default=1, nullable=False)
    cantidad_minima = db.Column(db.Integer, default=1)  # Para alertas

    # Otros campos
    codigo_qr = db.Column(db.Text)  # QR del tipo de equipo
    foto = db.Column(db.String(200))
    fecha_adquisicion = db.Column(db.Date)
    observaciones = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)

    # Relación con préstamos
    prestamos = db.relationship('DetallePrestamo', backref='tipo_equipo', lazy='dynamic')

    def __repr__(self):
        return f'<TipoEquipo {self.codigo}: {self.nombre}>'

    @property
    def cantidad_prestada(self):
        """Calcula la cantidad actualmente prestada"""
        prestamos_activos = DetallePrestamo.query.join(Prestamo).filter(
            DetallePrestamo.tipo_equipo_id == self.id,
            Prestamo.estado == 'activo'
        ).all()

        total_prestado = sum(p.cantidad - p.cantidad_devuelta for p in prestamos_activos)
        return total_prestado

    @property
    def cantidad_disponible(self):
        """Calcula la cantidad disponible para préstamo"""
        return self.cantidad_total - self.cantidad_prestada

    @property
    def porcentaje_disponible(self):
        """Porcentaje de equipos disponibles"""
        if self.cantidad_total == 0:
            return 0
        return int((self.cantidad_disponible / self.cantidad_total) * 100)

    @property
    def alerta_stock(self):
        """Indica si el stock está por debajo del mínimo"""
        return self.cantidad_disponible <= self.cantidad_minima


class Prestamo(db.Model):
    """Representa un préstamo que puede incluir múltiples tipos de equipo"""
    __tablename__ = 'prestamos'

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(20), unique=True)  # PRE-2024-0001
    usuario_prestamo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario_devolucion_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    responsable_nombre = db.Column(db.String(100), nullable=False)
    responsable_area = db.Column(db.String(100))
    responsable_telefono = db.Column(db.String(20))
    motivo = db.Column(db.Text)
    evento = db.Column(db.String(200))  # Si es para un evento específico

    fecha_prestamo = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_devolucion_esperada = db.Column(db.DateTime, nullable=False)
    fecha_devolucion_real = db.Column(db.DateTime)

    estado = db.Column(db.String(50), default='activo')  # activo, parcial, devuelto
    observaciones_devolucion = db.Column(db.Text)

    codigo_qr_prestamo = db.Column(db.Text)  # QR del préstamo completo

    # Relación con los detalles
    detalles = db.relationship('DetallePrestamo', backref='prestamo', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Prestamo {self.folio}>'

    @property
    def vencido(self):
        if self.estado in ['activo', 'parcial'] and self.fecha_devolucion_esperada:
            return datetime.now() > self.fecha_devolucion_esperada
        return False

    @property
    def dias_prestamo(self):
        if self.fecha_devolucion_real:
            delta = self.fecha_devolucion_real - self.fecha_prestamo
        else:
            delta = datetime.now() - self.fecha_prestamo
        return delta.days

    @property
    def total_items(self):
        """Total de items en el préstamo"""
        return sum(d.cantidad for d in self.detalles)

    @property
    def items_pendientes(self):
        """Items que faltan por devolver"""
        return sum(d.cantidad - d.cantidad_devuelta for d in self.detalles)

    def generar_folio(self):
        """Genera un folio único para el préstamo"""
        año = datetime.now().year
        ultimo = Prestamo.query.filter(
            Prestamo.folio.like(f'PRE-{año}-%')
        ).order_by(Prestamo.id.desc()).first()

        if ultimo:
            numero = int(ultimo.folio.split('-')[-1]) + 1
        else:
            numero = 1

        self.folio = f'PRE-{año}-{numero:04d}'


class DetallePrestamo(db.Model):
    """Detalle de cada tipo de equipo en un préstamo"""
    __tablename__ = 'detalles_prestamo'

    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey('prestamos.id'), nullable=False)
    tipo_equipo_id = db.Column(db.Integer, db.ForeignKey('tipos_equipo.id'), nullable=False)

    cantidad = db.Column(db.Integer, nullable=False, default=1)
    cantidad_devuelta = db.Column(db.Integer, default=0)

    estado_devolucion = db.Column(db.String(50))  # bueno, dañado, perdido
    observaciones = db.Column(db.Text)
    fecha_devolucion = db.Column(db.DateTime)

    def __repr__(self):
        return f'<DetallePrestamo: {self.cantidad} x {self.tipo_equipo.nombre}>'

    @property
    def pendiente(self):
        """Cantidad pendiente de devolver"""
        return self.cantidad - self.cantidad_devuelta

    @property
    def devuelto_completo(self):
        """Si se devolvió toda la cantidad"""
        return self.cantidad_devuelta >= self.cantidad