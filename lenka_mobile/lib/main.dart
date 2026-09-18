import 'package:flutter/material.dart';

void main() => runApp(const LenkaApp());

class LenkaApp extends StatelessWidget {
  const LenkaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Inversiones Lenka',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF7DB8E6)),
        useMaterial3: true,
      ),
      home: const LenkaWelcomeScreen(),
    );
  }
}

class LenkaWelcomeScreen extends StatelessWidget {
  const LenkaWelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.account_balance, size: 80),
                const SizedBox(height: 20),
                Text('Inversiones Lenka',
                    style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 8),
                const Text(
                  'Tus préstamos, inversiones, intereses y estados de cuenta en un solo lugar.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
