import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/lenka_api_client.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.api, required this.onLogout});
  final LenkaApiClient api;
  final VoidCallback onLogout;
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<Map<String, dynamic>> data;
  @override
  void initState() { super.initState(); data = widget.api.dashboard(); }

  String money(dynamic value) => NumberFormat('#,##0.00').format((value as num?) ?? 0);
  Future<void> refresh() async { setState(() => data = widget.api.dashboard()); await data; }
  Future<void> logout() async { await widget.api.logout(); widget.onLogout(); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Inversiones Lenka'), actions: [IconButton(onPressed: logout, icon: const Icon(Icons.logout), tooltip: 'Cerrar sesion')]),
      body: FutureBuilder<Map<String, dynamic>>(
        future: data,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (snapshot.hasError) return Center(child: FilledButton(onPressed: refresh, child: const Text('Reintentar')));
          final d = snapshot.data!;
          final partner = Map<String, dynamic>.from(d['partner'] as Map);
          final ops = Map<String, dynamic>.from(d['operations'] as Map);
          final inv = Map<String, dynamic>.from(d['investments'] as Map);
          return RefreshIndicator(
            onRefresh: refresh,
            child: ListView(padding: const EdgeInsets.all(16), children: [
              Text('Hola, ' + partner['name'].toString(), style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 18),
              _Card(title: 'Prestamos y financiamientos', icon: Icons.payments_outlined, lines: [
                ops['count'].toString() + ' operaciones',
                'Capital pendiente: ' + money(ops['outstanding_capital']),
                'Intereses pagados: ' + money(ops['paid_interest']),
              ]),
              const SizedBox(height: 12),
              _Card(title: 'Inversiones y depositos', icon: Icons.savings_outlined, lines: [
                inv['count'].toString() + ' inversiones',
                'Capital vigente: ' + money(inv['outstanding_principal']),
                'Interes acumulado: ' + money(inv['accrued_interest']),
              ]),
              const SizedBox(height: 22),
              const ListTile(leading: Icon(Icons.calendar_month_outlined), title: Text('Cuotas y vencimientos')),
              const ListTile(leading: Icon(Icons.trending_up), title: Text('Detalle de inversiones e intereses')),
              const ListTile(leading: Icon(Icons.receipt_long_outlined), title: Text('Estados de cuenta')),
            ]),
          );
        },
      ),
    );
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.title, required this.icon, required this.lines});
  final String title;
  final IconData icon;
  final List<String> lines;
  @override
  Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(18), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Icon(icon, size: 34), const SizedBox(width: 14), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title, style: Theme.of(context).textTheme.titleMedium), const SizedBox(height: 8), ...lines.map((line) => Padding(padding: const EdgeInsets.only(bottom: 4), child: Text(line))),
    ])),
  ])));
}
