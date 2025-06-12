from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))  # Aumentado para PostgreSQL
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    rol = db.Column(db.String(50), default='usuario')  # admin, supervisor, usuario
    area = db.Column(db.String(100))

    # 🆕 Campos adicionales para control de acceso
    area_trabajo = db.Column(db.String(100))  # Área específica donde trabaja
    puede_prestar_todas_areas = db.Column(db.Boolean, default=False)  # Super usuario

    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones mejoradas
    prestamos_realizados = db.relationship('Prestamo',
                                           foreign_keys='Prestamo.usuario_prestamo_id',
                                           backref='usuario_prestamo',
                                           lazy='dynamic')
    devoluciones_recibidas = db.relationship('Prestamo',
                                             foreign_keys='Prestamo.usuario_devolucion_id',
                                             backref='usuario_devolucion',
                                             lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Usuario {self.username}>'


class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    equipos = db.relationship('TipoEquipo', backref='categoria', lazy='dynamic')

    def __repr__(self):
        return f'<Categoria {self.nombre}>'


class Ubicacion(db.Model):
    __tablename__ = 'ubicaciones'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text)
    responsable = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    equipos = db.relationship('TipoEquipo', backref='ubicacion', lazy='dynamic')

    def __repr__(self):
        return f'<Ubicacion {self.nombre}>'


class TipoEquipo(db.Model):
    """Representa un tipo de equipo con cantidad total"""
    __tablename__ = 'tipos_equipo'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False, index=True)
    descripcion = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), index=True)
    ubicacion_id = db.Column(db.Integer, db.ForeignKey('ubicaciones.id'), index=True)

    # Cantidades
    cantidad_total = db.Column(db.Integer, default=1, nullable=False)
    cantidad_minima = db.Column(db.Integer, default=1)  # Para alertas

    # Otros campos mejorados para PostgreSQL
    codigo_qr = db.Column(db.Text)  # QR del tipo de equipo
    foto = db.Column(db.String(500))  # Aumentado para URLs largas
    fecha_adquisicion = db.Column(db.Date)
    observaciones = db.Column(db.Text)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)

    # 🆕 Campos adicionales para mejor control
    costo_unitario = db.Column(db.Numeric(10, 2))  # Costo por unidad
    proveedor = db.Column(db.String(200))  # Proveedor
    numero_serie = db.Column(db.String(100))  # Número de serie si aplica
    garantia_hasta = db.Column(db.Date)  # Fecha de vencimiento de garantía

    # Relación
    prestamos = db.relationship('DetallePrestamo', backref='tipo_equipo', lazy='dynamic')

    def __repr__(self):
        return f'<TipoEquipo {self.codigo}: {self.nombre}>'

    @property
    def cantidad_prestada(self):
        """Calcula la cantidad actualmente prestada"""
        try:
            prestamos_activos = DetallePrestamo.query.join(Prestamo).filter(
                DetallePrestamo.tipo_equipo_id == self.id,
                Prestamo.estado.in_(['activo', 'parcial'])
            ).all()

            total_prestado = sum(max(0, p.cantidad - p.cantidad_devuelta) for p in prestamos_activos)
            return total_prestado
        except Exception as e:
            print(f"Error calculando cantidad prestada: {e}")
            return 0

    @property
    def cantidad_disponible(self):
        """Calcula la cantidad disponible para préstamo"""
        try:
            disponible = self.cantidad_total - self.cantidad_prestada
            return max(0, disponible)  # No puede ser negativo
        except Exception as e:
            print(f"Error calculando cantidad disponible: {e}")
            return 0

    @property
    def porcentaje_disponible(self):
        """Porcentaje de equipos disponibles"""
        if self.cantidad_total == 0:
            return 0
        try:
            porcentaje = int((self.cantidad_disponible / self.cantidad_total) * 100)
            return max(0, min(100, porcentaje))  # Entre 0 y 100
        except Exception as e:
            print(f"Error calculando porcentaje: {e}")
            return 0

    @property
    def alerta_stock(self):
        """Indica si el stock está por debajo del mínimo"""
        try:
            return self.cantidad_disponible <= self.cantidad_minima
        except Exception as e:
            print(f"Error verificando alerta stock: {e}")
            return False


