# Consistencia de movimientos — 9 octubre 2026, Honduras

Se valida que interés bruto = retención + interés neto, tanto en intereses como en retiros. También total de retiro = capital + interés neto. Se comparan centavos enteros y se admite una diferencia máxima de un centavo por el redondeo independiente de componentes. Nunca se modifican los importes recibidos para forzar coincidencias.

Un desglose inconsistente rechaza el detalle completo mediante el mensaje existente de información no validada. No se calcula ni se cambia la tasa de retención.

Ejecutado: comprobación conjunta local aprobada; 40 verificaciones financieras, 35 de presentación, 10 de estados, 9 de inactividad, 14 de coordinación de sesión, escenarios de conexión/respuestas y sesiones; nueve pruebas Python; diez verificaciones de compatibilidad Python-Dart. Análisis puro sin incidencias, ícono original verificado.

Pendientes: Flutter/pantallas, ORM y Odoo real en staging, pruebas Android/iOS. Sin cambios de producción.
