import 'package:flutter/material.dart';
import 'package:userauth/pages/login.dart';
import 'context/auth.context.dart';
import 'package:userauth/pages/home.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: AuthSession.getSession(),
      builder: (BuildContext context, AsyncSnapshot<Map<String, dynamic>?> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          // If session check is in progress, show a loading indicator
          return const MaterialApp(
            debugShowCheckedModeBanner: false,
            home: Scaffold(body: Center(child: CircularProgressIndicator())),
          );
        } else {
          // If session check is complete
          final sessionData = snapshot.data;
          if (sessionData != null && sessionData['isActive']) {
            // If session is active, redirect to home page
            return MaterialApp(
              debugShowCheckedModeBanner: false,
              theme: ThemeData(fontFamily: 'Eudo'),
              home: HomePage(),
            );
          } else {
            // If session is not active, redirect to login page
            return MaterialApp(
              debugShowCheckedModeBanner: false,
              theme: ThemeData(fontFamily: 'Eudo'),
              home: const LoginPage(),
            );
          }
        }
      },
    );
  }
}
