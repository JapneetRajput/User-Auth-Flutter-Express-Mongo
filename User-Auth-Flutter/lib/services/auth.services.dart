import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:userauth/constants/auth.constants.dart';

class ApiService {
  static Future<Map<String, dynamic>> sendOTP(String email) async {
    const url = ApiConstants.sendOTP;
    final response = await http.post(Uri.parse(url),
        headers: <String, String>{
          'Content-Type': 'application/json; charset=UTF-8',
        },
        body: jsonEncode(<String, String>{
          'email': email,
          }
        )
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to send OTP');
    }
  }

  static Future<Map<String, dynamic>> verifyOTP(String email, String otp) async {
    print("Inside verify otp service");
    const url = ApiConstants.verifyOTP;
    final response = await http.post(
      Uri.parse(url),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{
        'email': email,
        'otp':otp,
      })
    );
    print("Response ");
    print(response.statusCode);

    if (response.statusCode == 200) {
      // If OTP verification is successful, return the response body
      return json.decode(response.body);
    } else {
      print("Error");
      print(response.body);
      // If OTP verification fails, throw an error
      throw Exception('Failed to verify OTP');
    }
  }


  static Future<Map<String, dynamic>> updateUserInfo(String email, String name, String pincode, String mobile) async {
    const url = ApiConstants.updateUserInfo;
    final response = await http.post(Uri.parse(url),
      headers: <String, String>{
        'Content-Type': 'application/json; charset=UTF-8',
      },
      body: jsonEncode(<String, String>{
        'email': email,
        'name': name,
        'pincode': pincode,
        'mobile': mobile,
      })
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to update user info!');
    }
  }
}
