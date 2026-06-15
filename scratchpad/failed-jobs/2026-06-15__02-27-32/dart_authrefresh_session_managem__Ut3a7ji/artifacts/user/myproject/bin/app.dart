import 'dart:convert';
import 'dart:io';

import 'package:pocketbase/pocketbase.dart';

/// Path to the session file (relative to the current working directory).
final _sessionFile = File('session.json');

// ---------------------------------------------------------------------------
// JWT helpers – we decode the payload without verifying the signature because
// we only need the `exp` claim for display purposes.
// ---------------------------------------------------------------------------

/// Decodes a JWT and returns its payload as a [Map].
/// Throws a [FormatException] if the token is structurally invalid.
Map<String, dynamic> _decodeJwtPayload(String token) {
  final parts = token.split('.');
  if (parts.length != 3) {
    throw const FormatException('Token is not a valid JWT (wrong segment count)');
  }

  // Base64-url decode the payload segment (add padding as required).
  var payload = parts[1];
  final remainder = payload.length % 4;
  if (remainder != 0) {
    payload = payload.padRight(payload.length + (4 - remainder), '=');
  }

  final decoded = utf8.decode(base64Url.decode(payload));
  final dynamic json = jsonDecode(decoded);
  if (json is! Map<String, dynamic>) {
    throw const FormatException('JWT payload is not a JSON object');
  }
  return json;
}

// ---------------------------------------------------------------------------
// Session persistence
// ---------------------------------------------------------------------------

/// Writes [token] and the serialised [record] to [_sessionFile].
Future<void> _saveSession(String token, RecordModel record) async {
  final data = jsonEncode({
    'token': token,
    'record': record.toJson(),
  });
  await _sessionFile.writeAsString(data);
}

/// Loads the session file and returns `{'token': String, 'record': Map}`.
/// Returns `null` when the file does not exist.
/// Throws a [FormatException] when the content is invalid.
Future<Map<String, dynamic>> _loadSession() async {
  if (!await _sessionFile.exists()) {
    throw const FormatException('session.json does not exist');
  }

  final raw = await _sessionFile.readAsString();
  final dynamic decoded = jsonDecode(raw); // throws FormatException on bad JSON

  if (decoded is! Map<String, dynamic>) {
    throw const FormatException('session.json root must be a JSON object');
  }

  final token = decoded['token'];
  if (token == null || token is! String || token.isEmpty) {
    throw const FormatException('session.json is missing a non-empty "token"');
  }

  return decoded;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

/// `login <email> <password>` — authenticates and persists the session.
Future<void> commandLogin(List<String> args) async {
  if (args.length < 2) {
    stderr.writeln('Usage: app login <email> <password>');
    exit(1);
  }

  final email = args[0];
  final password = args[1];

  final pb = PocketBase('http://127.0.0.1:8090');
  final result = await pb.collection('users').authWithPassword(email, password);

  await _saveSession(result.token, result.record);
  exit(0);
}

/// `refresh` — loads the session, refreshes the token, persists the new one,
/// then prints the user record id and the token `exp` epoch (seconds).
Future<void> commandRefresh() async {
  // --- load & validate session -------------------------------------------------
  Map<String, dynamic> session;
  try {
    session = await _loadSession();
  } on FormatException {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  } on Object {
    // Any unexpected I/O error is also treated as an invalid session.
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final token = session['token'] as String;

  // --- build a PocketBase client pre-seeded with the stored token --------------
  final pb = PocketBase('http://127.0.0.1:8090');

  // Restore the auth store so authRefresh() can attach the Authorization header.
  final recordMap = session['record'];
  if (recordMap is! Map<String, dynamic>) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }
  pb.authStore.save(token, RecordModel.fromJson(recordMap));

  // --- call authRefresh() on the users collection ------------------------------
  final result = await pb.collection('users').authRefresh();

  final newToken = result.token;

  // Persist only when the token actually changed.
  if (newToken != token) {
    await _saveSession(newToken, result.record);
  }

  // --- decode exp from the (possibly new) token --------------------------------
  final Map<String, dynamic> payload;
  try {
    payload = _decodeJwtPayload(newToken);
  } on FormatException {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final dynamic expRaw = payload['exp'];
  if (expRaw == null) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final int exp;
  if (expRaw is int) {
    exp = expRaw;
  } else if (expRaw is double) {
    exp = expRaw.toInt();
  } else {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  // Two lines, nothing else.
  stdout.writeln(result.record.id);
  stdout.writeln(exp);
  exit(0);
}

// ---------------------------------------------------------------------------
// Entry-point
// ---------------------------------------------------------------------------

Future<void> main(List<String> arguments) async {
  if (arguments.isEmpty) {
    stderr.writeln('Usage: app <login|refresh> [args...]');
    exit(1);
  }

  final command = arguments[0];

  switch (command) {
    case 'login':
      await commandLogin(arguments.sublist(1));
    case 'refresh':
      await commandRefresh();
    default:
      stderr.writeln('Unknown command: $command');
      stderr.writeln('Usage: app <login|refresh> [args...]');
      exit(1);
  }
}
