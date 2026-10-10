import 'validation.dart';

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
