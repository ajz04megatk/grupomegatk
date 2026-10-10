import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lenka_clientes/api.dart';
import 'package:lenka_clientes/brand.dart';
import 'package:lenka_clientes/main.dart';
import 'package:lenka_clientes/statements.dart';

import 'statements_smoke.dart' show statementFixture;

class FakeRepository implements SavingsRepository {
  int logouts = 0;
  bool fail = false;
  bool accessExpired = false;
  List<Map<String, dynamic>> statementData = [];
  @override
  Future<void> login(String email, String password) async {}
  @override
  Future<void> logout() async {
    logouts++;
  }

  @override
  Future<List<Map<String, dynamic>>> investments() async {
    if (accessExpired)
      throw const LenkaFailure('Acceso deshabilitado.', sessionExpired: true);
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
  Future<List<Map<String, dynamic>>> statements() async => statementData;
  @override
  Future<Map<String, dynamic>> detail(int id) async => {
    'id': id,
    'state': 'active',
    'name': 'Depósito A',
    'currency': 'HNL',
    'outstanding_principal': 25000,
    'accrued_interest': 500,
    'paid_interest': 450,
    'principal_amount': 25000,
    'passive_rate': 1.25,
    'early_withdrawal_rate': 0.5,
    'rate_period': 'annual',
    'start_date': '2026-01-01',
    'interest_history': [],
    'withdrawals': [],
  };
}

class DelayedRepository extends FakeRepository {
  final authentication = Completer<void>();
  final reads = <Completer<List<Map<String, dynamic>>>>[];
  @override
  Future<void> login(String email, String password) => authentication.future;
  @override
  Future<List<Map<String, dynamic>>> investments() {
    final result = Completer<List<Map<String, dynamic>>>();
    reads.add(result);
    return result.future;
  }
}

void main() {
  testWidgets('Revoked access returns to login without an extra tap', (
    tester,
  ) async {
    final repository = FakeRepository();
    await tester.pumpWidget(LenkaApp(repository: repository));
    await tester.enterText(
      find.byType(TextField).first,
      'client@example.invalid',
    );
    await tester.enterText(find.byType(TextField).last, 'fictional');
    await tester.tap(find.text('Ingresar'));
    await tester.pumpAndSettle();
    repository.accessExpired = true;
    await tester.tap(find.byTooltip('Actualizar'));
    await tester.pumpAndSettle();
    expect(find.text('Mis ahorros'), findsNothing);
    expect(find.text('Acceso deshabilitado.'), findsOneWidget);
    expect(find.text('Ingresar'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets(
    'Login guides missing fields and masks password after backgrounding',
    (tester) async {
      await tester.pumpWidget(LenkaApp(repository: FakeRepository()));
      await tester.tap(find.text('Ingresar'));
      await tester.pumpAndSettle();
      expect(find.text('Escribí tu correo.'), findsOneWidget);
      expect(find.text('Escribí tu contraseña.'), findsOneWidget);
      await tester.enterText(
        find.byType(TextField).first,
        'client@example.invalid',
      );
      await tester.enterText(find.byType(TextField).last, 'fictional');
      await tester.tap(find.byTooltip('Mostrar contraseña'));
      await tester.pump();
      expect(
        tester.widget<TextField>(find.byType(TextField).last).obscureText,
        isFalse,
      );
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      await tester.pump();
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      expect(
        tester.widget<TextField>(find.byType(TextField).last).obscureText,
        isTrue,
      );
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets('Deposit search combines name and currency', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: SavingsPage(repository: FakeRepository())),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.byType(TextField), 200);
    await tester.enterText(find.byType(TextField), 'Depósito A');
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.widgetWithText(ChoiceChip, 'Dólares'),
      150,
    );
    await tester.tap(find.widgetWithText(ChoiceChip, 'Dólares'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('No encontramos depósitos con esos filtros.'),
      150,
    );
    expect(
      find.text('No encontramos depósitos con esos filtros.'),
      findsOneWidget,
    );
    expect(find.text('Depósito A\nActivo'), findsNothing);
  });
  testWidgets('Idle session removes savings and returns to login', (
    tester,
  ) async {
    var elapsed = Duration.zero;
    final repository = FakeRepository();
    await tester.pumpWidget(
      LenkaApp(repository: repository, elapsed: () => elapsed),
    );
    await tester.enterText(
      find.byType(TextField).first,
      'test@example.invalid',
    );
    await tester.enterText(find.byType(TextField).last, 'fictional');
    await tester.tap(find.text('Ingresar'));
    await tester.pumpAndSettle();
    expect(find.text('Mis ahorros'), findsOneWidget);
    elapsed = const Duration(minutes: 5);
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(find.text('Mis ahorros'), findsNothing);
    expect(find.textContaining('5 minutos sin actividad'), findsOneWidget);
    expect(repository.logouts, greaterThanOrEqualTo(1));
    await tester.pumpWidget(const SizedBox());
  });
  testWidgets('Login displays the official Lenka asset', (tester) async {
    await tester.pumpWidget(LenkaApp(repository: FakeRepository()));
    await tester.pumpAndSettle();
    final image = tester.widget<Image>(find.byType(Image));
    expect(image.image, const AssetImage(LenkaBrand.iconAsset));
    expect(image.semanticLabel, 'Inversiones Lenka');
    expect(tester.takeException(), isNull);
  });
  test('Official Lenka colors define the interface', () {
    final theme = LenkaBrand.theme;
    expect(theme.colorScheme.primary, LenkaBrand.sky);
    expect(theme.colorScheme.onPrimary, LenkaBrand.ink);
    expect(theme.appBarTheme.backgroundColor, LenkaBrand.sky);
    expect(theme.scaffoldBackgroundColor, LenkaBrand.ivory);
  });
  testWidgets(
    'Statements distinguish savings and credit without mixing currencies',
    (tester) async {
      final repository = FakeRepository()
        ..statementData = [
          statementFixture(1, 'investment', 'HNL'),
          statementFixture(2, 'operation', 'USD'),
        ];
      await tester.pumpWidget(
        MaterialApp(home: StatementsPage(repository: repository)),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(ChoiceChip, 'Ahorros'));
      await tester.pumpAndSettle();
      expect(find.text('Estado 1'), findsOneWidget);
      expect(find.text('Estado 2'), findsNothing);
      expect(find.text('01/09/2026 — 30/09/2026'), findsOneWidget);
      expect(find.text('Saldo al cierre: HNL 200.00'), findsOneWidget);
      await tester.tap(find.widgetWithText(ChoiceChip, 'Créditos'));
      await tester.pumpAndSettle();
      expect(find.text('Estado 1'), findsNothing);
      expect(find.text('Estado 2'), findsOneWidget);
      expect(find.text('Saldo al cierre: USD 200.00'), findsOneWidget);
    },
  );
  testWidgets('Leaving login during authentication closes late session', (
    tester,
  ) async {
    final repository = DelayedRepository();
    await tester.pumpWidget(LenkaApp(repository: repository));
    await tester.enterText(
      find.byType(TextField).first,
      'test@example.invalid',
    );
    await tester.enterText(find.byType(TextField).last, 'fictional');
    await tester.tap(find.text('Ingresar'));
    await tester.pump();
    await tester.pumpWidget(const MaterialApp(home: SizedBox()));
    repository.authentication.complete();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(repository.logouts, 1);
  });
  testWidgets('Latest refresh wins when responses arrive out of order', (
    tester,
  ) async {
    final repository = DelayedRepository();
    await tester.pumpWidget(
      MaterialApp(home: SavingsPage(repository: repository)),
    );
    repository.reads.first.complete([]);
    await tester.pumpAndSettle();
    final refresh = tester
        .widget<RefreshIndicator>(find.byType(RefreshIndicator))
        .onRefresh;
    final older = refresh();
    final newer = refresh();
    repository.reads.last.complete([]);
    await newer;
    repository.reads[1].complete(await FakeRepository().investments());
    await older;
    await tester.pumpAndSettle();
    expect(find.text('HNL 25,000.00'), findsNothing);
    expect(
      find.text('Todavía no tenés depósitos registrados para consultar.'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });
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
      expect(find.text('HNL 25,000.00'), findsWidgets);
      expect(find.text('USD 1,000.00'), findsWidgets);
      expect(find.textContaining('26,000'), findsNothing);
      await tester.scrollUntilVisible(find.text('Depósito A\nActivo'), 250);
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
