import 'validation.dart';

List<Map<String, dynamic>> filterDeposits(
  List<Map<String, dynamic>> data, {
  String query = '',
  String? currency,
}) {
  if (currency != null && !const {'HNL', 'USD'}.contains(currency)) {
    throw ArgumentError.value(currency);
  }
  String normalize(String value) {
    var text = value.toLowerCase().trim();
    const accents = {
      'á': 'a',
      'é': 'e',
      'í': 'i',
      'ó': 'o',
      'ú': 'u',
      'ü': 'u',
    };
    accents.forEach(
      (key, replacement) => text = text.replaceAll(key, replacement),
    );
    return text;
  }

  final terms = normalize(query)
      .split(RegExp(r'\s+'))
      .where((term) => term.isNotEmpty);
  return validateDeposits(data).where((row) {
    if (currency != null && row['currency'] != currency) return false;
    final name = normalize(row['name'] as String);
    return terms.every(name.contains);
  }).toList();
}

enum StatementCategory { all, savings, credit }

String statementTypeLabel(String type) => switch (type) {
  'investment' => 'Ahorros / depósitos',
  'operation' => 'Préstamos / financiamientos / arrendamientos',
  _ => 'Tipo no disponible',
};

List<Map<String, dynamic>> statementRows(
  List<Map<String, dynamic>> data,
  StatementCategory category,
) {
  final rows = validateStatements(data)
      .where(
        (row) => switch (category) {
          StatementCategory.all => true,
          StatementCategory.savings => row['type'] == 'investment',
          StatementCategory.credit => row['type'] == 'operation',
        },
      )
      .toList();
  rows.sort((a, b) {
    final date = (b['date_to'] as String).compareTo(a['date_to'] as String);
    return date != 0 ? date : (b['id'] as int).compareTo(a['id'] as int);
  });
  return rows;
}

class SavingsTotal {
  SavingsTotal(this.currency, this.minorUnits, this.deposits);
  final String currency;
  final BigInt minorUnits;
  final int deposits;
  String get formatted {
    final digits = minorUnits.toString().padLeft(3, '0');
    final integer = digits
        .substring(0, digits.length - 2)
        .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (m) => '${m[1]},');
    return '$currency $integer.${digits.substring(digits.length - 2)}';
  }
}

/// HNL/USD have two decimal places. Round each displayed record before summing,
/// using integer cents so the summary matches the displayed deposits.
List<SavingsTotal> savingsTotals(List<Map<String, dynamic>> data) {
  final rows = validateDeposits(data);
  final cents = <String, BigInt>{};
  final counts = <String, int>{};
  for (final row in rows) {
    final currency = row['currency'] as String;
    final amount = row['outstanding_principal'] as num;
    // Exclude closed contracts from the current savings total, keep them in history.
    if (row['state'] == 'closed') continue;
    final fixed = amount == 0 ? '0.00' : amount.toStringAsFixed(2);
    if (!RegExp(r'^\d+\.\d{2}$').hasMatch(fixed)) {
      throw const InvalidFinancialData();
    }
    cents[currency] =
        (cents[currency] ?? BigInt.zero) +
        BigInt.parse(fixed.replaceAll('.', ''));
    counts[currency] = (counts[currency] ?? 0) + 1;
  }
  final currencies = cents.keys.toList()..sort();
  return [
    for (final currency in currencies)
      SavingsTotal(currency, cents[currency]!, counts[currency]!),
  ];
}

String displayDate(String iso) {
  final parts = iso.split('-');
  return parts.length == 3 ? '${parts[2]}/${parts[1]}/${parts[0]}' : iso;
}

List<String> depositConditions(Map<String, dynamic> data, int id) {
  final row = validateDepositDetail(data, id);
  final period = row['rate_period'] == 'monthly' ? 'mensual' : 'anual';
  String rate(num value) => value.toString().replaceFirst(RegExp(r'\.0$'), '');
  return [
    'Capital recibido: ${money(row['principal_amount'], row['currency'] as String)}',
    'Apertura: ${displayDate(row['start_date'] as String)}',
    'Vencimiento: ${row['maturity_date'] is String ? displayDate(row['maturity_date'] as String) : 'Sin fecha registrada'}',
    'Tasa contractual: ${rate(row['passive_rate'] as num)} % $period',
    'Tasa por retiro anticipado: ${rate(row['early_withdrawal_rate'] as num)} % $period',
  ];
}

class DepositMovement {
  const DepositMovement(this.date, this.label, this.amount, this.order);
  final String date;
  final String label;
  final num amount;
  final int order;
}

List<DepositMovement> depositMovements(Map<String, dynamic> data, int id) {
  final row = validateDepositDetail(data, id);
  final result = <DepositMovement>[];
  for (final item in row['interest_history'] as List) {
    result.add(
      DepositMovement(
        item['date'] as String,
        item['state'] == 'paid'
            ? 'Interés pagado (importe bruto)'
            : 'Interés registrado (importe bruto)',
        item['amount'] as num,
        result.length,
      ),
    );
  }
  for (final item in row['withdrawals'] as List) {
    result.add(
      DepositMovement(
        item['date'] as String,
        'Retiro registrado',
        item['total_amount'] as num,
        result.length,
      ),
    );
  }
  result.sort((a, b) {
    final dateOrder = b.date.compareTo(a.date);
    return dateOrder != 0 ? dateOrder : a.order.compareTo(b.order);
  });
  return result;
}

String money(dynamic amount, String currency) {
  if (amount is! num ||
      !amount.isFinite ||
      amount.abs() >= 1e21 ||
      !const ['HNL', 'USD'].contains(currency))
    return 'No disponible';
  final fixed = amount.toStringAsFixed(2);
  final parts = (fixed == '-0.00' ? '0.00' : fixed).split('.');
  final integer = parts[0].replaceAllMapped(
    RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
    (m) => '${m[1]},',
  );
  return '$currency $integer.${parts[1]}';
}
