import 'package:shared_preferences/shared_preferences.dart';

class AuthSession {
  static const String _keyUserId = 'user_id';
  static const String _keyUserEmail = 'user_email';
  static const String _keySessionExpiration = 'session_expiration';

  static Future<void> setSession({
    required String userId,
    required String userEmail,
    required DateTime expirationTime,
  }) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_keyUserId, userId);
    await preferences.setString(_keyUserEmail, userEmail);
    await preferences.setString(
        _keySessionExpiration, expirationTime.toIso8601String());
  }

  static Future<Map<String, dynamic>?> getSession() async {
    final preferences = await SharedPreferences.getInstance();
    final userId = preferences.getString(_keyUserId);
    final userEmail = preferences.getString(_keyUserEmail);
    final sessionExpirationString =
    preferences.getString(_keySessionExpiration);

    if (userId != null && userEmail != null && sessionExpirationString != null) {
      final sessionExpiration = DateTime.parse(sessionExpirationString);
      final bool isActive = DateTime.now().isBefore(sessionExpiration);
      return {
        'userId': userId,
        'userEmail': userEmail,
        'sessionExpiration': sessionExpiration,
        'isActive': isActive,
      };
    }
    return null;
  }

  static Future<void> clearSession() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(_keyUserId);
    await preferences.remove(_keyUserEmail);
    await preferences.remove(_keySessionExpiration);
  }
}