import 'package:flutter/material.dart';
import 'package:userauth/pages/verify.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:userauth/services/auth.services.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  Future<void> _sendOTP(BuildContext context, String email) async {
    try {
      print(email);
      final responseData = await ApiService.sendOTP(email);
      final isNewUser = responseData['isNewUser'] ?? false;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => VerifyPage(email:email,isNewUser: isNewUser),
        ),
      );
    } catch (e) {
      // Handle error response from server
      Fluttertoast.showToast(
        msg: 'Failed to send OTP. ${e.toString()}',
        toastLength: Toast.LENGTH_SHORT,
        gravity: ToastGravity.BOTTOM,
        backgroundColor: Colors.red,
        textColor: Colors.white,
        fontSize: 16.0,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final TextEditingController _emailController = TextEditingController();

    return Scaffold(
      body: SingleChildScrollView(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 80.0),
            Padding(padding: const EdgeInsets.only(left: 30.0, right: 30.0), 
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 100.0),

                // Login Title
                const Text(
                  'Sign In',
                  style: TextStyle(
                    fontFamily: 'Eudo',
                    fontSize: 30.0,
                  fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.left,
                ),
                const SizedBox(height: 30.0),

                // Email Input
                const Text(
                  'Email Address',
                  style: TextStyle(
                    fontFamily: 'Eudo',
                    fontWeight: FontWeight.w500,
                    fontSize: 12.0,
                    color: Color.fromARGB(255, 109, 109, 109),
                  ),
                  textAlign: TextAlign.left,
                ),
                const SizedBox(height: 5.0),
                TextFormField(
                  controller: _emailController,
                  decoration: InputDecoration(
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8.0),
                      borderSide: BorderSide.none,
                    ),
                    filled: true,
                    fillColor: const Color.fromARGB(255, 239, 239, 239),
                  ),
                  style: const TextStyle(
                    height: 0.8,
                    fontFamily: 'Eudo',
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 30.0),
                // Login Button
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () {
                          _sendOTP(context, _emailController.text);
                        },
                        style: ElevatedButton.styleFrom(
                          shadowColor: Colors.transparent,
                          backgroundColor: const Color.fromARGB(255, 227, 121, 216),
                          textStyle: const TextStyle(
                            fontSize: 16.0,
                            fontWeight: FontWeight.bold,
                          ),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12.0),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6.0),
                          ),
                        ),
                        child: const Text('Login'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            ),
          ],
        ),
      ),
    );
  }
}