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
Cerrar sesión elimina la sesión local; todavía falta revocación remota de sesión.
Tampoco se ha implementado biometría, bloqueo al pasar a segundo plano,
estados de cuenta ni distribución en tiendas.

## Verificaciones

Las pruebas widget están en `test/savings_test.dart`; no confundirlas con pruebas
en teléfono. `test/api_smoke.dart` ejecuta validaciones sin depender de Flutter.
Las pruebas Odoo de privacidad están en `lenka_financiero/tests/test_mobile_privacy.py`.
Nunca ejecutar pruebas que creen registros sobre la base de producción.
