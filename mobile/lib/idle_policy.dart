/// Monotonic time only: changing the phone's date cannot extend a session.
class IdlePolicy {
  IdlePolicy({this.timeout = const Duration(minutes: 5)}) {
    if (timeout <= Duration.zero) throw ArgumentError.value(timeout);
  }
  final Duration timeout;
  Duration? _lastActivity;
  bool get active => _lastActivity != null;
  void start(Duration now) => _lastActivity = now;
  void stop() => _lastActivity = null;
  bool expired(Duration now) => active && now - _lastActivity! >= timeout;
  // A late tap must never revive an expired session.
  void touch(Duration now) {
    if (active && !expired(now)) _lastActivity = now;
  }
}
