import 'dart:async';

import '../lib/api.dart';
import '../lib/session_boundary.dart';

class Repository implements SavingsRepository {
  final reads = <Completer<List<Map<String, dynamic>>>>[];
  int logouts = 0;
  @override
  Future<void> login(String email, String password) async {}
  @override
  Future<void> logout() async {
    logouts++;
  }

  @override
  Future<List<Map<String, dynamic>>> investments() {
    final pending = Completer<List<Map<String, dynamic>>>();
    reads.add(pending);
    return pending.future;
  }

  @override
  Future<Map<String, dynamic>> detail(int id) async =>
      throw const LenkaFailure('Acceso deshabilitado.', sessionExpired: true);
  @override
  Future<List<Map<String, dynamic>>> statements() => investments();
}

void check(bool value, String message) {
  if (!value) throw StateError(message);
}

Future<bool> rejected(Future<dynamic> future) async {
  try {
    await future;
    return false;
  } on LenkaFailure {
    return true;
  }
}

Future<void> main() async {
  final delegate = Repository();
  var expirations = 0;
  final boundary = SessionBoundary(delegate, onExpired: (_) => expirations++);
  check(await rejected(boundary.investments()), 'Anonymous read permitted');
  check(delegate.reads.isEmpty, 'Anonymous request reached delegate');
  await boundary.login('test', 'test');
  final transient = rejected(boundary.investments());
  delegate.reads.last.completeError(const LenkaFailure('Sin conexión'));
  check(await transient && expirations == 0, 'Network error expired session');
  final valid = boundary.investments();
  delegate.reads.last.complete([]);
  check((await valid).isEmpty, 'Retry after network error failed');
  check(await rejected(boundary.detail(1)), 'Expired detail was accepted');
  check(expirations == 1, 'Expired detail not signaled');
  check(
    await rejected(boundary.statements()) && expirations == 1,
    'Repeated expiry notification',
  );
  await boundary.login('test', 'test');
  final stale = rejected(boundary.investments());
  final old = delegate.reads.last;
  await boundary.logout();
  await boundary.login('test', 'test');
  old.completeError(const LenkaFailure('Old session', sessionExpired: true));
  check(await stale && expirations == 1, 'Old response expired a new session');
  final lateSuccess = rejected(boundary.investments());
  final late = delegate.reads.last;
  await boundary.logout();
  late.complete([
    {'private': 'old-data'},
  ]);
  check(await lateSuccess, 'Private data returned after logout');
  check(delegate.logouts == 2, 'Logout not forwarded');
  print('PASS: 10 session-boundary checks. No network used.');
}
