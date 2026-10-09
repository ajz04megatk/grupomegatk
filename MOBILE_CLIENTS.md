# Lenka para clientes — desarrollo iniciado 9 octubre 2026

Objetivo autorizado: iPhone y Android para consultar ahorros en Odoo.

## Primera entrega

- Inicio de sesión individual; habilitación explícita del cliente por Lenka.
- Mis ahorros: capital vigente separado en HNL y USD.
- Intereses en un renglón independiente. El interés acumulado del modelo incluye
  intereses históricos pagados: nunca llamarlo saldo disponible ni sumarlo al capital.
- Detalle de depósitos, vencimiento, intereses y retiros registrados.
- Estados de cuenta emitidos. Actualizar, carga, sin depósitos y error en español.
- Consulta solamente. No habilitar transferencias o retiros desde el teléfono.

## Avance concreto

El módulo ya tiene rutas autenticadas `/lenka/mobile/v1/` y habilitación de
clientes. Se corrigió en desarrollo el resumen para agrupar cada importe por
moneda. `by_currency` es la fuente de la pantalla; los totales antiguos devuelven
null si hay más de una moneda o ningún registro. No hay conversión implícita.
Las cinco pruebas unitarias se ejecutan con:

    python3 -m unittest discover -s mobile-tests -v

## Pendiente antes de conectar clientes reales

1. Aplicación móvil y autenticación con sesiones revocables, sin credenciales
   administrativas ni claves incrustadas; definir recuperación de acceso.
2. Validar aislamiento por cliente, contacto comercial y empresa en Odoo real.
   Las búsquedas actuales usan sudo y child_of: no dar por aprobado su aislamiento
   sin pruebas de intentos cruzados y política explícita para contactos hijos.
3. Pruebas de integración HTTP y compatibilidad del resumen actualizado.
4. Compilar, firmar y probar iPhone/Android; distribución de pruebas y tiendas.

Este avance vive en una rama separada. No modifica la instalación de producción.
No hay APK ni IPA listo todavía. No se habilitaron clientes ni se copiaron sus datos.
