# Sesiones — 9 octubre 2026, Tegucigalpa

Se verificó con un transporte HTTP simulado, sin red ni datos reales:
- La autenticación no sigue redirecciones.
- Se usa la cookie de la sesión correspondiente a cada consulta.
- Cerrar sesión intenta invocar el cierre remoto y borra inmediatamente la sesión local.
- Una respuesta recibida después del cierre no se acepta.
- Una conexión que termina de abrirse después del cierre se aborta sin enviar datos.
- AccessError revoca la sesión local; no se reutiliza para otra consulta.
- Una autenticación tardía no restaura la sesión después de que el usuario la cerró.

Dart analyze lib/api.dart test/session_smoke.dart: sin incidencias.
Dart test/session_smoke.dart: aprobado.
Las 21 validaciones financieras y las pruebas básicas de conexión siguen aprobadas.

Pendiente: ejecución Flutter/widget, pruebas Odoo de aislamiento en staging, expiración efectiva del servidor, pruebas de dispositivos y APK/IPA. Estos resultados NO acreditan una integración real. El bloqueo previo de Flutter no se reintentó. Producción sin modificaciones.
