# Lenka Clientes — aplicación en desarrollo

Flutter para Android/iPhone. Pantallas: ingreso, depósitos, detalle, historial
de intereses y retiros. Consulta sin operaciones de dinero.

## Ejecutar en un entorno de pruebas

Instalar Flutter estable y ejecutar desde esta carpeta:

```sh
flutter create --platforms=android,ios --project-name lenka_clientes .
flutter pub get
flutter analyze
flutter test
flutter run --dart-define=LENKA_ORIGIN=https://SERVIDOR-DE-PRUEBAS --dart-define=LENKA_DATABASE=BASE-DE-PRUEBAS
```

Los identificadores son de desarrollo: definir identificadores definitivos y
firma antes de distribuir. Android necesita el permiso INTERNET en el manifest
principal. iPhone requiere macOS/Xcode. No incluir cuentas o claves en el código.
El servidor se fija en la compilación, no lo elige el cliente en un formulario.

## Autenticación y pendientes

Se utiliza sesión Odoo autenticada vía HTTPS, solo en memoria. Debe probarse
contra un usuario portal móvil en staging, incluido el acceso revocado.
No habilitar usuarios reales hasta completar pruebas de aislamiento de empresa
y contacto, expiración, compatibilidad 2FA y recuperación de contraseña.
Cerrar sesión elimina de inmediato la sesión local e intenta revocarla en Odoo con un tiempo de espera limitado. Si no hay conexión, no se afirma que la revocación remota haya ocurrido.
Se añadieron estados de cuenta emitidos, filtros de ahorros/créditos, identidad visual oficial y una cubierta de privacidad al pasar a segundo plano. No equivale a bloquear capturas del sistema operativo. El cierre por inactividad de cinco minutos está implementado, pero su integración visual sigue pendiente de pruebas Flutter/dispositivo. Faltan biometría y distribución en tiendas.

## Verificaciones

Las pruebas widget están en `test/savings_test.dart`; no confundirlas con pruebas
en teléfono. `test/api_smoke.dart` ejecuta validaciones sin depender de Flutter.
Las pruebas Odoo de privacidad están en `lenka_financiero/tests/test_mobile_privacy.py`.
Nunca ejecutar pruebas que creen registros sobre la base de producción.

Para repetir todas las comprobaciones locales sin ejecutar Flutter ni conectar a Odoo:

```sh
python verify_offline.py --dart /RUTA/AL/SDK/dart
```

En Windows usar la ruta completa a `dart.exe`. El comando verifica el ícono
original, analiza los módulos Dart independientes, ejecuta ocho suites Dart y
catorce pruebas Python y una comprobación del contrato de datos Python/Dart. No compila APK/IPA, no instala nada y no valida pantallas
ni las reglas de acceso del ORM de Odoo. Esas comprobaciones siguen pendientes.

El estado y los requisitos para continuar están en `RELEASE_READINESS.md`.