class Prestamo(db.Model):
    """Representa un préstamo que puede incluir múltiples tipos de equipo"""
    __tablename__ = 'prestamos'

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(20), unique=True, index=True)  # PRE-2024-0001
    usuario_prestamo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)
    usuario_devolucion_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), index=True)

    # Información del responsable
    responsable_nombre = db.Column(db.String(100), nullable=False, index=True)
    responsable_area = db.Column(db.String(100), index=True)
    responsable_telefono = db.Column(db.String(20))
    responsable_email = db.Column(db.String(120))  # 🆕 Email del responsable

    # Detalles del préstamo
    motivo = db.Column(db.Text)
    evento = db.Column(db.String(200))  # Si es para un evento específico
    ubicacion_destino = db.Column(db.String(200))  # 🆕 Dónde se llevará el equipo

    # Fechas mejoradas
    fecha_prestamo = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    fecha_devolucion_esperada = db.Column(db.DateTime, nullable=False, index=True)
    fecha_devolucion_real = db.Column(db.DateTime, index=True)

    # Estado del préstamo
    estado = db.Column(db.String(50), default='activo', index=True)  # activo, parcial, devuelto, cancelado
    prioridad = db.Column(db.String(20), default='normal')  # alta, normal, baja

    # Observaciones
    observaciones_prestamo = db.Column(db.Text)  # Al momento del préstamo
    observaciones_devolucion = db.Column(db.Text)  # Al momento de la devolución

    # QR y documentos
    codigo_qr_prestamo = db.Column(db.Text)  # QR del préstamo completo

    # 🆕 Campos de auditoría mejorados
    ip_prestamo = db.Column(db.String(45))  # IP desde donde se hizo el préstamo
    ip_devolucion = db.Column(db.String(45))  # IP desde donde se hizo la devolución

    # Relación con los detalles
    detalles = db.relationship('DetallePrestamo', backref='prestamo', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Prestamo {self.folio}>'

    @property
    def vencido(self):
        """Verifica si el préstamo está vencido"""
        if self.estado in ['activo', 'parcial'] and self.fecha_devolucion_esperada:
            return datetime.now() > self.fecha_devolucion_esperada
        return False

    @property
    def dias_prestamo(self):
        """Calcula los días que lleva el préstamo"""
        try:
            if self.fecha_devolucion_real:
                delta = self.fecha_devolucion_real - self.fecha_prestamo
            else:
                delta = datetime.now() - self.fecha_prestamo
            return max(0, delta.days)
        except Exception as e:
            print(f"Error calculando días de préstamo: {e}")
            return 0

    @property
    def total_items(self):
        """Total de items en el préstamo"""
        try:
            return sum(d.cantidad for d in self.detalles)
        except Exception as e:
            print(f"Error calculando total items: {e}")
            return 0

    @property
    def items_pendientes(self):
        """Items que faltan por devolver"""
        try:
            return sum(max(0, d.cantidad - d.cantidad_devuelta) for d in self.detalles)
        except Exception as e:
            print(f"Error calculando items pendientes: {e}")
            return 0

    def generar_folio(self):
        """Genera un folio único para el préstamo"""
        try:
            año = datetime.now().year
            # Buscar el último folio del año
            ultimo = Prestamo.query.filter(
                Prestamo.folio.like(f'PRE-{año}-%')
            ).order_by(Prestamo.id.desc()).first()

            if ultimo and ultimo.folio:
                try:
                    numero = int(ultimo.folio.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    numero = 1
            else:
                numero = 1

            self.folio = f'PRE-{año}-{numero:04d}'
        except Exception as e:
            print(f"Error generando folio: {e}")
            # Folio de respaldo
            import time
            self.folio = f'PRE-{int(time.time())}'


class DetallePrestamo(db.Model):
    """Detalle de cada tipo de equipo en un préstamo"""
    __tablename__ = 'detalles_prestamo'

    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey('prestamos.id'), nullable=False, index=True)
    tipo_equipo_id = db.Column(db.Integer, db.ForeignKey('tipos_equipo.id'), nullable=False, index=True)

    # Cantidades
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    cantidad_devuelta = db.Column(db.Integer, default=0)

    # Estado de devolución
    estado_devolucion = db.Column(db.String(50))  # bueno, dañado, perdido, mantenimiento
    observaciones = db.Column(db.Text)
    fecha_devolucion = db.Column(db.DateTime)

    # 🆕 Campos adicionales para mejor trazabilidad
    condicion_prestamo = db.Column(db.String(50), default='bueno')  # Estado al prestar
    condicion_devolucion = db.Column(db.String(50))  # Estado al devolver
    usuario_devolucion_item_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))  # Quién recibió la devolución

    # Relación adicional
    usuario_devolucion_item = db.relationship('Usuario', foreign_keys=[usuario_devolucion_item_id])

    def __repr__(self):
        return f'<DetallePrestamo: {self.cantidad} x {self.tipo_equipo.nombre if self.tipo_equipo else "N/A"}>'

    @property
    def pendiente(self):
        """Cantidad pendiente de devolver"""
        try:
            return max(0, self.cantidad - self.cantidad_devuelta)
        except Exception as e:
            print(f"Error calculando pendiente: {e}")
            return 0

    @property
    def devuelto_completo(self):
        """Si se devolvió toda la cantidad"""
        try:
            return self.cantidad_devuelta >= self.cantidad
        except Exception as e:
            print(f"Error verificando devolución completa: {e}")
            return False


# 🛠️ FUNCIONES DE UTILIDAD PARA POSTGRESQL

def crear_indices_adicionales():
    """Crear índices adicionales para mejorar performance en PostgreSQL"""
    try:
        # Solo crear índices si estamos usando PostgreSQL
        if 'postgresql' in str(db.engine.url):
            db.engine.execute(
                'CREATE INDEX IF NOT EXISTS idx_prestamos_estado_fecha ON prestamos(estado, fecha_prestamo)')
            db.engine.execute(
                'CREATE INDEX IF NOT EXISTS idx_equipos_disponibilidad ON tipos_equipo(activo, cantidad_total)')
            db.engine.execute(
                'CREATE INDEX IF NOT EXISTS idx_detalles_prestamo_estado ON detalles_prestamo(prestamo_id, cantidad, cantidad_devuelta)')
            print("✅ Índices adicionales creados para PostgreSQL")
    except Exception as e:
        print(f"⚠️ No se pudieron crear índices adicionales: {e}")


def optimizar_postgresql():
    """Configuraciones específicas para PostgreSQL"""
    try:
        if 'postgresql' in str(db.engine.url):
            # Configurar timezone
            db.engine.execute("SET timezone = 'UTC'")
            print("✅ Timezone configurado para PostgreSQL")
    except Exception as e:
        print(f"⚠️ No se pudo optimizar PostgreSQL: {e}")