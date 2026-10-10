# Consultas móviles — 9 octubre 2026, Honduras

Corregido: el detalle directo de operaciones no filtraba estados, aunque el listado sí. Ahora dashboard, listado y detalle aplican los mismos estados permitidos. Listados de depósitos también usan una lista explícita de estados publicados. Se mantiene la restricción por contacto exacto y empresas autorizadas; no se concede acceso adicional.

Ejecutado sin Odoo, base de datos ni red: 9 pruebas Python (5 de totales por moneda y 4 de consultas/habilitación). Las pruebas nuevas ejecutan los métodos reales del servicio con un registrador simulado de búsquedas: verifican filtros en las seis consultas, y ausencia de búsquedas cuando falta contacto, grupo móvil o habilitación. No validan reglas ORM ni sustituyen integración.

Añadidas 2 pruebas TransactionCase para operaciones no publicadas y cotizaciones aprobadas: pendientes de ejecutar dentro de Odoo en una base aislada. Compilación sintáctica Python correcta.

Cambios guardados únicamente en lenka-mobile-savings. Sin instalación en producción ni gastos.
