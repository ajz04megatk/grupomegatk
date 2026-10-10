import 'dart:convert';
import 'dart:io';

import 'validation.dart';

class LenkaFailure implements Exception {
  const LenkaFailure(this.message, {this.sessionExpired = false});
  final String message;
  final bool sessionExpired;
}

abstract class SavingsRepository {
  Future<void> login(String email, String password);
  Future<List<Map<String, dynamic>>> investments();
  Future<Map<String, dynamic>> detail(int id);
  Future<void> logout();
  Future<List<Map<String, dynamic>>> statements();
}

/// In-memory session only. No passwords, tokens or balances written to disk.
class OdooSavingsRepository implements SavingsRepository {
  OdooSavingsRepository(
    this.origin,
    this.database, {
    HttpClient Function()? clientFactory,
  }) : _clientFactory = clientFactory ?? HttpClient.new,
       _client = (clientFactory ?? HttpClient.new)() {
    if (origin.scheme != 'https' ||
        origin.host.isEmpty ||
        origin.userInfo.isNotEmpty ||
        origin.hasQuery ||
        origin.hasFragment ||
        (origin.path.isNotEmpty && origin.path != '/') ||
        database.isEmpty) {
      throw ArgumentError('Se requiere el servidor HTTPS de Lenka y su base.');
    }
  }
  final Uri origin;
  final String database;
  final HttpClient Function() _clientFactory;
  final HttpClient _client;
  String? _session;
  int _generation = 0;

  Future<dynamic> _call(
    String path,
    Map<String, dynamic> params, {
    bool authenticate = false,
  }) async {
    final generation = _generation;
    final session = _session;
    HttpClientRequest? request;
    try {
      if (!authenticate && _session == null) {
        throw const LenkaFailure('Ingresá nuevamente.', sessionExpired: true);
      }
      request = await _client
          .postUrl(origin.resolve(path))
          .timeout(const Duration(seconds: 15));
      if (generation != _generation) {
        throw const LenkaFailure('Sesión cerrada.', sessionExpired: true);
      }
      request.followRedirects = false;
      request.headers.contentType = ContentType.json;
      if (session != null) request.cookies.add(Cookie('session_id', session));
      request.write(
        jsonEncode({
          'jsonrpc': '2.0',
          'method': 'call',
          'id': 1,
          'params': params,
        }),
      );
      final response = await request.close().timeout(
        const Duration(seconds: 20),
      );
      if (generation != _generation)
        throw const LenkaFailure('Sesión cerrada.', sessionExpired: true);
      if (response.statusCode == 401 || response.statusCode == 403) {
        logout();
        throw const LenkaFailure(
          'Ingresá nuevamente o consultá a Lenka para habilitar tu acceso.',
          sessionExpired: true,
        );
      }
      if (response.statusCode != 200) {
        throw const LenkaFailure(
          'No pudimos consultar Lenka. Intentá nuevamente.',
        );
      }
      final body = await _readBody(response)
          .timeout(const Duration(seconds: 20));
      if (generation != _generation)
        throw const LenkaFailure('Sesión cerrada.', sessionExpired: true);
      final envelope = jsonDecode(body) as Map<String, dynamic>;
      if (envelope['error'] != null) {
        final error = envelope['error'];
        final name = error is Map
            ? (error['data'] is Map ? error['data']['name'] : null)
            : null;
        if (name == 'odoo.http.SessionExpiredException' ||
            (!authenticate && name == 'odoo.exceptions.AccessError')) {
          logout();
          throw const LenkaFailure(
            'Tu sesión venció. Ingresá nuevamente.',
            sessionExpired: true,
          );
        }
        throw LenkaFailure(
          authenticate
              ? 'No pudimos ingresar. Revisá tus datos y que Lenka haya habilitado tu cuenta.'
              : 'No pudimos consultar tu información. Contactá a Lenka si el problema continúa.',
        );
      }
      if (!envelope.containsKey('result')) throw const FormatException();
      if (authenticate) {
        final result = envelope['result'];
        if (result is! Map || result['uid'] is! int || result['uid'] <= 0) {
          throw const LenkaFailure('Correo o contraseña incorrectos.');
        }
        for (final cookie in response.cookies) {
          if (cookie.name == 'session_id' && cookie.value.isNotEmpty) {
            _session = cookie.value;
          }
        }
        if (_session == null)
          throw const LenkaFailure('No se pudo abrir una sesión segura.');
      }
      return envelope['result'];
    } on LenkaFailure {
      request?.abort();
      rethrow;
    } catch (_) {
      request?.abort();
      throw const LenkaFailure(
        'No pudimos conectar. Revisá tu conexión y volvé a intentar.',
      );
    }
  }

