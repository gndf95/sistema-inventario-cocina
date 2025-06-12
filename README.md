# 🍳 Sistema de Inventario y Préstamo de Equipo Menor de Cocina

Sistema web desarrollado en Flask para gestionar el inventario, préstamos y devoluciones de equipo menor de cocina en entornos profesionales.

## 📋 Características Principales

- ✅ **Gestión de Inventario**: Control completo de tipos de equipo y unidades individuales
- ✅ **Sistema de Préstamos**: Registro de préstamos con responsables y fechas de devolución
- ✅ **Códigos QR**: Generación automática de QR para equipos y tarjetas de préstamo
- ✅ **Dashboard Responsivo**: Interfaz optimizada para móviles y tablets
- ✅ **Alertas Inteligentes**: Notificaciones de stock bajo y préstamos vencidos
- ✅ **Red Local**: Funciona en la red interna sin necesidad de Internet
- ✅ **Fácil Instalación**: Scripts automatizados para Windows

## 🚀 Instalación Rápida

### Requisitos
- Python 3.7+
- Windows (con scripts .bat incluidos)
- Red local activa

### Pasos de Instalación

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/TU-USUARIO/sistema-inventario-cocina.git
   cd sistema-inventario-cocina
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar firewall** (como administrador)
   ```bash
   configurar_firewall.bat
   ```

4. **Iniciar el sistema**
   ```bash
   iniciar_sistema.bat
   ```

5. **Acceder al sistema**
   - Local: `http://localhost:5000`
   - Red: `http://[IP-SERVIDOR]:5000`

## 🌐 Uso en Red Local

El sistema está configurado para funcionar en red local:

- **Servidor**: Computadora donde se ejecuta el sistema
- **Clientes**: Cualquier dispositivo en la misma red WiFi
- **Puerto**: 5000 (configurable)
- **Acceso móvil**: Compatible con smartphones y tablets

## 📱 Funcionalidades

### Dashboard Principal
- Estadísticas en tiempo real
- Alertas de stock bajo
- Préstamos vencidos
- Accesos rápidos

### Gestión de Equipos
- Alta de nuevos tipos de equipo
- Registro de unidades individuales
- Códigos QR automáticos
- Control de estados (disponible, prestado, mantenimiento)

### Sistema de Préstamos
- Préstamos con código QR
- Asignación de responsables
- Fechas de devolución
- Devoluciones parciales
- Historial completo

### Reportes y Alertas
- Préstamos activos y vencidos
- Equipos con stock bajo
- Historial de movimientos
- Estadísticas de uso

## 🛠️ Estructura del Proyecto

```
sistema-inventario-cocina/
├── app.py                      # Aplicación principal
├── requirements.txt            # Dependencias Python
├── iniciar_sistema.bat         # Script de inicio
├── configurar_firewall.bat     # Configuración de red
├── instalar_como_servicio.bat  # Auto-inicio
├── templates/                  # Plantillas HTML
│   ├── base.html
│   ├── index.html
│   ├── equipos.html
│   └── prestamos.html
├── static/                     # Archivos estáticos
│   ├── css/
│   ├── js/
│   └── img/
└── README.md                   # Este archivo
```

## 🔧 Configuración Avanzada

### Auto-inicio del Sistema
```bash
# Ejecutar como administrador
instalar_como_servicio.bat
```

### Cambiar Puerto
Editar `app.py` línea final:
```python
app.run(host='0.0.0.0', port=NUEVO_PUERTO, debug=False)
```

### Configuración de Red
- **Firewall**: Puerto 5000 debe estar abierto
- **Red**: Todas las computadoras en la misma subred
- **IP Estática**: Recomendada para el servidor

## 📊 Base de Datos

El sistema utiliza SQLite con las siguientes tablas:
- `tipos_equipo`: Catálogo de tipos de equipo
- `unidades_equipo`: Unidades individuales con QR
- `prestamos`: Registro de préstamos
- `prestamo_items`: Items específicos de cada préstamo

## 🔒 Seguridad

- ✅ Sistema solo accesible en red local
- ✅ No expuesto a Internet
- ✅ Autenticación por roles (futuro)
- ✅ Validación de datos
- ✅ Logs de auditoría

## 🛠️ Solución de Problemas

### Error: "Address already in use"
```bash
# Terminar procesos Python existentes
taskkill /f /im python.exe
```

### No se puede acceder desde otras PCs
1. Verificar firewall configurado
2. Confirmar misma red WiFi
3. Probar con IP correcta

### Base de datos corrupta
```bash
# El sistema regenera automáticamente
# O restaurar desde backup
```

## 📞 Soporte

- **Documentación**: Ver `GUIA_DE_INSTALACION.md`
- **Issues**: Usar el sistema de issues de GitHub
- **Wiki**: Documentación adicional en Wiki del proyecto

## 🤝 Contribuciones

Las contribuciones son bienvenidas:

1. Fork del proyecto
2. Crear feature branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver archivo [LICENSE](LICENSE) para detalles.

## 📈 Versiones

- **v1.0**: Sistema básico de inventario y préstamos
- **v1.1**: Interfaz responsive y códigos QR
- **v1.2**: Configuración para red local
- **v2.0**: Sistema de roles y permisos (planeado)

## 🎯 Roadmap

- [ ] Sistema de usuarios y roles
- [ ] Reportes en PDF
- [ ] API REST
- [ ] Notificaciones por email
- [ ] Backup automático
- [ ] Integración con sistemas contables

---

**Desarrollado para optimizar la gestión de equipo menor de cocina en entornos profesionales** 🍳

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)