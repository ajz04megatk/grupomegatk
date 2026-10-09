import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lenka_clientes/api.dart';
import 'package:lenka_clientes/main.dart';

class FakeRepository implements SavingsRepository {
  int logouts = 0;
  bool fail = false;
  @override
  Future<void> login(String email, String password) async {}
  @override
  void logout() {
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
  Future<Map<String, dynamic>> detail(int id) async => {
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
      expect(find.text('HNL 25,000.00'), findsOneWidget);
      expect(find.text('USD 1,000.00'), findsOneWidget);
      expect(find.textContaining('26,000'), findsNothing);
      await tester.tap(find.text('HNL 25,000.00'));
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
}
