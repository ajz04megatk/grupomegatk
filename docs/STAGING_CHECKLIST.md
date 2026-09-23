# Lista de verificación en staging

Esta lista se ejecuta después de instalar o actualizar `megatk_cash_flow_forecast` en Odoo 18.

Antes de staging, GitHub Actions debe completar dos controles: validación estática e instalación/pruebas
automatizadas dentro de un Odoo 18 temporal con PostgreSQL aislado.

## Instalación y seguridad

- La aplicación aparece como **Flujo de caja proyectado** con su propio icono.
- Los grupos Gestor de cobros, Usuario y Administrador aparecen en Ajustes > Usuarios.
- Un gestor de cobros solo ve CxC, cobros esperados e historial de cobros.
- Un usuario del flujo ve bancos, CxC, CxP, promesas y egresos de sus empresas autorizadas.
- Al cambiar la empresa activa, no se mezclan registros de otra empresa.

## Disponible real

- Se puede escoger un diario bancario/tarjeta o una cuenta contable, pero no ambos en la misma línea.
- El saldo contable de Odoo es de solo lectura.
- El disponible real es editable y no crea ningún asiento contable.
- La diferencia contra Odoo y los totales se actualizan correctamente.

## Cuentas por cobrar y pagar

- El botón **Actualizar desde Odoo** reconstruye el detalle de la empresa activa.
- Al día aparece verde; 1–30 días amarillo; 31 días en adelante rojo.
- Solo los créditos de clientes y anticipos/pagos a proveedores aparecen azules.
- Los importes y períodos coinciden con el informe de antigüedad de Odoo.
- Las clasificaciones cubren Clientes, CxC empleados, Grupo Mega, Proveedores, Acreedores, Anticipos, En legal, Por depurar y Por asignar.
- **Actualizar cliente** refresca solo el contacto seleccionado sin borrar el resto de la cartera.
- **Ver documentos** abre las facturas o documentos todavía pendientes del cliente o proveedor.
- En la ficha del cliente se ven el saldo pendiente, las gestiones y las proyecciones del flujo.

## Promesas e historial

- Las semanas 1, 2, 3 y Pendiente aparecen junto al contacto; verde en CxC y rojo en CxP.
- Desde una fila de cartera, **Programar** abre un cobro o pago con empresa, contacto y tipo prellenados.
- Crear, cambiar de semana o retirar una proyección actualiza la insignia sin reconstruir la cartera.
- Una nueva gestión actualiza inmediatamente la última observación y próxima fecha.
- La última observación no se edita directamente; cada cambio se registra como una nueva gestión histórica.
- El historial conserva fecha, autor y todas las gestiones anteriores.
- Cada gestión puede vincularse a una factura y queda publicada en el historial de la factura y del cliente.
- Al seleccionar un cliente o proveedor, se muestran el saldo actual de Odoo, el monto proyectado y el saldo posterior.
- Cuando Odoo ya no muestra deuda abierta, la promesa deja de afectar el flujo sin borrar su historial.

## Egresos recurrentes y proyección

- Planilla, alquiler u otro egreso recurrente se conserva y permite cambiar período y monto.
- Un egreso en dólares usa la tasa de Odoo correspondiente a la fecha seleccionada.
- Los totales de cobros, pagos y saldo acumulado de cada semana son correctos.
- Ninguna operación del módulo crea o modifica asientos, facturas, pagos o conciliaciones.
- Cobros proyectados, pagos a proveedores y egresos manuales/recurrentes aparecen en secciones separadas.
