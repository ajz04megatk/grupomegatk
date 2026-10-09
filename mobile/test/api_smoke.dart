// SDK-only checks: dart run test/api_smoke.dart
import '../lib/api.dart';

Future<void> main() async {
  for (final url in [
    'http://example.com',
    'https://example.com/path',
    'https://user:password@example.com',
    'https://example.com?token=x',
  ]) {
    var rejected = false;
    try {
      OdooSavingsRepository(Uri.parse(url), 'test');
    } on ArgumentError {
      rejected = true;
    }
    if (!rejected) throw StateError('Insecure origin accepted: $url');
  }
  final repository = OdooSavingsRepository(
    Uri.parse('https://example.invalid'),
    'test',
  );
  await repository.logout();
  try {
    await repository.investments();
    throw StateError('Read allowed without a session');
  } on LenkaFailure catch (e) {
    if (!e.sessionExpired) rethrow;
  }
  print(
    'PASS: four invalid origins rejected; reads require an active session.',
  );
}
