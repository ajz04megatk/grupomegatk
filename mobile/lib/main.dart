import 'dart:async';

import 'package:flutter/material.dart';

import 'api.dart';
import 'brand.dart';
import 'idle_policy.dart';
import 'statements.dart';
import 'presentation.dart';
export 'presentation.dart' show money;

void main() {
  const host = String.fromEnvironment('LENKA_ORIGIN');
  const database = String.fromEnvironment('LENKA_DATABASE');
  SavingsRepository? repository;
  if (host.isNotEmpty && database.isNotEmpty) {
    try {
      repository = OdooSavingsRepository(Uri.parse(host), database);
    } catch (_) {
      /* Fail closed when configuration is missing or invalid. */
    }
  }
  runApp(LenkaApp(repository: repository));
}

class LenkaApp extends StatefulWidget {
  const LenkaApp({super.key, required this.repository, this.elapsed});
  final SavingsRepository? repository;
  final Duration Function()? elapsed;
  @override
  State<LenkaApp> createState() => _LenkaAppState();
}

class _LenkaAppState extends State<LenkaApp> with WidgetsBindingObserver {
  final navigator = GlobalKey<NavigatorState>();
  final clock = Stopwatch()..start();
  final idle = IdlePolicy();
  Timer? timer;
  Duration get elapsed => widget.elapsed?.call() ?? clock.elapsed;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    timer = Timer.periodic(const Duration(seconds: 1), (_) => checkIdle());
  }

  @override
  void dispose() {
    timer?.cancel();
    clock.stop();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void checkIdle() {
    if (!mounted || !idle.expired(elapsed)) return;
    idle.stop();
    widget.repository?.logout();
    navigator.currentState?.pushAndRemoveUntil(
      PageRouteBuilder<void>(
        transitionDuration: Duration.zero,
        reverseTransitionDuration: Duration.zero,
        pageBuilder: (_, __, ___) => loginPage(
          message: 'Cerramos tu sesión después de 5 minutos sin actividad. Ingresá nuevamente.',
        ),
      ),
      (_) => false,
    );
  }

  void activity() {
    checkIdle();
    idle.touch(elapsed);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) checkIdle();
  }

  Widget loginPage({String? message}) => LoginPage(
    repository: widget.repository!,
    initialMessage: message,
    onAuthenticated: () => idle.start(elapsed),
    onSessionEnded: idle.stop,
  );

  @override
  Widget build(BuildContext context) => MaterialApp(
    navigatorKey: navigator,
    builder: (context, child) => Listener(
      onPointerDown: (_) => activity(),
      onPointerMove: (_) => activity(),
      onPointerSignal: (_) => activity(),
      child: PrivacyCover(child: child ?? const SizedBox.shrink()),
    ),
    title: 'Lenka',
    debugShowCheckedModeBanner: false,
    theme: LenkaBrand.theme,
    home: widget.repository == null
        ? const Scaffold(
            body: Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('Esta versión todavía no está conectada a Lenka.'),
              ),
            ),
          )
        : loginPage(),
  );
}

