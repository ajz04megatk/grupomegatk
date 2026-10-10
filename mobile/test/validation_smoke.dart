import '../lib/validation.dart';

int passed = 0;
void rejects(void Function() action) {
  try {
    action();
  } on InvalidFinancialData {
    passed++;
    return;
  }
  throw StateError('Invalid financial data was accepted');
}

Map<String, dynamic> deposit() => {
  'id': 1,
  'name': 'Depósito de prueba',
  'currency': 'HNL',
  'state': 'active',
  'outstanding_principal': 1200.50,
};
Map<String, dynamic> detail() => {
  ...deposit(),
  'accrued_interest': 10,
  'paid_interest': 5,
  'principal_amount': 25000,
  'passive_rate': 1.25,
  'early_withdrawal_rate': 0.5,
  'rate_period': 'annual',
  'start_date': '2026-01-01',
  'maturity_date': false,
  'interest_history': [
    {'date': '2026-10-09', 'amount': 10, 'state': 'accrued'},
  ],
  'withdrawals': [],
};
Map<String, dynamic> statement() => {
  'id': 5,
  'name': 'Estado de prueba',
  'type': 'investment',
  'currency': 'USD',
  'state': 'generated',
  'opening_balance': 100,
  'closing_balance': 200,
  'date_from': '2026-09-01',
  'date_to': '2026-09-30',
};

void main() {
  for (final currency in ['HNL', 'USD']) {
    final row = deposit()..['currency'] = currency;
    final parsed = validateDeposits([row]);
    if (parsed.single['currency'] != currency ||
        parsed.single['outstanding_principal'] != 1200.50) {
      throw StateError('Currency or amount changed');
    }
    passed++;
  }
  if (validateDeposits([]).isNotEmpty) throw StateError('Empty data changed');
  passed++;
  for (final amount in [null, '1000', double.nan, double.infinity, 1e21, -1]) {
    rejects(
      () => validateDeposits([deposit()..['outstanding_principal'] = amount]),
    );
  }
  rejects(() => validateDeposits([deposit()..['currency'] = 'EUR']));
  rejects(() => validateDeposits([deposit()..remove('id')]));
  rejects(() => validateDeposits([deposit()..['state'] = 'draft']));
  rejects(() => validateDeposits([deposit(), false]));
  validateDepositDetail(detail(), 1);
  passed++;
  rejects(() => validateDepositDetail(detail()..['rate_period'] = 'weekly', 1));
  rejects(() => validateDepositDetail(detail()..['passive_rate'] = -1, 1));
  rejects(
    () => validateDepositDetail(detail()..['early_withdrawal_rate'] = null, 1),
  );
  rejects(() => validateDepositDetail(detail()..remove('start_date'), 1));
  rejects(
    () => validateDepositDetail(detail()..['maturity_date'] = '2025-12-31', 1),
  );
  rejects(() => validateDepositDetail(detail(), 2));
  rejects(() => validateDepositDetail(detail()..['withdrawals'] = null, 1));
  rejects(
    () => validateDepositDetail(detail()..['maturity_date'] = '2026-02-30', 1),
  );
  rejects(
    () => validateDepositDetail(
      detail()
        ..['interest_history'] = [
          {'date': '2026-10-09', 'amount': 10, 'state': 'draft'},
        ],
      1,
    ),
  );
  validateStatements([statement()]);
  passed++;
  rejects(() => validateStatements([statement()..['date_to'] = '2026-08-31']));
  rejects(() => validateStatements([statement()..['closing_balance'] = null]));
  rejects(() => validateStatements([statement()..['state'] = 'draft']));
  rejects(() => validateStatements([statement()..remove('type')]));
  rejects(() => validateStatements([statement()..['type'] = 'unknown']));
  rejects(() => validateDeposits([deposit(), deposit()]));
  rejects(() => validateDeposits([deposit(), deposit()..['currency'] = 'USD']));
  rejects(() => validateStatements([statement(), statement()]));
  final sameAmountDifferentIds = validateDeposits([
    deposit(),
    deposit()..['id'] = 2,
  ]);
  if (sameAmountDifferentIds.length != 2) {
    throw StateError('Distinct deposits with matching amounts were removed');
  }
  passed++;
  print('PASS: $passed financial response validation checks.');
}