  // Bound decoded response bytes before JSON parsing, including chunked bodies.
  Future<String> _readBody(HttpClientResponse response) async {
    const limit = 4 * 1024 * 1024;
    final bytes = <int>[];
    await for (final chunk in response) {
      if (bytes.length + chunk.length > limit) {
        throw const LenkaFailure(
          'La consulta contiene demasiada información. Contactá a Lenka para revisar tu historial.',
        );
      }
      bytes.addAll(chunk);
    }
    return utf8.decode(bytes);
  }

  @override
  Future<void> login(String email, String password) async {
    if (email.trim().isEmpty || password.isEmpty) {
      throw const LenkaFailure('Completá tu correo y contraseña.');
    }
    final cleanup = logout();
    final generation = _generation;
    await cleanup;
    if (generation != _generation) {
      throw const LenkaFailure(
        'El ingreso fue cancelado.',
        sessionExpired: true,
      );
    }
    await _call('/web/session/authenticate', {
      'db': database,
      'login': email.trim(),
      'password': password,
    }, authenticate: true);
  }

  @override
  Future<List<Map<String, dynamic>>> investments() async {
    final data = await _call('/lenka/mobile/v1/investments', {});
    try {
      return validateDeposits(data);
    } on InvalidFinancialData {
      throw const LenkaFailure(
        'La información de tus depósitos está incompleta. Intentá actualizar o contactá a Lenka.',
      );
    }
  }

  @override
  Future<Map<String, dynamic>> detail(int id) async {
    if (id <= 0) throw ArgumentError.value(id);
    final data = await _call('/lenka/mobile/v1/investments/$id', {});
    try {
      return validateDepositDetail(data, id);
    } on InvalidFinancialData {
      throw const LenkaFailure(
        'No pudimos validar el detalle de tu depósito. Contactá a Lenka.',
      );
    }
  }

  @override
  Future<void> logout() async {
    final session = _session;
    _generation++;
    _session = null;
    if (session == null) return;
    // Separate client: late logout must never overwrite a newly opened session.
    final client = _clientFactory()
      ..connectionTimeout = const Duration(seconds: 5);
    try {
      final request = await client
          .postUrl(origin.resolve('/web/session/destroy'))
          .timeout(const Duration(seconds: 5));
      request.followRedirects = false;
      request.headers.contentType = ContentType.json;
      request.cookies.add(Cookie('session_id', session));
      request.write(
        jsonEncode({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': {}}),
      );
      final response = await request.close().timeout(
        const Duration(seconds: 5),
      );
      await response.drain<void>().timeout(const Duration(seconds: 5));
    } catch (_) {
      // Local session is already discarded even when offline. Server expiry still applies.
    } finally {
      client.close(force: true);
    }
  }

  @override
  Future<List<Map<String, dynamic>>> statements() async {
    final data = await _call('/lenka/mobile/v1/statements', {});
    try {
      return validateStatements(data);
    } on InvalidFinancialData {
      throw const LenkaFailure(
        'No pudimos validar tus estados de cuenta. Intentá actualizar o contactá a Lenka.',
      );
    }
  }
}
