# Lenka Clientes: preparación para pruebas

Fecha: 10 de octubre de 2026. Rama: `lenka-mobile-savings`.

## Estado

Código preparado para continuar la validación; todavía no es una aplicación
lista para distribuir. Este trabajo no instala cambios móviles en producción.

Incluye consulta de depósitos HNL/USD por separado, condiciones, movimientos,
estados de cuenta, filtros, mensajes en español, identidad visual oficial,
cierre de sesión y cierre por inactividad. No realiza transferencias ni retiros.

Al habilitar un cliente nuevo, se asigna únicamente la empresa seleccionada y
los grupos portal/móvil. Una cuenta existente no recibe empresas adicionales.
Las cuentas archivadas y los correos usados por otro contacto se detienen con
un mensaje explicativo. No se crea una contraseña ni se envía una invitación.
El administrador debe completar el acceso mediante el procedimiento de Odoo.

## Evidencia disponible

El verificador local comprueba el ícono original, analiza los módulos Dart sin
Flutter, ejecuta ocho suites Dart, catorce pruebas Python y una comprobación
Python/Dart de los datos publicados. Los dobles de registros no sustituyen al
ORM: los permisos reales deben verificarse en una base Odoo aislada.

Hay pruebas widget y pruebas Odoo de privacidad escritas pero no ejecutadas.
No hay APK/IPA, firma de distribución ni prueba física de Android o iPhone.

## Siguiente bloque, en un entorno autorizado

1. Revisar `flutter doctor -v` en la computadora de desarrollo. Crear los
   proyectos nativos según README, configurar permiso INTERNET de Android y
   ejecutar análisis y pruebas Flutter. Resolver los resultados antes de seguir.
2. Preparar una base Odoo de pruebas separada de la base compartida con O Dental.
   Actualizar allí el módulo junto con la app: el detalle usa campos nuevos.
   Ejecutar las pruebas Odoo, incluidas las de privacidad y habilitación móvil.
3. Usar dos clientes ficticios y dos empresas, con depósitos HNL y USD. Comprobar
   que cada cliente ve exclusivamente sus registros y empresas permitidas,
   tampoco accede a registros ajenos por identificador y no puede escribir datos
   financieros directamente. Verificar cuentas archivadas, correos duplicados,
   usuarios internos y revocación de acceso.
4. Probar autenticación HTTPS real, contraseña incorrecta, política 2FA,
   recuperación de acceso, cierre remoto y pérdida de conexión. Las credenciales
   se introducen en el dispositivo; no se guardan en el repositorio ni en el chat.
5. En teléfono, revisar teclado, texto ampliado, desplazamiento, modo suspendido,
   cubierta de privacidad, inactividad y cierre de sesión durante una consulta.
   Contrastar saldos y movimientos con Odoo, sin mezclar monedas.
6. Solo después de superar esas pruebas, definir identificadores definitivos,
   íconos nativos y firma. iPhone requiere macOS/Xcode. Las cuentas de tienda o
   servicios con costo requieren autorización antes de contratarlos.

## Condición para avanzar

En este entorno la ejecución de Flutter fue rechazada por la revisión automática
de permisos. No se reintenta por otra vía ni se sustituye por una compilación
remota. La siguiente evidencia necesaria es la ejecución en la computadora
autorizada y en Odoo de pruebas. No se afirma que la validación local haya probado
pantallas, autenticación real, permisos del ORM o instalación nativa.
