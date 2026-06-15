import 'dart:convert';
import 'dart:io';
import 'package:pocketbase/pocketbase.dart';

void main(List<String> args) async {
  if (args.isEmpty) {
    printUsageAndExit();
  }

  final command = args[0];
  if (command == 'login') {
    if (args.length < 3) {
      stderr.writeln('Usage: login <email> <password>');
      exit(1);
    }
    final email = args[1];
    final password = args[2];
    await handleLogin(email, password);
  } else if (command == 'refresh') {
    await handleRefresh();
  } else {
    printUsageAndExit();
  }
}

void printUsageAndExit() {
  stderr.writeln('Usage:');
  stderr.writeln('  dart run bin/app.dart login <email> <password>');
  stderr.writeln('  dart run bin/app.dart refresh');
  exit(1);
}

Future<void> handleLogin(String email, String password) async {
  final pb = PocketBase('http://127.0.0.1:8090');
  try {
    final authData = await pb.collection('users').authWithPassword(email, password);
    final token = authData.token;
    if (token.isEmpty) {
      stderr.writeln('Error: Empty token received');
      exit(1);
    }
    
    final sessionFile = File('session.json');
    await sessionFile.writeAsString(jsonEncode({'token': token}), flush: true);
    exit(0);
  } catch (e) {
    stderr.writeln('Login failed: $e');
    exit(1);
  }
}

Future<void> handleRefresh() async {
  final sessionFile = File('session.json');
  if (!await sessionFile.exists()) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  String content;
  try {
    content = await sessionFile.readAsString();
  } catch (e) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  Map<String, dynamic> sessionData;
  try {
    final parsed = jsonDecode(content);
    if (parsed is! Map<String, dynamic>) {
      stderr.writeln('INVALID_SESSION');
      exit(1);
    }
    sessionData = parsed;
  } catch (e) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final token = sessionData['token'];
  if (token is! String || token.isEmpty) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  // Validate and decode the JWT to check format/validity before calling API
  try {
    decodeJwt(token);
  } catch (e) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final pb = PocketBase('http://127.0.0.1:8090');
  pb.authStore.save(token, null);

  RecordAuth refreshed;
  try {
    refreshed = await pb.collection('users').authRefresh();
  } on ClientException catch (_) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  } catch (_) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final newToken = refreshed.token;
  final userId = refreshed.record.id;

  // Persist the new token back to session.json if it changed
  if (newToken != token) {
    try {
      await sessionFile.writeAsString(jsonEncode({'token': newToken}), flush: true);
    } catch (_) {
      // Ignore write errors to avoid crashing if read-only, though usually we can write
    }
  }

  // Decode new token to get the exp claim
  Map<String, dynamic> newJwtPayload;
  try {
    newJwtPayload = decodeJwt(newToken);
  } catch (_) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final exp = newJwtPayload['exp'];
  if (exp is! num) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  // Stdout prints exactly two lines and nothing else
  print(userId);
  print(exp.toInt());
  exit(0);
}

Map<String, dynamic> decodeJwt(String token) {
  final parts = token.split('.');
  if (parts.length != 3) {
    throw Exception('Invalid JWT format');
  }
  final payload = parts[1];
  final normalized = base64Url.normalize(payload);
  final decoded = utf8.decode(base64Url.decode(normalized));
  return jsonDecode(decoded) as Map<String, dynamic>;
}
