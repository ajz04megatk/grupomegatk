import 'dart:io';

/// Apply the approved identity to the generated Android project.
/// Run from mobile: dart tool/configure_android.dart
void main() {
  final root = File.fromUri(Platform.script).parent.parent;
  final manifest = File('${root.path}/android/app/src/main/AndroidManifest.xml');
  final source = File('${root.path}/assets/lenka-icon.png');
  if (!manifest.existsSync() || !source.existsSync()) {
    stderr.writeln('Falta el proyecto Android o el icono oficial. No se hicieron cambios.');
    exitCode = 1;
    return;
  }
  final original = manifest.readAsStringSync();
  final applications = RegExp(r'<application\b[^>]*>').allMatches(original).toList();
  if (applications.length != 1) {
    stderr.writeln('No se pudo identificar la configuracion Android. No se hicieron cambios.');
    exitCode = 1;
    return;
  }
  final application = applications.single;
  var tag = application.group(0)!;
  if (!tag.contains('android:label="lenka_clientes"') &&
      !tag.contains('android:label="Lenka"')) {
    stderr.writeln('El nombre Android cambio. Revisar antes de reemplazarlo.');
    exitCode = 1;
    return;
  }
  if (!tag.contains('android:icon="@mipmap/ic_launcher"') &&
      !tag.contains('android:icon="@drawable/lenka_launcher"')) {
    stderr.writeln('El icono Android cambio. Revisar antes de reemplazarlo.');
    exitCode = 1;
    return;
  }
  tag = tag.replaceAll('android:label="lenka_clientes"', 'android:label="Lenka"')
      .replaceAll('android:icon="@mipmap/ic_launcher"',
          'android:icon="@drawable/lenka_launcher"');
  var updated = original.replaceRange(application.start, application.end, tag);
  if (!updated.contains('android.permission.INTERNET')) {
    updated = updated.replaceFirst('<application',
        '<uses-permission android:name="android.permission.INTERNET"/>\n    <application');
  }
  // Keep the uploaded artwork byte-for-byte; Android scales this drawable.
  final target = File('${root.path}/android/app/src/main/res/drawable-nodpi/lenka_launcher.png');
  final backup = File('${manifest.path}.before-lenka');
  if (!backup.existsSync()) manifest.copySync(backup.path);
  target.parent.createSync(recursive: true);
  source.copySync(target.path);
  manifest.writeAsStringSync(updated);
  stdout.writeln('Listo: nombre Lenka, icono oficial y permiso de Internet configurados.');
  stdout.writeln('Respaldo del manifiesto: ${backup.path}');
  stdout.writeln('Falta recompilar y comprobar el APK. No se configuro ningun servidor.');
}
