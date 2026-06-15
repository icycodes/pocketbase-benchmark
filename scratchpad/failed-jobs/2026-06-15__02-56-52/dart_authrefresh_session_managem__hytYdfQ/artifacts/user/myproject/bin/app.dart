import 'dart:convert';
import 'dart:io';
import 'package:pocketbase/pocketbase.dart';

void main(List<String> args) async {
  if (args.isEmpty) return;

  final pb = PocketBase('http://127.0.0.1:8090');
  final command = args[0];

  final sessionFile = File('session.json');

  if (command == 'login') {
    if (args.length < 3) return;
    final email = args[1];
    final password = args[2];

    try {
      final authData = await pb.collection('users').authWithPassword(email, password);
      final token = pb.authStore.token;
      await sessionFile.writeAsString(jsonEncode({'token': token}));
      exit(0);
    } catch (e) {
      exit(1);
    }
  } else if (command == 'refresh') {
    if (!sessionFile.existsSync()) {
      stderr.writeln('INVALID_SESSION');
      exit(1);
    }

    String token;
    try {
      final content = await sessionFile.readAsString();
      final data = jsonDecode(content);
      if (data is! Map || !data.containsKey('token') || data['token'] == null || data['token'].toString().isEmpty) {
        stderr.writeln('INVALID_SESSION');
        exit(1);
      }
      token = data['token'];
    } catch (e) {
      stderr.writeln('INVALID_SESSION');
      exit(1);
    }

    try {
      pb.authStore.save(token, null);
      final authData = await pb.collection('users').authRefresh();
      
      final newToken = pb.authStore.token;
      await sessionFile.writeAsString(jsonEncode({'token': newToken}));
      
      final userId = authData.record?.id ?? '';
      
      // decode token to get exp
      final parts = newToken.split('.');
      if (parts.length != 3) throw Exception('Invalid token');
      
      var payload = parts[1];
      while (payload.length % 4 != 0) {
        payload += '=';
      }
      final decoded = utf8.decode(base64Url.decode(payload));
      final payloadMap = jsonDecode(decoded);
      final exp = payloadMap['exp'];
      
      print(userId);
      print(exp);
      exit(0);
    } catch (e) {
      exit(1);
    }
  }
}
