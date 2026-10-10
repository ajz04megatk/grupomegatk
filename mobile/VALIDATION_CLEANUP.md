# Cierre y privacidad inicial — 9 octubre 2026, Honduras

El desmontaje de la aplicación invalida la sesión y detiene el control de inactividad. No se depende únicamente del desmontaje de la pantalla de ahorros. La cubierta de privacidad consulta el estado de ciclo de vida al crearse: si ya está inactiva o aún no se ha reanudado, comienza cerrada.

Ejecutado: análisis Dart de coordinador y pruebas sin incidencias; catorce comprobaciones de sesión aprobadas, incluyendo cuatro nuevas de ingreso pendiente cancelado y dos ingresos que terminan en distinto orden.

Prueba widget de creación de la cubierta estando ya en segundo plano añadida: NO ejecutada. Los procesos terminados por el sistema operativo pueden no ejecutar dispose; no se garantiza revocación remota si el proceso muere o no hay red. La sesión local solo reside en memoria. Verificación en dispositivos, Flutter y Odoo real pendiente.
