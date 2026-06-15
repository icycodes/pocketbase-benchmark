import 'dart:convert';
import 'dart:io';

import 'package:pocketbase/pocketbase.dart';

const _baseURL = 'http://127.0.0.1:8090';
const _collection = 'users';
const _sessionFile = 'session.json';

void main(List<String> args) {
  if (args.isEmpty) {
    stderr.writeln('Usage: dart run bin/app.dart <login|refresh> [...]');
    exit(1);
  }

  final command = args[0];

  switch (command) {
    case 'login':
      if (args.length != 3) {
        stderr.writeln('Usage: dart run bin/app.dart login <email> <password>');
        exit(1);
      }
      _login(args[1], args[2]);
      break;
    case 'refresh':
      _refresh();
      break;
    default:
      stderr.writeln('Unknown command: $command');
      exit(1);
  }
}

/// Decodes the payload of a JWT token and returns it as a Map.
Map<String, dynamic> _decodeJwtPayload(String token) {
  final parts = token.split('.');
  if (parts.length != 3) {
    throw FormatException('invalid JWT format');
  }
  final payload = parts[1];
  final normalized = base64.normalize(payload);
  final decoded = utf8.decode(base64Decode(normalized));
  return jsonDecode(decoded) as Map<String, dynamic>;
}

/// Extracts the `exp` claim from a JWT token as an integer epoch (seconds).
int _getExp(String token) {
  final payload = _decodeJwtPayload(token);
  return payload['exp'] as int;
}

/// Handles the `login` command.
void _login(String email, String password) {
  final pb = PocketBase(_baseURL);

  pb.collection(_collection).authWithPassword(email, password).then((auth) {
    final token = auth.token;
    if (token.isEmpty) {
      stderr.writeln('Login failed: empty token');
      exit(1);
    }

    final session = {'token': token};
    File(_sessionFile).writeAsStringSync(jsonEncode(session));
    exit(0);
  }).catchError((error) {
    stderr.writeln('Login failed: $error');
    exit(1);
  });
}

/// Handles the `refresh` command.
void _refresh() {
  // Load session.json
  Map<String, dynamic> session;
  try {
    final content = File(_sessionFile).readAsStringSync();
    session = jsonDecode(content) as Map<String, dynamic>;
  } catch (_) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final token = session['token'];
  if (token is! String || token.isEmpty) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  // Create a PocketBase client and pre-load the auth store with the saved token
  final pb = PocketBase(_baseURL);
  pb.authStore.save(token, null);

  pb.collection(_collection).authRefresh().then((auth) {
    final newToken = auth.token;
    final recordId = auth.record.id;
    final exp = _getExp(newToken);

    // Persist the new token back to session.json if it changed
    if (newToken != token) {
      final newSession = {'token': newToken};
      File(_sessionFile).writeAsStringSync(jsonEncode(newSession));
    }

    // Print exactly two lines: record id, then exp epoch
    stdout.writeln(recordId);
    stdout.writeln(exp);
    exit(0);
  }).catchError((error) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  });
}
