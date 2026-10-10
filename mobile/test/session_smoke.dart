import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../lib/api.dart';

class FakeHeaders implements HttpHeaders {
  @override
  ContentType? contentType;
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeResponse extends Stream<List<int>> implements HttpClientResponse {
  FakeResponse(this.data, {this.statusCode = 200, this.cookies = const []});
  final Map<String, dynamic> data;
  @override
  final int statusCode;
  @override
  final List<Cookie> cookies;
  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int>)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) => Stream.value(utf8.encode(jsonEncode(data))).listen(
    onData,
    onError: onError,
    onDone: onDone,
    cancelOnError: cancelOnError,
  );
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeRequest implements HttpClientRequest {
  final completer = Completer<HttpClientResponse>();
  final body = StringBuffer();
  bool aborted = false;
  @override
  bool followRedirects = true;
  @override
  final HttpHeaders headers = FakeHeaders();
  @override
  final List<Cookie> cookies = [];
  @override
  void write(Object? object) => body.write(object);
  @override
  Future<HttpClientResponse> close() => completer.future;
  @override
  void abort([Object? exception, StackTrace? stackTrace]) {
    aborted = true;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeClient implements HttpClient {
  final requests = <FakeRequest>[];
  final paths = <String>[];
  Completer<HttpClientRequest>? delayedOpen;
  @override
  Duration? connectionTimeout;
  @override
  Future<HttpClientRequest> postUrl(Uri url) async {
    paths.add(url.path);
    final request = FakeRequest();
    requests.add(request);
    if (url.path == '/web/session/destroy') {
      request.completer.complete(FakeResponse({'result': null}));
    }
    if (delayedOpen != null) return delayedOpen!.future;
    return request;
  }

  @override
  void close({bool force = false}) {}
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void check(bool value, String message) {
  if (!value) throw StateError(message);
}

Future<void> tick() => Future<void>.delayed(Duration.zero);
Future<bool> expired(Future<dynamic> pending) async {
  try {
    await pending;
    return false;
  } on LenkaFailure catch (e) {
    return e.sessionExpired;
  }
}

Future<void> login(
  OdooSavingsRepository repository,
  FakeClient client,
  String token,
) async {
  final pending = repository.login(
    'client@example.invalid',
    'fictional-test-password',
  );
  await tick();
  final request = client.requests.last;
  request.completer.complete(
    FakeResponse(
      {
        'result': {'uid': 1},
      },
      cookies: [Cookie('session_id', token)],
    ),
  );
  await pending;
  check(!request.followRedirects, 'Login must never redirect credentials');
}

Future<void> main() async {
  final client = FakeClient();
  final repository = OdooSavingsRepository(
    Uri.parse('https://example.invalid'),
    'test',
    clientFactory: () => client,
  );
  await login(repository, client, 'first-session');
  final pending = expired(repository.investments());
  await tick();
  final read = client.requests.last;
  check(read.cookies.single.value == 'first-session', 'Session cookie missing');
  await repository.logout();
  check(client.paths.last == '/web/session/destroy', 'Remote logout missing');
  read.completer.complete(FakeResponse({'result': []}));
  check(await pending, 'Response after logout was accepted');

  await login(repository, client, 'second-session');
  client.delayedOpen = Completer<HttpClientRequest>();
  final waiting = expired(repository.investments());
  await tick();
  final unsent = client.requests.last;
  final gate = client.delayedOpen!;
  client.delayedOpen = null;
  await repository.logout();
  gate.complete(unsent);
  check(await waiting, 'Cancelled connection was accepted');
  check(
    unsent.body.isEmpty && unsent.cookies.isEmpty && unsent.aborted,
    'Cancelled connection sent data',
  );

  await login(repository, client, 'third-session');
  final denied = expired(repository.investments());
  await tick();
  client.requests.last.completer.complete(
    FakeResponse({
      'error': {
        'data': {
          'name': 'odoo.exceptions.AccessError',
          'debug': 'never display this',
        },
      },
    }),
  );
  check(await denied, 'Revoked access must end local session');
  check(await expired(repository.investments()), 'Revoked session was reused');

  // Cancel a pending authentication: a late cookie cannot restore that session.
  final auth = expired(
    repository.login('client@example.invalid', 'fictional-test-password'),
  );
  await tick();
  final authRequest = client.requests.last;
  await repository.logout();
  authRequest.completer.complete(
    FakeResponse(
      {
        'result': {'uid': 1},
      },
      cookies: [Cookie('session_id', 'late-cookie')],
    ),
  );
  check(await auth, 'Late login was accepted');
  check(
    await expired(repository.investments()),
    'Late cookie restored a session',
  );
  print(
    'PASS: logout during read/open/login, remote logout, revoked access and redirect protection. No network used.',
  );
}
