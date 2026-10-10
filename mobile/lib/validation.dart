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
  void Function(Map<String, dynamic>) check,
) {
  if (value is! List) _invalid();
  final rows = <Map<String, dynamic>>[];
  for (final item in value) {
    final row = _record(item);
    check(row);
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
    _list(value, _deposit);

Map<String, dynamic> validateDepositDetail(dynamic value, int requestedId) {
  final row = _record(value);
  _deposit(row);
  if (row['id'] != requestedId) _invalid();
  _amount(row, 'accrued_interest');
  _amount(row, 'paid_interest');
  _date(row, 'maturity_date', optional: true);
  row['interest_history'] = _list(row['interest_history'], (item) {
    _date(item, 'date');
    _amount(item, 'amount');
    if (!const {'accrued', 'paid'}.contains(item['state'])) _invalid();
  });
  row['withdrawals'] = _list(row['withdrawals'], (item) {
    _date(item, 'date');
    _amount(item, 'total_amount');
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
    });
