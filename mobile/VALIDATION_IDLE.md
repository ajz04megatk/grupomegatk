# Cierre por inactividad — 9 octubre 2026, Honduras

Implementado en desarrollo: sesión iniciada al autenticar, cierre después de 5 minutos sin actividad táctil, revisión cada segundo y al regresar de segundo plano. Se elimina la sesión local mediante logout y se retiran las rutas de datos para regresar al ingreso con explicación en español. La revocación remota conserva su comportamiento de mejor esfuerzo si no hay conexión.

Se usa tiempo monotónico (Stopwatch), no la fecha editable del teléfono. Un toque después del vencimiento no renueva la sesión. La política no actúa mientras no se haya autenticado el cliente.

Ejecutado sin Flutter ni red: análisis estático del módulo puro sin incidencias y 9 comprobaciones de la política aprobadas. Prueba widget agregada de salida de saldos y regreso al ingreso: NO ejecutada. Falta revisar en teléfonos suspensión del proceso, teclado/accesibilidad, navegación, sesiones concurrentes y eliminación visual de datos al expirar. No se presenta como seguridad verificada en dispositivo ni como biometría.

Sin cambios en producción ni compilación Android/iOS.
