import 'package:flutter/material.dart';

import 'api.dart';
import 'main.dart' show money;

class StatementsPage extends StatefulWidget {
  const StatementsPage({super.key, required this.repository});
  final SavingsRepository repository;
  @override
  State<StatementsPage> createState() => _StatementsPageState();
}

class _StatementsPageState extends State<StatementsPage> {
  late Future<List<Map<String, dynamic>>> pending;
  @override
  void initState() {
    super.initState();
    pending = widget.repository.statements();
  }

  void reload() {
    setState(() => pending = widget.repository.statements());
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Estados de cuenta'),
      actions: [
        IconButton(
          onPressed: reload,
          tooltip: 'Actualizar',
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: pending,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          final failure = snapshot.error;
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    failure is LenkaFailure
                        ? failure.message
                        : 'No pudimos consultar tus estados de cuenta.',
                  ),
                  FilledButton(
                    onPressed: () {
                      if (failure is LenkaFailure && failure.sessionExpired) {
                        Navigator.of(context)
                            .popUntil((route) => route.isFirst);
                      } else {
                        reload();
                      }
                    },
                    child: const Text('Continuar'),
                  ),
                ],
              ),
            ),
          );
        }
        final rows = snapshot.data!;
        if (rows.isEmpty)
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text('Todavía no tenés estados de cuenta emitidos.'),
            ),
          );
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            const Text(
              'Los saldos corresponden al cierre del período indicado; pueden diferir del saldo actual.',
            ),
            const SizedBox(height: 16),
            for (final row in rows)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        row['name'] as String? ?? 'Estado de cuenta',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text('${row['date_from']} — ${row['date_to']}'),
                      const SizedBox(height: 12),
                      Text(
                        'Saldo inicial: ${money(row['opening_balance'], row['currency'] as String? ?? '')}',
                      ),
                      Text(
                        'Saldo al cierre: ${money(row['closing_balance'], row['currency'] as String? ?? '')}',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    ),
  );
}

/// Hides financial screens while the app is inactive or in the background.
/// This does not claim to prevent OS screenshots; device testing is required.
class PrivacyCover extends StatefulWidget {
  const PrivacyCover({super.key, required this.child});
  final Widget child;
  @override
  State<PrivacyCover> createState() => _PrivacyCoverState();
}

class _PrivacyCoverState extends State<PrivacyCover>
    with WidgetsBindingObserver {
  bool hidden = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (mounted) setState(() => hidden = state != AppLifecycleState.resumed);
  }

  @override
  Widget build(BuildContext context) => Stack(
    fit: StackFit.expand,
    children: [
      ExcludeSemantics(
        excluding: hidden,
        child: IgnorePointer(ignoring: hidden, child: widget.child),
      ),
      if (hidden)
        const Positioned.fill(
          child: ColoredBox(
            color: Color(0xfff4f7fa),
            child: Center(
              child: Text(
                'Lenka · Tu información es privada',
                textDirection: TextDirection.ltr,
                style: TextStyle(color: Color(0xff075e88), fontSize: 20),
              ),
            ),
          ),
        ),
    ],
  );
}
