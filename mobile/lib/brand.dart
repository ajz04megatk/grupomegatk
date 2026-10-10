import 'package:flutter/material.dart';

/// Representative colors sampled from the official textured Lenka icon.
/// The source image has tonal variations, so these are interface base colors.
abstract final class LenkaBrand {
  static const iconAsset = 'assets/lenka-icon.png';
  static const sky = Color(0xff85c6e7);
  static const ink = Color(0xff1a1a18);
  static const ivory = Color(0xffedebe6);

  static ThemeData get theme {
    final colors =
        ColorScheme.fromSeed(
          seedColor: sky,
          brightness: Brightness.light,
        ).copyWith(
          primary: sky,
          onPrimary: ink,
          primaryContainer: sky,
          onPrimaryContainer: ink,
          secondary: ink,
          onSecondary: Colors.white,
          secondaryContainer: sky,
          onSecondaryContainer: ink,
          surface: Colors.white,
          onSurface: ink,
          onSurfaceVariant: ink,
        );
    return ThemeData(
      useMaterial3: true,
      colorScheme: colors,
      scaffoldBackgroundColor: ivory,
      appBarTheme: const AppBarTheme(
        backgroundColor: sky,
        foregroundColor: ink,
        surfaceTintColor: Colors.transparent,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: ink),
      textSelectionTheme: const TextSelectionThemeData(
        cursorColor: ink,
        selectionColor: sky,
        selectionHandleColor: ink,
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(),
        focusedBorder: OutlineInputBorder(
          borderSide: BorderSide(color: ink, width: 2),
        ),
        floatingLabelStyle: TextStyle(color: ink),
      ),
    );
  }
}

class LenkaLogo extends StatelessWidget {
  const LenkaLogo({super.key, this.size = 104});
  final double size;

  @override
  Widget build(BuildContext context) => Image.asset(
    LenkaBrand.iconAsset,
    width: size,
    height: size,
    fit: BoxFit.contain,
    semanticLabel: 'Inversiones Lenka',
  );
}
