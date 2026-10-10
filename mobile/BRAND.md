# Identidad visual Lenka

Referencia aprobada por Luis: ícono celeste con símbolo negro, adjuntado el 9 de octubre de 2026 (Honduras). La imagen contiene textura y variaciones tonales. Colores base representativos muestreados de la imagen, no una supuesta guía corporativa preexistente:

- Celeste: #85C6E7. Botones principales, encabezados y selección.
- Negro: #1A1A18. Texto, iconos, foco y progreso.
- Marfil: #EDEBE6. Fondo general y cubierta de privacidad.
- Blanco: superficies de lectura y campos.

Contraste calculado del negro: 9.32:1 sobre celeste, 14.63:1 sobre marfil y 17.43:1 sobre blanco. Se evita texto blanco sobre el celeste claro. Errores conservan el color semántico de error.

Implementación centralizada en lib/brand.dart, usada por la aplicación y la cubierta de privacidad. Prueba del tema añadida, todavía no ejecutada con Flutter. Formateo Dart correcto. Pendientes: revisión visual y accesibilidad en dispositivos, y empaquetado del ícono nativo. Este cambio aplica la paleta; no genera todavía iconos Android/iOS. Sin cambios en Odoo producción.
