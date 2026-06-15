import 'dart:convert';
import 'dart:io';

import 'package:pocketbase/pocketbase.dart';

const sessionFile = 'session.json';

void main(List<String> args) async {
  if (args.isEmpty) {
    stderr.writeln('Usage: dart run bin/app.dart <login|refresh> [args]');
    exit(1);
  }

  final command = args[0];

  switch (command) {
    case 'login':
      if (args.length != 3) {
        stderr.writeln('Usage: dart run bin/app.dart login <email> <password>');
        exit(1);
      }
      await login(args[1], args[2]);
      break;
    case 'refresh':
      await refresh();
      break;
    default:
      stderr.writeln('Unknown command: $command');
      exit(1);
  }
}

Future<void> login(String email, String password) async {
  final pb = PocketBase('http://127.0.0.1:8090');

  final auth = await pb.collection('users').authWithPassword(email, password);

  final sessionData = {
    'token': auth.token,
    'record': auth.record.toJson(),
  };

  File(sessionFile).writeAsStringSync(jsonEncode(sessionData));

  exit(0);
}

Future<void> refresh() async {
  final file = File(sessionFile);

  if (!file.existsSync()) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  String rawJson;
  try {
    rawJson = file.readAsStringSync();
  } catch (e) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  Map<String, dynamic> sessionData;
  try {
    final decoded = jsonDecode(rawJson);
    if (decoded is! Map<String, dynamic>) {
      stderr.writeln('INVALID_SESSION');
      exit(1);
    }
    sessionData = decoded;
  } catch (e) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final token = sessionData['token'];
  if (token is! String || token.isEmpty) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final recordData = sessionData['record'];
  if (recordData is! Map<String, dynamic>) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final pb = PocketBase('http://127.0.0.1:8090');
  pb.authStore.save(token, RecordModel.fromJson(recordData));

  await pb.collection('users').authRefresh();

  final newToken = pb.authStore.token;
  final newRecord = pb.authStore.record;

  // Persist session if the token changed
  if (newToken != token && newRecord != null) {
    final newSessionData = {
      'token': newToken,
      'record': newRecord.toJson(),
    };
    file.writeAsStringSync(jsonEncode(newSessionData));
  }

  // Decode JWT to get exp claim
  final parts = newToken.split('.');
  if (parts.length != 3) {
    stderr.writeln('INVALID_SESSION');
    exit(1);
  }

  final payloadStr = base64Url.normalize(parts[1]);
  final payloadBytes = base64Url.decode(payloadStr);
  final payload =
      jsonDecode(utf8.decode(payloadBytes)) as Map<String, dynamic>;

  final exp = payload['exp'];
  final recordId = newRecord?.id ?? '';

  print(recordId);
  print(exp is int ? exp : int.parse(exp.toString()));

  exit(0);
}