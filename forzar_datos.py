# forzar_datos.py
import os
import sys
import qrcode
from io import BytesIO
import base64

# Agregar el directorio actual al path para importar desde app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar desde app.py después de agregar al path
from app import app, db, Usuario, TipoEquipo, Categoria, Ubicacion


def generar_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    buffered.seek(0)
    return base64.b64encode(buffered.getvalue()).decode()


def crear_datos_completos():
    with app.app_context():
        print("🚀 Creando datos de ejemplo...")

        # Crear ubicaciones
        ubicaciones = [
            ('Almacén Compras', 'Utensilios generales'),
            ('Almacén Calidad e Higiene', 'Instrumentos de medición'),
            ('Almacén Equipo Especial', 'Maquinaria especializada')
        ]

        for nombre, desc in ubicaciones:
            if not Ubicacion.query.filter_by(nombre=nombre).first():
                ubicacion = Ubicacion(nombre=nombre, descripcion=desc)
                db.session.add(ubicacion)
                print(f"✅ Ubicación: {nombre}")
        db.session.commit()

        # Crear categorías
        categorias = [
            'Utensilios Básicos',
            'Cuchillos y Herramientas de Corte',
            'Contenedores y Recipientes',
            'Instrumentos de Medición',
            'Balanzas de Precisión',
            'Maquinaria de Repostería'
        ]

        for cat in categorias:
            if not Categoria.query.filter_by(nombre=cat).first():
                categoria = Categoria(nombre=cat, descripcion=f"Categoría {cat}")
                db.session.add(categoria)
                print(f"✅ Categoría: {cat}")
        db.session.commit()

        # Crear equipos
        equipos = [
            {
                'codigo': 'COMP-CUCH-001',
                'nombre': 'Cuchillo Chef 8"',
                'categoria': 'Cuchillos y Herramientas de Corte',
                'ubicacion': 'Almacén Compras',
                'total': 15,
                'min': 5
            },
            {
                'codigo': 'COMP-ESP-001',
                'nombre': 'Set Espátulas de Silicón',
                'categoria': 'Utensilios Básicos',
                'ubicacion': 'Almacén Compras',
                'total': 12,
                'min': 3
            },
            {
                'codigo': 'CAL-TERM-001',
                'nombre': 'Termómetro Digital',
                'categoria': 'Instrumentos de Medición',
                'ubicacion': 'Almacén Calidad e Higiene',
                'total': 6,
                'min': 2
            },
            {
                'codigo': 'ESP-BAT-001',
                'nombre': 'Batidora Planetaria 20L',
                'categoria': 'Maquinaria de Repostería',
                'ubicacion': 'Almacén Equipo Especial',
                'total': 2,
                'min': 1
            }
        ]

        equipos_creados = 0
        for eq in equipos:
            if not TipoEquipo.query.filter_by(codigo=eq['codigo']).first():
                categoria = Categoria.query.filter_by(nombre=eq['categoria']).first()
                ubicacion = Ubicacion.query.filter_by(nombre=eq['ubicacion']).first()

                if categoria and ubicacion:
                    nuevo_equipo = TipoEquipo(
                        codigo=eq['codigo'],
                        nombre=eq['nombre'],
                        categoria_id=categoria.id,
                        ubicacion_id=ubicacion.id,
                        cantidad_total=eq['total'],
                        cantidad_minima=eq['min']
                    )
                    db.session.add(nuevo_equipo)
                    db.session.commit()

                    # Generar QR
                    qr_data = f"EQUIPO:{nuevo_equipo.id}:{nuevo_equipo.codigo}"
                    nuevo_equipo.codigo_qr = generar_qr(qr_data)
                    db.session.commit()

                    equipos_creados += 1
                    print(f"✅ Equipo: {eq['codigo']} - {eq['nombre']}")
                else:
                    print(f"❌ Error: No se encontró categoría '{eq['categoria']}' o ubicación '{eq['ubicacion']}'")

        print(f"\n🎉 ¡Datos creados!")
        print(f"📊 Equipos creados: {equipos_creados}")
        print(f"📊 Total equipos en BD: {TipoEquipo.query.count()}")
        print("🌐 Ve a http://localhost:5000/equipos")


if __name__ == "__main__":
    crear_datos_completos()