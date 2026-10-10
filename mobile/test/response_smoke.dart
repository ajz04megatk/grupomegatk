import 'dart:async';
import 'dart:io';

import '../lib/api.dart';
import 'session_smoke.dart'
    show FakeClient, FakeResponse, check, expired, login, tick;

class ChunkedResponse extends Stream<List<int>> implements HttpClientResponse {
  ChunkedResponse(this.chunks);
  final List<List<int>> chunks;
  @override
  int get statusCode => 200;
  @override
  List<Cookie> get cookies => [];
  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int>)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) => Stream.fromIterable(chunks).listen(
    onData,
    onError: onError,
    onDone: onDone,
    cancelOnError: cancelOnError,
  );
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<LenkaFailure?> failure(Future<dynamic> operation) async {
  try {
    await operation;
    return null;
  } on LenkaFailure catch (error) {
    return error;
  }
}

Future<void> main() async {
  final client = FakeClient();
  final repository = OdooSavingsRepository(
    Uri.parse('https://example.invalid'),
    'test',
    clientFactory: () => client,
  );
  for (final uid in [0, -1, false, null, '1']) {
    final pending = failure(repository.login('test@example.invalid', 'test'));
    await tick();
    client.requests.last.completer.complete(
      FakeResponse(
        {
          'result': {'uid': uid},
        },
        cookies: [Cookie('session_id', 'invalid')],
      ),
    );
    check(await pending != null, 'Invalid identity accepted: $uid');
    check(
      await expired(repository.investments()),
      'Invalid identity kept cookie',
    );
  }
  final missingCookie = failure(
    repository.login('test@example.invalid', 'test'),
  );
  await tick();
  client.requests.last.completer.complete(
    FakeResponse({
      'result': {'uid': 1},
    }),
  );
  check(await missingCookie != null, 'Authentication without cookie accepted');

  await login(repository, client, 'valid');
  final oversized = failure(repository.investments());
  await tick();
  final request = client.requests.last;
  request.completer.complete(
    ChunkedResponse([
      List.filled(2 * 1024 * 1024, 32),
      List.filled(2 * 1024 * 1024, 32),
      [32],
    ]),
  );
  final result = await oversized;
  check(
    result != null && result.message.contains('demasiada información'),
    'Chunked oversized response was not bounded',
  );
  check(request.aborted, 'Oversized request was not aborted');

  final invalidJson = failure(repository.investments());
  await tick();
  client.requests.last.completer.complete(
    ChunkedResponse([
      [255],
    ]),
  );
  check(await invalidJson != null, 'Invalid UTF-8 was accepted');

  final retry = repository.investments();
  await tick();
  client.requests.last.completer.complete(FakeResponse({'result': []}));
  check((await retry).isEmpty, 'Valid retry failed after rejected response');
  await repository.logout();
  print(
    'PASS: invalid identities, missing cookie, oversized chunks, invalid UTF-8 and recovery. No network used.',
  );
}
