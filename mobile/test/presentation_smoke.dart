import '../lib/presentation.dart';

Map<String, dynamic> deposit(
  int id,
  String currency,
  num amount, {
  String state = 'active',
}) => {
  'id': id,
  'name': 'Test $id',
  'currency': currency,
  'state': state,
  'outstanding_principal': amount,
};
void check(bool value, String message) {
  if (!value) throw StateError(message);
}

void main() {
  check(money(25000, 'HNL') == 'HNL 25,000.00', 'Money grouping incorrect');
  check(money(-1234.56, 'USD') == 'USD -1,234.56', 'Negative amount incorrect');
  check(money(-0.001, 'USD') == 'USD 0.00', 'Negative zero displayed');
  for (final value in [null, double.nan, double.infinity, 1e21, '100']) {
    check(money(value, 'HNL') == 'No disponible', 'Invalid amount displayed');
  }
  check(money(100, 'EUR') == 'No disponible', 'Unsupported currency displayed');
  final rows = [
    deposit(1, 'HNL', 25000),
    deposit(2, 'USD', 1000),
    deposit(3, 'HNL', 5000),
    deposit(4, 'USD', 8000, state: 'closed'),
  ];
  final totals = savingsTotals(rows);
  check(totals.length == 2, 'Mixed currencies combined');
  check(totals[0].formatted == 'HNL 30,000.00', 'HNL total incorrect');
  check(
    totals[1].formatted == 'USD 1,000.00',
    'Closed contract inflated total',
  );
  check(totals[0].deposits == 2, 'Deposit count incorrect');
  check(savingsTotals([]).isEmpty, 'Empty portfolio invented balance');
  check(
    savingsTotals([deposit(1, 'USD', 0.1), deposit(2, 'USD', 0.2)])
            .single
            .formatted ==
        'USD 0.30',
    'Decimal sum incorrect',
  );
  check(
    savingsTotals([deposit(1, 'HNL', 0)]).single.formatted == 'HNL 0.00',
    'Zero display incorrect',
  );
  final detail = {
    ...deposit(1, 'HNL', 1000),
    'accrued_interest': 20,
    'paid_interest': 10,
    'maturity_date': false,
    'interest_history': [
      {'date': '2026-09-01', 'amount': 10, 'state': 'paid'},
      {'date': '2026-10-01', 'amount': 10, 'state': 'accrued'},
    ],
    'withdrawals': [
      {'date': '2026-09-15', 'total_amount': 100},
    ],
  };
  final movements = depositMovements(detail, 1);
  check(
    movements.map((m) => m.date).join(',') ==
        '2026-10-01,2026-09-15,2026-09-01',
    'Movements out of order',
  );
  check(movements.last.label.contains('bruto'), 'Gross interest mislabeled');
  check(displayDate('2026-10-09') == '09/10/2026', 'Spanish date incorrect');
  check(
    (detail['interest_history'] as List).first['date'] == '2026-09-01',
    'Source mutated',
  );
  print(
    'PASS: 20 formatting, savings summary and movement presentation checks.',
  );
}
