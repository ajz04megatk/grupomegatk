# Sesión rechazada por Odoo — 9 octubre 2026, Honduras

Se añade SessionBoundary alrededor del repositorio de la aplicación. Cuando una consulta de ahorros, detalle o estados recibe sesión vencida/acceso revocado, avisa una sola vez al navegador central, descarta la sesión y retira las pantallas privadas para volver al ingreso con mensaje. Errores transitorios de conexión permiten reintentar. Una respuesta de una sesión anterior no invalida una nueva ni devuelve datos después del cierre.

Ejecutado: ocho suites Dart y nueve pruebas Python aprobadas mediante verify_offline.py; análisis puro sin incidencias; diez comprobaciones nuevas de coordinación de sesión. Ícono original verificado. Se evita la doble navegación desde la pantalla de ahorros cuando actúa el coordinador.

Prueba widget de revocación y regreso automático añadida: NO ejecutada. Falta comprobar rutas, pantalla oculta, concurrencia y servidor Odoo real en staging/dispositivo. Sin cambios en producción.
