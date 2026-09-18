import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class LenkaApiException implements Exception {
  LenkaApiException(this.message);
  final String message;
}

class LenkaApiClient {
  LenkaApiClient({required this.baseUrl, required this.database});

  final String baseUrl;
  final String database;
  final _storage = const FlutterSecureStorage();
  final _http = http.Client();

  static const _sessionKey = 'lenka_session_id';

  Future<bool> hasSession() async {
    final value = await _storage.read(key: _sessionKey);
    return value != null && value.isNotEmpty;
  }

  Future<void> login(String login, String password) async {
    final response = await _http.post(
      Uri.parse(baseUrl + '/web/session/authenticate'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {'db': database, 'login': login, 'password': password},
        'id': 1,
      }),
    );

    final data = _decode(response);
    final result = data['result'];
    if (result is! Map || result['uid'] == null || result['uid'] == false) {
      throw LenkaApiException('Correo o contrasena incorrectos.');
    }

    final cookie = response.headers['set-cookie'];
    final session = _extractSession(cookie);
    if (session == null) {
      throw LenkaApiException('No fue posible crear la sesion.');
    }
    await _storage.write(key: _sessionKey, value: session);
  }

  Future<void> logout() async {
    await _storage.delete(key: _sessionKey);
  }

  Future<Map<String, dynamic>> dashboard() async {
    final result = await _rpc('/lenka/mobile/v1/dashboard');
    return Map<String, dynamic>.from(result as Map);
  }

  Future<List<dynamic>> operations() async {
    final result = await _rpc('/lenka/mobile/v1/operations');
    return List<dynamic>.from(result as List);
  }

  Future<List<dynamic>> investments() async {
    final result = await _rpc('/lenka/mobile/v1/investments');
    return List<dynamic>.from(result as List);
  }

  Future<List<dynamic>> statements() async {
    final result = await _rpc('/lenka/mobile/v1/statements');
    return List<dynamic>.from(result as List);
  }

  Future<dynamic> _rpc(String path) async {
    final session = await _storage.read(key: _sessionKey);
    if (session == null || session.isEmpty) {
      throw LenkaApiException('Debe iniciar sesion.');
    }

    final response = await _http.post(
      Uri.parse(baseUrl + path),
      headers: {
        'Content-Type': 'application/json',
        'Cookie': 'session_id=' + session,
      },
      body: jsonEncode({
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {},
        'id': DateTime.now().millisecondsSinceEpoch,
      }),
    );

    final data = _decode(response);
    if (data['error'] != null) {
      final error = data['error'] as Map;
      final detail = error['data'] is Map ? (error['data'] as Map)['message'] : null;
      throw LenkaApiException((detail ?? error['message'] ?? 'Error del servidor').toString());
    }
    return data['result'];
  }

  Map<String, dynamic> _decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw LenkaApiException('Error HTTP ' + response.statusCode.toString());
    }
    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw LenkaApiException('Respuesta invalida del servidor.');
    }
    if (decoded['error'] != null) {
      final error = decoded['error'] as Map;
      final detail = error['data'] is Map ? (error['data'] as Map)['message'] : null;
      throw LenkaApiException((detail ?? error['message'] ?? 'Error de autenticacion').toString());
    }
    return decoded;
  }

  String? _extractSession(String? cookie) {
    if (cookie == null) return null;
    final match = RegExp(r'session_id=([^;]+)').firstMatch(cookie);
    return match?.group(1);
  }
}
