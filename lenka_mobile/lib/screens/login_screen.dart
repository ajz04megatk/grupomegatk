import 'package:flutter/material.dart';

import '../core/lenka_api_client.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.api, required this.onLoggedIn});
  final LenkaApiClient api;
  final VoidCallback onLoggedIn;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool loading = false;
  String? error;

  Future<void> submit() async {
    setState(() { loading = true; error = null; });
    try {
      await widget.api.login(email.text.trim(), password.text);
      if (mounted) widget.onLoggedIn();
    } on LenkaApiException catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) setState(() => error = 'No fue posible conectarse con Inversiones Lenka.');
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const Icon(Icons.account_balance, size: 76),
                const SizedBox(height: 18),
                Text('Inversiones Lenka', textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 8),
                const Text('Consulta tus operaciones, inversiones e intereses.', textAlign: TextAlign.center),
                const SizedBox(height: 30),
                TextField(controller: email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Correo electronico', border: OutlineInputBorder())),
                const SizedBox(height: 14),
                TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Contrasena', border: OutlineInputBorder()), onSubmitted: (_) => loading ? null : submit()),
                if (error != null) ...[const SizedBox(height: 12), Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error))],
                const SizedBox(height: 18),
                FilledButton(onPressed: loading ? null : submit, child: Padding(padding: const EdgeInsets.symmetric(vertical: 14), child: loading ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Ingresar'))),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}
