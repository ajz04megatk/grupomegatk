import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../core/lenka_api_client.dart';

class OperationsScreen extends StatelessWidget {
  const OperationsScreen({super.key, required this.api});
  final LenkaApiClient api;
  String money(dynamic v) => NumberFormat('#,##0.00').format((v as num?) ?? 0);
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Mis operaciones')),
    body: FutureBuilder<List<dynamic>>(
      future: api.operations(),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError) return const Center(child: Text('No fue posible cargar las operaciones.'));
        final rows = snapshot.data ?? [];
        if (rows.isEmpty) return const Center(child: Text('No tienes operaciones activas.'));
        return ListView.builder(padding: const EdgeInsets.all(12), itemCount: rows.length, itemBuilder: (context, index) {
          final row = Map<String, dynamic>.from(rows[index] as Map);
          final next = row['next_payment'] is Map ? Map<String, dynamic>.from(row['next_payment'] as Map) : null;
          final subtitle = StringBuffer('Capital pendiente: ');
          subtitle.write(row['currency']); subtitle.write(' '); subtitle.write(money(row['outstanding_capital']));
          if (next != null) { subtitle.write('\nProxima cuota: '); subtitle.write(next['date']); subtitle.write(' - '); subtitle.write(row['currency']); subtitle.write(' '); subtitle.write(money(next['amount_due'])); }
          return Card(child: ListTile(
            leading: const Icon(Icons.payments_outlined), title: Text(row['name'].toString()), subtitle: Text(subtitle.toString()),
            isThreeLine: next != null, trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => OperationDetailScreen(api: api, operationId: row['id'] as int))),
          ));
        });
      },
    ),
  );
}

class OperationDetailScreen extends StatelessWidget {
  const OperationDetailScreen({super.key, required this.api, required this.operationId});
  final LenkaApiClient api; final int operationId;
  String money(dynamic v) => NumberFormat('#,##0.00').format((v as num?) ?? 0);
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Detalle de operacion')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: api.operationDetail(operationId),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError) return const Center(child: Text('No fue posible cargar el detalle.'));
        final d = snapshot.data!; final schedule = List<dynamic>.from(d['schedule'] as List? ?? []); final payments = List<dynamic>.from(d['payments'] as List? ?? []);
        return ListView(padding: const EdgeInsets.all(16), children: [
          Text(d['name'].toString(), style: Theme.of(context).textTheme.headlineSmall), const SizedBox(height: 8),
          Text('Capital pendiente: ' + d['currency'].toString() + ' ' + money(d['outstanding_capital'])),
          Text('Tasa: ' + d['interest_rate'].toString() + '% ' + d['rate_period'].toString()),
          Text('Plazo: ' + d['term_months'].toString() + ' meses'), const SizedBox(height: 22),
          Text('Cuotas', style: Theme.of(context).textTheme.titleLarge),
          ...schedule.map((item) { final line = Map<String, dynamic>.from(item as Map); return ListTile(contentPadding: EdgeInsets.zero, title: Text('Cuota ' + line['sequence'].toString() + ' - ' + line['date'].toString()), subtitle: Text('Capital ' + money(line['capital']) + ' + interes ' + money(line['interest'])), trailing: Text(d['currency'].toString() + ' ' + money(line['amount_due']))); }),
          const Divider(), Text('Pagos realizados', style: Theme.of(context).textTheme.titleLarge),
          if (payments.isEmpty) const ListTile(contentPadding: EdgeInsets.zero, title: Text('Sin pagos registrados')),
          ...payments.map((item) { final p = Map<String, dynamic>.from(item as Map); return ListTile(contentPadding: EdgeInsets.zero, title: Text(p['date'].toString()), subtitle: Text('Capital ' + money(p['capital']) + ' | Interes ' + money(p['interest'])), trailing: Text(d['currency'].toString() + ' ' + money(p['net_amount']))); }),
        ]);
      },
    ),
  );
}
