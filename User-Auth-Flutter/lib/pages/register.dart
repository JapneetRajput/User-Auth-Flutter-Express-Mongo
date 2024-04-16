import 'package:flutter/material.dart';
import 'package:userauth/context/auth.context.dart';
import 'package:userauth/pages/home.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:userauth/services/auth.services.dart';

class RegisterPage extends StatelessWidget {
  final String email;

  const RegisterPage({super.key, required this.email});

  Future<void> _updateUserInfo(BuildContext context, String name, String pincode, String mobile) async {
    try {
      final response = await ApiService.updateUserInfo(email, name, pincode, mobile);
      await AuthSession.setSession(
        userId: response['user']['_id'],
        userEmail: response['user']['email'],
        expirationTime: DateTime.now().add(Duration(days: 30)),
      );
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => HomePage(),
        ),
      );
    } catch (e) {
      // Handle error response from server
      Fluttertoast.showToast(
        msg: 'Failed to update user info.',
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
    final TextEditingController _nameController = TextEditingController();
    final TextEditingController _pincodeController = TextEditingController();
    final TextEditingController _mobileController = TextEditingController();

    return Scaffold(
      appBar: AppBar(),
      body: SingleChildScrollView(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Logo
            SvgPicture.asset(
              'assets/images/strips.svg',
              width: MediaQuery.of(context).size.width,
              fit: BoxFit.cover,
            ),
            Padding(
              padding: const EdgeInsets.only(left: 30.0, right: 30.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 50.0),
                  // Login Title
                  const Text(
                    'Sign Up',
                    style: TextStyle(
                      fontFamily: 'Eudo',
                      fontSize: 30.0,
                      fontWeight: FontWeight.bold,
                    ),
                    textAlign: TextAlign.left,
                  ),
                  const SizedBox(height: 20.0),
                  // Reusable Input Field
                  CustomTextField(
                    label: 'Full Name',
                    controller: _nameController,
                  ),
                  const SizedBox(height: 15.0),
                  // Reusable Input Field
                  CustomTextField(
                    label: 'Phone Number',
                    controller: _mobileController,
                  ),
                  const SizedBox(height: 15.0),
                  // Reusable Input Field
                  CustomTextField(
                    label: 'Pincode',
                    controller: _pincodeController,
                  ),
                  const SizedBox(height: 50.0),
                  // Login Button
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () {
                            _updateUserInfo(context, _nameController.text, _pincodeController.text, _mobileController.text);
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
                          child: const Text('Register'),
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

class CustomTextField extends StatelessWidget {
  final String label;
  final TextEditingController controller;

  const CustomTextField({Key? key, required this.label, required this.controller}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontFamily: 'Eudo',
            fontWeight: FontWeight.w500,
            fontSize: 12.0,
            color: Color.fromARGB(255, 109, 109, 109),
          ),
          textAlign: TextAlign.left,
        ),
        const SizedBox(height: 5.0),
        TextFormField(
          controller:controller,
          decoration: InputDecoration(
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8.0),
              borderSide: BorderSide.none,
            ),
            filled: true,
            fillColor: const Color.fromARGB(255, 239, 239, 239),
          ),
          style: const TextStyle(
            height: 0.7,
            fontFamily: 'Eudo',
            fontSize: 14,
          ),
        ),
      ],
    );
  }
}
