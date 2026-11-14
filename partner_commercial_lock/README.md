# Protección de representantes comerciales — 18.0.2.0.0

Corrige la vía de reasignación desde la columna **Responsable** de las líneas de cotización (`sale.order.line.x_user_id`) y el alias de cabecera `sale.order.x_responsable_id`, además de conservar la protección de `res.partner.user_id`.

## Política

- Los usuarios sin autorización específica no pueden cambiar ni vaciar representantes de contactos existentes, cotizaciones ni líneas, aunque tengan roles generales de Administrador de Ventas o el antiguo grupo Editar Comercial en Cotizaciones. La restricción explícita anterior tiene prioridad; `sudo` conservando el usuario y banderas de contexto no la eliminan.
- Gerencia de Ventas, Facturación y Administración conservan la edición mediante el nuevo grupo **Administrar asignaciones comerciales**, dentro de sus ACL y empresas habituales. El grupo no concede acceso a empresas/documentos ni operaciones contables adicionales.
- **Excepción expresa de Luis: Claudia Díaz (Nicaragua) queda fuera del bloqueo y conserva sus permisos actuales.** Se comprueba el UID 535 y su login exacto en la decisión de bloqueo, sin añadirle grupos, ACL ni empresas. La migración no modifica su cuenta.
- La concesión inicial o de actualización verifica UID, login, estado activo y pertenencia a MEGATK/MEDITEK para Luis Morán, Mirthy Sauceda, Darcy Vasquez, Elisa Rodriguez, Administración Mega, Noely Fuentes, Yajaira Alvarado y Facturación. No cambia contraseñas, API keys, empresas ni otros grupos salvo la autorización específica y su permiso de edición de pantalla asociado.

## Crear, copiar y editar

Las cotizaciones nuevas creadas por usuarios restringidos toman el representante ya asignado al cliente principal. Si el cliente no tiene representante, la nueva cotización toma al creador sin asignarle el contacto. Las líneas nuevas heredan el representante de la cabecera. Intentar elegir otro responsable, vaciarlo o trasladar líneas existentes entre órdenes falla antes de guardar.

Las copias normales conservan el representante. Copiar o reemplazar líneas con repartos distintos de la cabecera requiere un usuario autorizado para evitar que una copia o eliminación reatribuya la venta. Las ediciones ordinarias de productos/cantidades y los valores de representante sin cambios siguen permitidos. El onchange del producto conserva asignaciones anteriores. La preparación de la factura conserva el responsable de la línea sin emitir documentos para probarlo.

## Validación y publicación

La CI usa Odoo 18/PostgreSQL y datos ficticios. Genera adaptadores aislados para los campos/onchanges de `fields_megatk` y `grupos_accesos` fuera del repositorio; nunca sustituye los módulos reales en producción. Falta validar la integración con los módulos reales en staging antes de actualizar producción.

Para la instancia existente se actualiza el módulo `partner_commercial_lock`; su migración `18.0.2.0.0/post-migration.py` concede los permisos específicos a las cuentas verificadas. Una instalación nueva utiliza `post_init_hook`. No usar facturas reales ni consumir consecutivos fiscales en las pruebas. El conector Sentinel sigue estrictamente de lectura y no ejecuta esta actualización.
