import 'package:flutter/material.dart';

import 'core/lenka_api_client.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';

void main() { WidgetsFlutterBinding.ensureInitialized(); runApp(const LenkaApp()); }

class LenkaApp extends StatefulWidget {
  const LenkaApp({super.key});
  @override
  State<LenkaApp> createState() => _LenkaAppState();
}

class _LenkaAppState extends State<LenkaApp> {
  final api = LenkaApiClient(
    baseUrl: const String.fromEnvironment('LENKA_ODOO_URL', defaultValue: 'https://example.odoo.com'),
    database: const String.fromEnvironment('LENKA_ODOO_DB', defaultValue: 'odoo'),
  );
  bool? loggedIn;

  @override
  void initState() { super.initState(); restore(); }
  Future<void> restore() async { final value = await api.hasSession(); if (mounted) setState(() => loggedIn = value); }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Inversiones Lenka',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF7DB8E6)), useMaterial3: true),
      home: loggedIn == null
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : loggedIn!
              ? DashboardScreen(api: api, onLogout: () => setState(() => loggedIn = false))
              : LoginScreen(api: api, onLoggedIn: () => setState(() => loggedIn = true)),
    );
  }
}
