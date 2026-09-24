# Piloto de Inversiones Lenka

## Alcance

El piloto utiliza el modulo `lenka_financiero` en Odoo 18. Android y iPhone quedan para una fase posterior. La instalacion del piloto no requiere reconectar Supabase.

El codigo se desarrolla en `ajz04megatk/grupomegatk`, rama `lenka-pilot`. El proyecto de Odoo.sh utiliza otro repositorio: `rzavalatk/grupomegatk`. Tener el codigo y las pruebas aprobadas en el primero no significa que el piloto este instalado en el segundo.

## Publicacion autorizada

1. Trabajar con la cuenta `ajz04megatk`. El conector de ChatGPT puede rechazar escrituras en `rzavalatk/grupomegatk` aunque la sesion de navegador de ese usuario si tenga permisos. No confundir ese rechazo con falta de acceso del usuario ni exigir iniciar sesion como `rzavalatk`. La alternativa de navegador ya fue autorizada para este piloto.
2. Leer el HEAD actual de `master` en ese repositorio y comprobar si ya existe `lenka-pilot`. Si existe, revisar su contenido antes de actualizarla.
3. Crear la nueva rama desde el HEAD del repositorio de destino, incorporando solamente `lenka_financiero` desde una revision validada del repositorio de desarrollo. Conservar todos los demas archivos y submodulos del destino.
4. Mantener la rama como entorno Development en Odoo.sh. No mover `master`, no reutilizar entornos de otros aplicativos y no contratar recursos adicionales.
5. Esperar la construccion, revisar el registro de instalacion e instalar el modulo en la base del piloto si aun no esta instalado. Para versiones posteriores, actualizar el modulo en esa misma base de desarrollo.
6. Ejecutar los casos de aceptacion siguientes con datos de prueba. Registrar revision, fecha, URL del piloto y resultados antes de entregar el acceso.

No ejecutar el flujo `publish-v28.yml` del repositorio de destino: corresponde a otro aplicativo y modifica `master`.

## Publicacion verificada el 24 de septiembre de 2026

- Cuenta de GitHub y Odoo.sh: `ajz04megatk`.
- Rama destino creada desde `master`: `rzavalatk/grupomegatk:lenka-pilot`, clasificada automaticamente como Development.
- Preparacion: rama `ajz04megatk/grupomegatk:lenka-odoo18-release`, basada en el HEAD del destino e incorporando exclusivamente los 55 archivos de Lenka.
- Incorporacion mediante la interfaz de GitHub: PR https://github.com/rzavalatk/grupomegatk/pull/27, fusionada en `lenka-pilot`.
- Commit destino: `b699d220ff7053f5e92697b1e97823e99b10b737`.
- Arbol del modulo: `4661b1ab248e98c4ff42ac1f83302ed2a64c95e5`, identico al validado con 192 pruebas sin fallos.
- Configuracion especifica de la rama: instalar `lenka_financiero` y ejecutar pruebas de los modulos seleccionados. No heredar la instalacion de todos los aplicativos del repositorio.
- Odoo.sh reconocio ambos commits y puso la construccion en cola. Este registro confirma publicacion y configuracion; la disponibilidad de la base y la validacion visual deben comprobarse cuando termine la construccion.

En futuras actualizaciones, preparar desde el HEAD actual de la rama destino, conservar los demas archivos, comparar el alcance y fusionar exclusivamente hacia `lenka-pilot`. No cambiar permisos ni usar credenciales del propietario para suplir el limite del conector.

## Casos de aceptacion de reestructuracion

Usar una operacion activa con capital pendiente de 100.000, intereses exigibles de 3.000 y mora pendiente de 200. Los intereses de cuotas futuras no forman parte de los 3.000. Seleccionar una nueva tasa de 2% mensual y el metodo de solo intereses para comprobar facilmente la primera cuota.

| Caso | Accion | Resultado esperado |
| --- | --- | --- |
| Capitalizar | Elegir sumar intereses y mora, actualizar saldos y aprobar | Nuevo capital de 103.200; primer interes mensual de 2.064 |
| Cobrar por separado | Elegir cobrar intereses y mora antes del traslado | Nuevo capital de 100.000; preparar queda bloqueado hasta registrar los 3.200 de pago efectivo |
| Pago completo | Registrar los 3.200 y preparar la sucesora | Primer interes mensual de 2.000 sobre capital de 100.000 |
| Cambio de saldos | Registrar pagos o cambios de mora despues de aprobar | Exigir revision y nueva aprobacion cuando cambien los saldos relevantes |
| Identidad | Intentar cambiar cliente, moneda, empresa o tipo de la sucesora | Rechazar el cambio incluso antes de firmar |
| Contrato pendiente | Intentar completar sin contratar la sucesora | Mantener la operacion original activa y sin traslado |
| Traslado | Firmar el contrato y completar la reestructuracion | Activar la sucesora y cerrar la original; saldo original cero |
| Efectivo | Revisar desembolsos y cobros del traslado | No generar un desembolso ni registrar la deuda trasladada como cobro |
| Repeticion | Pulsar nuevamente completar | No duplicar deuda, traslado ni cobros |
| Estado de cuenta | Generar el estado de la original | Mostrar el traslado con referencia a la sucesora y saldo final cero |
| Permisos | Intentar aprobar o completar con un operador | Reservar estas acciones al gerente |

Cada caso que cambie saldos debe usar su propia operacion de prueba o volver expresamente al estado de revision antes de aprobar de nuevo. No reutilizar un contrato firmado para modificar la negociacion.

## Casos de aceptacion de inversiones

- Verificar que un retiro anticipado parcial conserve la tasa reducida contractual de 1% mensual sobre el capital restante.
- Verificar un periodo mensual completo y un periodo parcial: el mes completo conserva su interes mensual y la fraccion utiliza dias reales divididos entre 30.
- Comprobar una inversion iniciada el 31 de enero: febrero utiliza su ultimo dia y marzo recupera el dia 31 como aniversario.
- Revisar que el estado muestre interes bruto, retencion y pago neto sin duplicar intereses ya pagados.
- Verificar que un retiro total deje el saldo en cero y que los movimientos pagados o contabilizados no puedan alterarse directamente.

## Evidencia y recuperacion

La validacion automatizada incluye instalacion limpia, pruebas del modulo, instalacion de demostracion y comprobaciones HTTP y ORM. Conservar el enlace de la ejecucion correspondiente a la revision publicada; una ejecucion anterior no valida cambios posteriores.

Si falla la construccion del piloto, corregir en la rama de desarrollo y repetir la validacion. Si una actualizacion modifica datos, revertir codigo por si solo no revierte esos datos: recuperar la base de desarrollo o reconstruir el piloto segun corresponda. Cualquier paso hacia produccion requiere una decision separada.
