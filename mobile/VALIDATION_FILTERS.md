# Búsqueda de depósitos — 9 octubre 2026, Honduras

Se añade búsqueda por nombre/referencia del depósito y filtros Todas las monedas/Lempiras/Dólares. La búsqueda ignora mayúsculas y tildes en vocales, admite varias palabras y se combina con la moneda. No realiza solicitudes adicionales ni guarda consultas en disco. Los totales generales permanecen sin filtrar y la interfaz lo aclara. Se diferencia cartera vacía de búsqueda sin coincidencias.

Ejecutado: análisis Dart puro sin incidencias; 31 comprobaciones de presentación aprobadas, seis nuevas para filtros y conservación de totales. Prueba widget agregada de búsqueda más moneda, pendiente de Flutter. Se ajustó la navegación de una prueba existente para recorrer la lista antes de abrir un depósito.

Pendiente: revisión visual, teclado, accesibilidad y pruebas en dispositivos/Odoo staging. Sin cambios de producción.
