# Compatibilidad del servicio y la app — 9 octubre 2026, Honduras

Nueva comprobación conjunta: service_contract_fixture.py ejecuta los métodos reales de serialización del servicio móvil con registros ficticios HNL/USD y relaciones simuladas. Genera JSON temporal, que contract_smoke.dart procesa usando los validadores y presentadores reales de la app.

Resultado: diez verificaciones aprobadas de cantidad de registros, separación de monedas, saldos, interés neto, retiro y período de tasa. Los movimientos en borrador no se incluyen y las notas internas ficticias no se serializan. El archivo temporal se elimina al terminar.

También aprobaron las ocho suites Dart previas, nueve pruebas Python, análisis Dart puro y verificación del ícono. Todo reunido en verify_offline.py.

Alcance: valida compatibilidad entre Python y Dart y filtros de relaciones, no ORM, reglas reales de registros, autenticación HTTP ni conectividad Odoo. Flutter, dispositivos y staging siguen pendientes. Sin datos reales, cambios de producción ni gastos.
