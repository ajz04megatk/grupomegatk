"""Run SDK-only checks. Does not invoke Flutter, Odoo, builds or deployment."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dart', required=True, type=Path,
                        help='Absolute path to the Dart SDK executable (dart or dart.exe).')
    args = parser.parse_args()
    dart = args.dart.resolve()
    if not dart.is_file() or dart.name.lower() not in ('dart', 'dart.exe'):
        parser.error('Provide the Dart SDK executable; this script does not run Flutter.')
    root = Path(__file__).resolve().parent
    icon = root / 'assets/lenka-icon.png'
    expected = 'decb67ae8bec87f9c98953989559cf11264be28ec26bf65d705344bf7b108517'
    if hashlib.sha256(icon.read_bytes()).hexdigest() != expected:
        raise SystemExit('FAIL: official icon differs from the approved source.')
    suites = ['api_smoke', 'session_smoke', 'response_smoke', 'validation_smoke',
              'presentation_smoke', 'statements_smoke', 'idle_smoke', 'boundary_smoke']
    sources = ['lib/api.dart', 'lib/validation.dart', 'lib/presentation.dart',
               'lib/idle_policy.dart', 'lib/session_boundary.dart'] + [f'test/{suite}.dart' for suite in suites]
    commands = [[str(dart), 'analyze', *sources]]
    commands.extend([str(dart), f'test/{suite}.dart'] for suite in suites)
    commands.append([sys.executable, '-m', 'unittest', 'discover',
                     '-s', str(root.parent / 'mobile-tests'), '-v'])
    for command in commands:
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
    print('PASS: SDK-only checks and original icon verification.')
    print('NOT RUN: Flutter/widgets, Odoo integration, Android/iOS builds or device checks.')


if __name__ == '__main__':
    main()
