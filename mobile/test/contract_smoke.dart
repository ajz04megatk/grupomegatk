import 'dart:convert';
import 'dart:io';

import '../lib/validation.dart';
import '../lib/presentation.dart';

void check(bool value, String message) {
  if (!value) throw StateError(message);
}

void main(List<String> args) {
  final payload = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final deposits = validateDeposits(payload['deposits']);
  final statements = validateStatements(payload['statements']);
  check(deposits.length == 2 && statements.length == 2, 'Records lost');
  check(
    savingsTotals(deposits).map((r) => r.formatted).join('|') ==
        'HNL 900.00|USD 900.00',
    'Server balances changed',
  );
  for (final raw in payload['details'] as List) {
    final row = validateDepositDetail(raw, raw['id'] as int);
    final movements = depositMovements(row, row['id'] as int);
    check(movements.length == 2, 'Unpublished movements leaked');
    check(
      movements[0].details.contains('Interés neto: ${row['currency']} 9.00'),
      'Net interest mismatch',
    );
    check(movements[1].amount == 109, 'Withdrawal mismatch');
    check(
      depositConditions(
        row,
        row['id'] as int,
      ).contains('Tasa contractual: 1 % mensual'),
      'Rate period mismatch',
    );
  }
  print(
    'PASS: 10 cross-language payload checks from actual service serialization with fictional records. No Odoo ORM or network.',
  );
}