class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    required this.repository,
    this.initialMessage,
    this.onAuthenticated,
    this.onSessionEnded,
  });
  final SavingsRepository repository;
  final String? initialMessage;
  final VoidCallback? onAuthenticated;
  final VoidCallback? onSessionEnded;
  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> with WidgetsBindingObserver {
  final email = TextEditingController();
  final password = TextEditingController();
  final emailFocus = FocusNode();
  final passwordFocus = FocusNode();
  bool showPassword = false;
  bool attempted = false;
  bool busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed && showPassword && mounted) {
      setState(() => showPassword = false);
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    emailFocus.dispose();
    passwordFocus.dispose();
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (busy) return;
    setState(() => attempted = true);
    if (email.text.trim().isEmpty || password.text.isEmpty) {
      setState(() => error = null);
      (email.text.trim().isEmpty ? emailFocus : passwordFocus).requestFocus();
      return;
    }
    FocusScope.of(context).unfocus();
    setState(() {
      busy = true;
      showPassword = false;
      error = null;
    });
    try {
      await widget.repository.login(email.text, password.text);
      if (!mounted) {
        await widget.repository.logout();
        return;
      }
      password.clear();
      widget.onAuthenticated?.call();
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => SavingsPage(repository: widget.repository),
        ),
      );
    } on LenkaFailure catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted)
        setState(() => error = 'No pudimos ingresar. Volvé a intentar.');
    } finally {
      widget.onSessionEnded?.call();
      if (mounted) {
        password.clear();
        setState(() {
          busy = false;
          attempted = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(28),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Center(child: LenkaLogo()),
                const SizedBox(height: 16),
                Text(
                  'Bienvenido a Lenka',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const Text('Tus ahorros, siempre a mano.'),
                if (widget.initialMessage != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Text(widget.initialMessage!),
                  ),
                const SizedBox(height: 32),
                TextField(
                  controller: email,
                  focusNode: emailFocus,
                  onChanged: (_) => setState(() => error = null),
                  enabled: !busy,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  textInputAction: TextInputAction.next,
                  decoration: InputDecoration(
                    labelText: 'Correo electrónico',
                    errorText: attempted && email.text.trim().isEmpty
                        ? 'Escribí tu correo.'
                        : null,
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: password,
                  focusNode: passwordFocus,
                  onChanged: (_) => setState(() => error = null),
                  enabled: !busy,
                  obscureText: !showPassword,
                  autocorrect: false,
                  enableSuggestions: false,
                  textInputAction: TextInputAction.done,
                  decoration: InputDecoration(
                    labelText: 'Contraseña',
                    errorText: attempted && password.text.isEmpty
                        ? 'Escribí tu contraseña.'
                        : null,
                    suffixIcon: IconButton(
                      tooltip: showPassword
                          ? 'Ocultar contraseña'
                          : 'Mostrar contraseña',
                      onPressed: busy
                          ? null
                          : () => setState(() => showPassword = !showPassword),
                      icon: Icon(
                        showPassword ? Icons.visibility_off : Icons.visibility,
                      ),
                    ),
                  ),
                  onSubmitted: (_) => submit(),
                ),
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Semantics(
                      liveRegion: true,
                      child: Text(
                        error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ),
                  ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: busy ? null : submit,
                  child: Text(busy ? 'Ingresando…' : 'Ingresar'),
                ),
                const SizedBox(height: 16),
                const Text(
                  '¿Necesitás habilitar tu cuenta o recuperar el acceso? Contactá a Lenka.',
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class SavingsPage extends StatefulWidget {
  const SavingsPage({super.key, required this.repository});
  final SavingsRepository repository;
  @override
  State<SavingsPage> createState() => _SavingsPageState();
}

class _SavingsPageState extends State<SavingsPage> {
  final search = TextEditingController();
  String? selectedCurrency;
  List<Map<String, dynamic>> get visibleRows => filterDeposits(
    rows ?? [],
    query: search.text,
    currency: selectedCurrency,
  );
  List<Map<String, dynamic>>? rows;
  bool busy = true;
  int refreshVersion = 0;
  String? error;
  @override
  void initState() {
    super.initState();
    refresh();
  }

  @override
  void dispose() {
    search.dispose();
    widget.repository.logout();
    super.dispose();
  }

  Future<void> refresh() async {
    final version = ++refreshVersion;
    setState(() {
      busy = true;
      rows = null;
      error = null;
    });
    try {
      final result = await widget.repository.investments();
      if (mounted && version == refreshVersion) {
        setState(() => rows = result);
      }
    } on LenkaFailure catch (e) {
      if (!mounted || version != refreshVersion) return;
      if (e.sessionExpired) {
        Navigator.of(context).popUntil((route) => route.isFirst);
        return;
      }
      setState(() => error = e.message);
    } catch (_) {
      if (mounted && version == refreshVersion) {
        setState(
          () => error = 'No pudimos consultar tus ahorros. Volvé a intentar.',
        );
      }
    } finally {
      if (mounted && version == refreshVersion) {
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Mis ahorros'),
      automaticallyImplyLeading: false,
      actions: [
        IconButton(
          tooltip: 'Estados de cuenta',
          icon: const Icon(Icons.receipt_long),
          onPressed: () => Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => StatementsPage(repository: widget.repository),
            ),
          ),
        ),
        IconButton(
          tooltip: 'Actualizar',
          onPressed: busy ? null : refresh,
          icon: const Icon(Icons.refresh),
        ),
        IconButton(
          tooltip: 'Cerrar sesión',
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.logout),
        ),
      ],
    ),
    body: busy
        ? const Center(child: CircularProgressIndicator())
        : error != null
        ? Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(error!),
                  FilledButton(
                    onPressed: refresh,
                    child: const Text('Volver a intentar'),
                  ),
                ],
              ),
            ),
          )
        : RefreshIndicator(
            onRefresh: refresh,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(20),
              children: [
                for (final total in savingsTotals(rows!))
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Mis ahorros · ${total.currency}'),
                          Text(
                            total.formatted,
                            style: Theme.of(context).textTheme.headlineMedium,
                          ),
                          Text(
                            '${total.deposits} depósitos activos o vencidos',
                          ),
                          const Text(
                            'Capital vigente. No incluye intereses ni contratos cerrados.',
                          ),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 20),
                const Text(
                  'Capital vigente por depósito',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                ),
                const Text(
                  'Los importes conservan su moneda. El capital a plazo está sujeto a las condiciones de tu contrato.',
                ),
                const SizedBox(height: 20),
                TextField(
                  controller: search,
                  onChanged: (_) => setState(() {}),
                  autocorrect: false,
                  decoration: InputDecoration(
                    labelText: 'Buscar depósito por nombre o referencia',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: search.text.isEmpty
                        ? null
                        : IconButton(
                            tooltip: 'Limpiar búsqueda',
                            icon: const Icon(Icons.clear),
                            onPressed: () => setState(search.clear),
                          ),
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  children: [
                    for (final currency in <String?>[null, 'HNL', 'USD'])
                      ChoiceChip(
                        label: Text(
                          currency == null
                              ? 'Todas las monedas'
                              : currency == 'HNL'
                              ? 'Lempiras'
                              : 'Dólares',
                        ),
                        selected: selectedCurrency == currency,
                        onSelected: (_) =>
                            setState(() => selectedCurrency = currency),
                      ),
                  ],
                ),
                const Text(
                  'Los totales superiores incluyen todos tus depósitos vigentes, aunque filtres esta lista.',
                ),
                const SizedBox(height: 16),
                if (rows!.isEmpty)
                  const Text(
                    'Todavía no tenés depósitos registrados para consultar.',
                  ),
                if (rows!.isNotEmpty && visibleRows.isEmpty)
                  const Text('No encontramos depósitos con esos filtros.'),
                for (final row in visibleRows)
                  Card(
                    child: ListTile(
                      contentPadding: const EdgeInsets.all(16),
                      title: Text(
                        money(
                          row['outstanding_principal'],
                          row['currency'] as String? ?? '',
                        ),
                        style: const TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      subtitle: Text(
                        '${row['name']}\n${stateLabel(row['state'])}',
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => DepositPage(
                            repository: widget.repository,
                            id: row['id'] as int,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
  );
}

String stateLabel(dynamic state) =>
    const {
      'active': 'Activo',
      'matured': 'Vencido',
      'closed': 'Cerrado',
      'draft': 'Pendiente',
      'accrued': 'Registrado',
      'paid': 'Pagado',
    }[state] ??
    'Consultar con Lenka';

class DepositPage extends StatefulWidget {
  const DepositPage({super.key, required this.repository, required this.id});
  final SavingsRepository repository;
  final int id;
  @override
  State<DepositPage> createState() => _DepositPageState();
}

class _DepositPageState extends State<DepositPage> {
  late Future<Map<String, dynamic>> pending;
  @override
  void initState() {
    super.initState();
    pending = widget.repository.detail(widget.id);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Mi depósito')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: pending,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done)
          return const Center(child: CircularProgressIndicator());
        if (snap.hasError)
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    snap.error is LenkaFailure
                        ? (snap.error as LenkaFailure).message
                        : 'No pudimos consultar el depósito.',
                  ),
                  FilledButton(
                    onPressed: () {
                      if (snap.error is LenkaFailure &&
                          (snap.error as LenkaFailure).sessionExpired) {
                        Navigator.of(context)
                            .popUntil((route) => route.isFirst);
                      } else {
                        setState(
                          () => pending = widget.repository.detail(widget.id),
                        );
                      }
                    },
                    child: const Text('Continuar'),
                  ),
                ],
              ),
            ),
          );
        final data = snap.data!;
        final currency = data['currency'] as String? ?? '';
        final movements = depositMovements(data, widget.id);
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              data['name'] as String? ?? 'Depósito',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const Text('Capital vigente'),
            Text(
              money(data['outstanding_principal'], currency),
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            Text(
              'Intereses históricos: ${money(data['accrued_interest'], currency)}',
            ),
            const Text(
              'Incluyen intereses ya pagados. No representan saldo disponible.',
            ),
            Text(
              'Intereses netos pagados: ${money(data['paid_interest'], currency)}',
            ),
            const Divider(height: 40),
            Text(
              'Condiciones del depósito',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            for (final condition in depositConditions(data, widget.id))
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(condition),
              ),
            const SizedBox(height: 12),
            const Text(
              'Las tasas corresponden al período indicado. El importe de un retiro anticipado debe confirmarse con Lenka según tu contrato.',
            ),
            const Divider(height: 40),
            Text('Movimientos', style: Theme.of(context).textTheme.titleLarge),
            const Text(
              'Los intereses pagados pueden formar parte de un retiro. No sumés ambos importes como ingresos separados.',
            ),
            if (movements.isEmpty)
              const Text('No hay movimientos registrados.'),
            for (final item in movements)
              ListTile(
                title: Text(item.label),
                subtitle: Text(
                  [displayDate(item.date), ...item.details].join('\n'),
                ),
                trailing: Text(money(item.amount, currency)),
              ),
          ],
        );
      },
    ),
  );
}
