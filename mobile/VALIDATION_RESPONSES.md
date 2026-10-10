# Validación de respuestas — 10 octubre 2026

Se rechazan identidades de autenticación nulas, falsas, textuales, cero o negativas y sesiones sin cookie. Las respuestas de consulta se limitan a 4 MiB antes de interpretar JSON, también cuando llegan en fragmentos. Un exceso muestra un mensaje en español y cancela la solicitud; no trunca ni presenta saldos parciales.

Ejecutado con Dart SDK, sin red: análisis estático sin incidencias; response_smoke.dart y session_smoke.dart aprobados. Se comprobó el reintento válido después de respuestas rechazadas.

Pendiente: Flutter/widget, compilaciones Android/iOS y conexión real con Odoo en pruebas. Este cambio no se instaló en producción. El límite requiere observar historiales reales en staging; si resultara insuficiente, implementar paginación antes de distribuir.
