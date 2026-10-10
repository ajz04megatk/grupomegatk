/// Validate server data before any financial screen consumes it.
/// No coercion of numeric strings, missing amounts or unknown currencies.
class InvalidFinancialData implements Exception {
  const InvalidFinancialData();
}

Never _invalid() => throw const InvalidFinancialData();

Map<String, dynamic> _record(dynamic value) {
  if (value is! Map || value.keys.any((key) => key is! String)) _invalid();
  return Map<String, dynamic>.from(value);
}

void _text(Map<String, dynamic> row, String key) {
  if (row[key] is! String || (row[key] as String).trim().isEmpty) _invalid();
}

void _amount(Map<String, dynamic> row, String key) {
  final value = row[key];
  if (value is! num || !value.isFinite || value.abs() >= 1e21) _invalid();
}

void _date(Map<String, dynamic> row, String key, {bool optional = false}) {
  final value = row[key];
  if (optional && (value == null || value == false)) return;
  if (value is! String || !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value))
    _invalid();
  final parsed = DateTime.tryParse(value);
  if (parsed == null || parsed.toIso8601String().substring(0, 10) != value)
    _invalid();
}

void _identity(Map<String, dynamic> row) {
  if (row['id'] is! int || (row['id'] as int) <= 0) _invalid();
  _text(row, 'name');
  // The first mobile version is explicitly HNL/USD. Never relabel another currency.
  if (!const {'HNL', 'USD'}.contains(row['currency'])) _invalid();
}

List<Map<String, dynamic>> _list(
  dynamic value,
  void Function(Map<String, dynamic>) check, {
  bool uniqueIds = false,
}) {
  if (value is! List) _invalid();
  final rows = <Map<String, dynamic>>[];
  final ids = <int>{};
  for (final item in value) {
    final row = _record(item);
    check(row);
    if (uniqueIds && !ids.add(row['id'] as int)) _invalid();
    rows.add(row);
  }
  return rows;
}

void _deposit(Map<String, dynamic> row) {
  _identity(row);
  if (!const {'active', 'matured', 'closed'}.contains(row['state'])) _invalid();
  _amount(row, 'outstanding_principal');
  if ((row['outstanding_principal'] as num) < 0) _invalid();
}

List<Map<String, dynamic>> validateDeposits(dynamic value) =>
    _list(value, _deposit, uniqueIds: true);

Map<String, dynamic> validateDepositDetail(dynamic value, int requestedId) {
  final row = _record(value);
  _deposit(row);
  if (row['id'] != requestedId) _invalid();
  _amount(row, 'accrued_interest');
  _amount(row, 'paid_interest');
  _amount(row, 'principal_amount');
  _amount(row, 'passive_rate');
  _amount(row, 'early_withdrawal_rate');
  if ((row['principal_amount'] as num) <= 0 ||
      (row['passive_rate'] as num) < 0 ||
      (row['early_withdrawal_rate'] as num) < 0)
    _invalid();
  if (!const {'monthly', 'annual'}.contains(row['rate_period'])) _invalid();
  _date(row, 'start_date');
  _date(row, 'maturity_date', optional: true);
  if (row['maturity_date'] is String &&
      (row['maturity_date'] as String).compareTo(row['start_date'] as String) <
          0) {
    _invalid();
  }
  row['interest_history'] = _list(row['interest_history'], (item) {
    _date(item, 'date');
    _amount(item, 'amount');
    _amount(item, 'tax_amount');
    _amount(item, 'net_amount');
    if (!const {'accrued', 'paid'}.contains(item['state'])) _invalid();
  });
  row['withdrawals'] = _list(row['withdrawals'], (item) {
    _date(item, 'date');
    _amount(item, 'total_amount');
    _amount(item, 'principal_amount');
    _amount(item, 'interest_amount');
    _amount(item, 'gross_interest_amount');
    _amount(item, 'interest_tax_amount');
  });
  return row;
}

List<Map<String, dynamic>> validateStatements(dynamic value) =>
    _list(value, (row) {
      _identity(row);
      if (!const {'investment', 'operation'}.contains(row['type'])) _invalid();
      if (!const {'generated', 'sent'}.contains(row['state'])) _invalid();
      _amount(row, 'opening_balance');
      _amount(row, 'closing_balance');
      _date(row, 'date_from');
      _date(row, 'date_to');
      if ((row['date_from'] as String).compareTo(row['date_to'] as String) > 0)
        _invalid();
    }, uniqueIds: true);
