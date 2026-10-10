import 'package:flutter/material.dart';

import 'api.dart';
import 'brand.dart';
import 'presentation.dart';

class StatementsPage extends StatefulWidget {
  const StatementsPage({super.key, required this.repository});
  final SavingsRepository repository;
  @override
  State<StatementsPage> createState() => _StatementsPageState();
}

class _StatementsPageState extends State<StatementsPage> {
  late Future<List<Map<String, dynamic>>> pending;
  StatementCategory category = StatementCategory.all;
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
        final data = snapshot.data!;
        if (data.isEmpty)
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text('Todavía no tenés estados de cuenta emitidos.'),
            ),
          );
        final rows = statementRows(data, category);
        return ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Wrap(
              spacing: 8,
              children: [
                for (final option in StatementCategory.values)
                  ChoiceChip(
                    label: Text(switch (option) {
                      StatementCategory.all => 'Todos',
                      StatementCategory.savings => 'Ahorros',
                      StatementCategory.credit => 'Créditos',
                    }),
                    selected: category == option,
                    onSelected: (_) => setState(() => category = option),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'Los saldos corresponden al cierre del período indicado; pueden diferir del saldo actual.',
            ),
            const SizedBox(height: 16),
            if (rows.isEmpty)
              const Text('No hay estados de cuenta de esta categoría.'),
            for (final row in rows)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(statementTypeLabel(row['type'] as String)),
                      Text(
                        row['name'] as String? ?? 'Estado de cuenta',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        '${displayDate(row['date_from'] as String)} — ${displayDate(row['date_to'] as String)}',
                      ),
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
            color: LenkaBrand.ivory,
            child: Center(
              child: Text(
                'Lenka · Tu información es privada',
                textDirection: TextDirection.ltr,
                style: TextStyle(color: LenkaBrand.ink, fontSize: 20),
              ),
            ),
          ),
        ),
    ],
  );
}
