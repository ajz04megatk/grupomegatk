import '../lib/presentation.dart';
import '../lib/validation.dart';

Map<String, dynamic> statementFixture(
  int id,
  String type,
  String currency, {
  String end = '2026-09-30',
}) => {
  'id': id,
  'name': 'Estado $id',
  'type': type,
  'currency': currency,
  'state': 'generated',
  'date_from': '2026-09-01',
  'date_to': end,
  'opening_balance': 100,
  'closing_balance': 200,
};

void check(bool value, String reason) {
  if (!value) throw StateError(reason);
}

void main() {
  final data = [
    statementFixture(1, 'investment', 'HNL'),
    statementFixture(2, 'operation', 'USD', end: '2026-10-01'),
    statementFixture(3, 'investment', 'USD'),
  ];
  final all = statementRows(data, StatementCategory.all);
  check(
    all.map((r) => r['id']).join(',') == '2,3,1',
    'Order not deterministic',
  );
  final savings = statementRows(data, StatementCategory.savings);
  check(
    savings.length == 2 && savings.every((r) => r['type'] == 'investment'),
    'Credits mixed into savings',
  );
  check(
    savings.map((r) => r['currency']).join(',') == 'USD,HNL',
    'Currency changed',
  );
  check(
    statementRows(data, StatementCategory.credit).single['id'] == 2,
    'Credit filter incorrect',
  );
  check(
    statementRows(savings, StatementCategory.credit).isEmpty,
    'Empty category invented statement',
  );
  check(data.map((r) => r['id']).join(',') == '1,2,3', 'Input reordered');
  savings.first['closing_balance'] = 0;
  check(data.last['closing_balance'] == 200, 'Source data mutated');
  check(
    statementTypeLabel('investment') == 'Ahorros / depósitos',
    'Savings label',
  );
  check(
    statementTypeLabel('operation').contains('arrendamientos'),
    'Credit label',
  );
  bool rejected = false;
  try {
    statementRows([
      statementFixture(1, 'unknown', 'HNL'),
    ], StatementCategory.savings);
  } on InvalidFinancialData {
    rejected = true;
  }
  check(rejected, 'Unknown type silently hidden');
  print('PASS: 10 statement categorization, ordering and isolation checks.');
}
