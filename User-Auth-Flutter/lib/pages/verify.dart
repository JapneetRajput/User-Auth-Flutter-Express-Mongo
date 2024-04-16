import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:userauth/pages/home.dart';
import 'package:userauth/pages/register.dart';
import 'package:userauth/services/auth.services.dart';
import 'package:userauth/context/auth.context.dart';

class VerifyPage extends StatelessWidget {
  final bool isNewUser;
  final String email;

  VerifyPage({Key? key, required this.isNewUser, required this.email})
      : super(key: key);
  final List<String> digitInputs = List.filled(5, '');

  Future<void> _verifyOTP(BuildContext context) async {
    try {
      final response = await ApiService.verifyOTP(email, digitInputs.join());
      // Handle successful OTP verification
      if (isNewUser) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => RegisterPage(email: email),
          ),
        );
      } else {
        await AuthSession.setSession(
          userId: response['user']['_id'],
          userEmail: response['user']['email'],
          expirationTime: DateTime.now().add(const Duration(days: 30)),
        );
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => HomePage(),
          ),
        );
      }
    } catch (e) {
      print(e.toString());
      Fluttertoast.showToast(
        msg: 'Failed to verify OTP.${e.toString()}',
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
    print(isNewUser);
    return Scaffold(
      appBar: AppBar(),
      body: SingleChildScrollView(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Padding(
                padding:
                    EdgeInsets.only(left: 30, right: 30, bottom: 10, top: 30),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Verification Code',
                      style: TextStyle(
                        fontSize: 26,
                        fontFamily: 'Eudo',
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'We just sent you a code to verify your email. Check your inbox and enter the code below.',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey,
                        fontFamily: 'Eudo',
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 40),
              Padding(
                padding: const EdgeInsets.only(left: 30, right: 30),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal, // Add this
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      buildDigitTextField(0),
                      buildDigitTextField(1),
                      buildDigitTextField(2),
                      buildDigitTextField(3),
                      buildDigitTextField(4),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 40),

              // Verify Button
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(
                          left: 30, right: 30, bottom: 10),
                      child: ElevatedButton(
                        onPressed: () {
                          _verifyOTP(context);
                        },
                        style: ElevatedButton.styleFrom(
                          shadowColor: Colors.transparent,
                          backgroundColor:
                              const Color.fromARGB(255, 227, 121, 216),
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
                        child: const Text('Verify'),
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 20),
              const CountdownTimer(),
            ],
          ),
        ),
      ),
    );
  }

  Widget buildDigitTextField(int index) {
    final focusNode = FocusNode();

    return Container(
      width: 50,
      height: 65,
      margin: const EdgeInsets.symmetric(horizontal: 5),
      decoration: BoxDecoration(
        color: const Color.fromARGB(255, 239, 239, 239),
        border: Border.all(
          color: const Color.fromARGB(0, 158, 158, 158),
          width: 1,
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      child: TextField(
        keyboardType: TextInputType.text,
        maxLength: 1,
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 20),
        decoration: const InputDecoration(
          counterText: '',
          border: InputBorder.none,
        ),
        onChanged: (value) {
          if (value.isNotEmpty) {
            digitInputs[index] = value; // Store input in the list
            focusNode.nextFocus();
          } else {
            focusNode.previousFocus();
          }
        },
        focusNode: focusNode,
      ),
    );
  }
}

class CountdownTimer extends StatefulWidget {
  const CountdownTimer({super.key});

  @override
  _CountdownTimerState createState() => _CountdownTimerState();
}

class _CountdownTimerState extends State<CountdownTimer> {
  int _secondsRemaining = 30;

  @override
  void initState() {
    super.initState();
    startTimer();
  }

  void startTimer() {
    Future.delayed(const Duration(seconds: 1), () {
      setState(() {
        _secondsRemaining--;
      });
      if (_secondsRemaining > 0) {
        startTimer();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      'Re-send code in 0:$_secondsRemaining',
      style: const TextStyle(
        color: Colors.grey,
      ),
    );
  }
}
