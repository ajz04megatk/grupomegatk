import 'api.dart';

/// Coordinates all financial screens when a server rejects the current session.
class SessionBoundary implements SavingsRepository {
  SessionBoundary(this.delegate, {required this.onExpired});
  final SavingsRepository delegate;
  final void Function(String message) onExpired;
  int _epoch = 0;
  bool _active = false;

  @override
  Future<void> login(String email, String password) async {
    final epoch = ++_epoch;
    _active = false;
    await delegate.login(email, password);
    if (epoch != _epoch) {
      throw const LenkaFailure(
        'El ingreso fue cancelado.',
        sessionExpired: true,
      );
    }
    _active = true;
  }

  Future<T> _read<T>(Future<T> Function() action) async {
    final epoch = _epoch;
    if (!_active) {
      throw const LenkaFailure('Ingresá nuevamente.', sessionExpired: true);
    }
    try {
      final value = await action();
      if (epoch != _epoch || !_active) {
        throw const LenkaFailure('Sesión cerrada.', sessionExpired: true);
      }
      return value;
    } on LenkaFailure catch (error) {
      if (error.sessionExpired && epoch == _epoch && _active) {
        _active = false;
        _epoch++;
        // Navigation callback closes the session and removes every private route.
        onExpired(error.message);
      }
      rethrow;
    }
  }

  @override
  Future<void> logout() {
    _active = false;
    _epoch++;
    return delegate.logout();
  }

  @override
  Future<List<Map<String, dynamic>>> investments() =>
      _read(delegate.investments);
  @override
  Future<Map<String, dynamic>> detail(int id) =>
      _read(() => delegate.detail(id));
  @override
  Future<List<Map<String, dynamic>>> statements() => _read(delegate.statements);
}
