import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lenka_clientes/api.dart';
import 'package:lenka_clientes/main.dart';
import 'package:lenka_clientes/statements.dart';

class FakeRepository implements SavingsRepository {
  int logouts = 0;
  bool fail = false;
  @override
  Future<void> login(String email, String password) async {}
  @override
  Future<void> logout() async {
    logouts++;
  }

  @override
  Future<List<Map<String, dynamic>>> investments() async {
    if (fail) throw const LenkaFailure('Sin conexión');
    return [
      {
        'id': 1,
        'name': 'Depósito A',
        'currency': 'HNL',
        'state': 'active',
        'outstanding_principal': 25000,
      },
      {
        'id': 2,
        'name': 'Depósito B',
        'currency': 'USD',
        'state': 'active',
        'outstanding_principal': 1000,
      },
    ];
  }

  @override
  Future<List<Map<String, dynamic>>> statements() async => [];
  @override
  Future<Map<String, dynamic>> detail(int id) async => {
    'id': id,
    'state': 'active',
    'name': 'Depósito A',
    'currency': 'HNL',
    'outstanding_principal': 25000,
    'accrued_interest': 500,
    'paid_interest': 450,
    'interest_history': [],
    'withdrawals': [],
  };
}

void main() {
  test('Currency is always explicit and missing amounts are not zero', () {
    expect(money(25000, 'HNL'), 'HNL 25,000.00');
    expect(money(1000, 'USD'), 'USD 1,000.00');
    expect(money(null, 'USD'), 'No disponible');
  });
  test('Only HTTPS origins can receive credentials', () {
    expect(
      () => OdooSavingsRepository(Uri.parse('http://example.com'), 'db'),
      throwsArgumentError,
    );
    expect(
      () => OdooSavingsRepository(Uri.parse('https://example.com/path'), 'db'),
      throwsArgumentError,
    );
  });
  testWidgets(
    'Deposits retain their currencies and detail distinguishes historical interest',
    (tester) async {
      final repository = FakeRepository();
      await tester.pumpWidget(
        MaterialApp(home: SavingsPage(repository: repository)),
      );
      await tester.pumpAndSettle();
      expect(find.text('HNL 25,000.00'), findsNWidgets(2));
      expect(find.text('USD 1,000.00'), findsNWidgets(2));
      expect(find.textContaining('26,000'), findsNothing);
      await tester.ensureVisible(find.text('Depósito A\nActivo'));
      await tester.tap(find.text('Depósito A\nActivo'));
      await tester.pumpAndSettle();
      expect(find.text('Intereses históricos: HNL 500.00'), findsOneWidget);
      expect(
        find.textContaining('No representan saldo disponible'),
        findsOneWidget,
      );
    },
  );
  testWidgets('Refresh failure removes previously displayed balances', (
    tester,
  ) async {
    final repository = FakeRepository();
    await tester.pumpWidget(
      MaterialApp(home: SavingsPage(repository: repository)),
    );
    await tester.pumpAndSettle();
    repository.fail = true;
    await tester.tap(find.byTooltip('Actualizar'));
    await tester.pumpAndSettle();
    expect(find.text('Sin conexión'), findsOneWidget);
    expect(find.text('HNL 25,000.00'), findsNothing);
    expect(find.text('Volver a intentar'), findsOneWidget);
  });
  testWidgets('Statements show an honest empty state', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: StatementsPage(repository: FakeRepository())),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('Todavía no tenés estados de cuenta emitidos.'),
      findsOneWidget,
    );
  });
  testWidgets('Backgrounding covers private financial content', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: PrivacyCover(child: Text('Private balance'))),
    );
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
    await tester.pump();
    expect(find.text('Lenka · Tu información es privada'), findsOneWidget);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(find.text('Lenka · Tu información es privada'), findsNothing);
  });
}
