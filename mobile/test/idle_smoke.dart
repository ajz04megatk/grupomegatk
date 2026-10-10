import '../lib/idle_policy.dart';

void check(bool value, String message) {
  if (!value) throw StateError(message);
}

void main() {
  final policy = IdlePolicy();
  check(
    !policy.active && !policy.expired(const Duration(days: 1)),
    'Login timed out',
  );
  policy.start(Duration.zero);
  check(
    !policy.expired(const Duration(minutes: 4, seconds: 59)),
    'Early expiry',
  );
  check(policy.expired(const Duration(minutes: 5)), 'Boundary not expired');
  policy.touch(const Duration(minutes: 6));
  check(policy.expired(const Duration(minutes: 6)), 'Late tap revived session');
  policy.start(const Duration(minutes: 10));
  policy.touch(const Duration(minutes: 14));
  check(!policy.expired(const Duration(minutes: 18)), 'Activity ignored');
  check(
    policy.expired(const Duration(minutes: 19)),
    'Activity extended forever',
  );
  policy.stop();
  check(!policy.active, 'Logout did not stop policy');
  policy.touch(const Duration(hours: 1));
  check(!policy.active, 'Touch started a logged-out session');
  bool invalid = false;
  try {
    IdlePolicy(timeout: Duration.zero);
  } on ArgumentError {
    invalid = true;
  }
  check(invalid, 'Invalid timeout accepted');
  print('PASS: 9 idle-session checks using a monotonic clock.');
}
