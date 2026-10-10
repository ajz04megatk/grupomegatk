# Desglose de intereses y retiros — 9 octubre 2026, Honduras

Se exponen los campos existentes tax_amount/net_amount de intereses y gross_interest_amount/interest_tax_amount de retiros en el servicio móvil. La app muestra retención e interés neto en movimientos de interés; capital, interés bruto, retención e interés neto en retiros. No se alteran cálculos, impuestos ni asientos de Odoo.

El historial advierte que los intereses pagados pueden estar incluidos en un retiro y no deben sumarse como entradas separadas. Se conservan monedas y totales originales.

Ejecutado: verificación conjunta SDK-only aprobada, 34 comprobaciones financieras, 35 de presentación, 10 de estados y 9 de inactividad, escenarios de API/sesiones/respuestas, nueve pruebas Python. Compilación sintáctica del servicio correcta. Sin Flutter ni Odoo real.

Compatibilidad: para probar este desglose deben actualizarse juntos el servicio móvil y la app en staging. Si el servidor no entrega los campos requeridos, la app rechaza el detalle incompleto, no inventa una retención cero. Pendientes pruebas ORM/integración, pantallas y dispositivos. No instalado en producción.
