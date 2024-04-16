import User from "../models/users.js";
import nodemailer from "nodemailer";
import randomstring from "randomstring";

export const sendOTP = async (req, res) => {
  try {
    const { email } = req.body;
    // Generate OTP
    const OTP = randomstring.generate(5);

    const user = await User.findOne({ email });

    let isNewUser = false;

    if (user) {
      if (user.OTP == undefined) {
        user.OTP = OTP;
        await user.save();
      }
    } else {
      await User.create({ email, OTP });
      isNewUser = true;
    }

    // Send OTP via email
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: "pampermee.dev@gmail.com", // Gmail email address
        pass: "afqu crly mgbl pqvy", // Gmail password
      },
    });

    const mailOptions = {
      from: "pampermee.dev@gmail.com",
      to: email,
      subject: "OTP for verification",
      text: `Your OTP is: ${OTP}`,
    };

    transporter.sendMail(mailOptions, function (error, info) {
      if (error) {
        console.log(error);
        res.status(500).send("Failed to send OTP : ", error.message);
      } else {
        console.log("Email sent: " + info.response);
        res.status(200).send({ message: "OTP sent successfully", isNewUser });
      }
    });
  } catch (error) {
    console.error(error);
    res.status(500).send("Server error : ", error.message);
  }
};

// Function to verify OTP
export const verifyOTP = async (req, res) => {
  try {
    const { email, otp } = req.body;
    // Find the user by email
    const user = await User.findOne({ email });

    if (!user) {
      return res.status(404).send("User not found");
    }

    // Check if OTP matches
    if (user.OTP !== otp) {
      return res.status(400).send("Invalid OTP");
    } else {
      user.OTP = undefined;
      user.save();

      // If OTP matches, proceed to the next step
      res.status(200).send({ message: "OTP verified successfully", user });
    }
  } catch (error) {
    console.error(error);
    res.status(500).send("Server Error");
  }
};

// Function to update user information
export const updateUserInfo = async (req, res) => {
  try {
    const { email, name, mobile, pincode } = req.body;

    // Find the user by email
    let user = await User.findOne({ email });

    if (!user) {
      return res.status(404).send("User not found");
    }

    // Update user information
    user.name = name;
    user.mobile = mobile;
    user.pincode = pincode;
    user.OTP = undefined;

    // Save the updated user
    await user.save();
    console.log("Verified");

    res
      .status(200)
      .send({ message: "User information updated successfully", user });
  } catch (error) {
    console.error(error);
    res.status(500).send("Server Error");
  }
};

export const getUser = (req, res, next) => {
  console.log("fetching user");
  const userid = req.params.id;
  User.findById(userid)
    .then((user) => {
      if (!user) {
        const error = new Error("User not found");
        error.status = 404;
        throw error;
      }
      res.send(user);
    })
    .catch((err) => {
      next(err);
    });
};

export const createUser = async (req, res, next) => {
  const { email, name, mobile, pincode } = req.body;
  const user = await User.findOne({ email: email });
  if (user) {
    return res.json({ status: "failed", message: "User already exists" });
  } else {
    if (name !== "" && mobile !== "" && email !== "") {
      try {
        const newUser = new User({
          email,
          name,
          mobile,
          pincode,
        });
        await newUser
          .save()
          .then((user) => {
            return res.json({
              user: user,
              status: "success",
              message: "User registered",
            });
          })
          .catch((err) => {
            console.log(err);
            return res.json({ status: "failed", message: err.message });
          });
      } catch (error) {
        console.log(error);
        res.json({ status: "failed", message: "Unable to register" });
      }
    } else {
      return res.json({
        status: "failed",
        message: "All fields are mandatory!",
      });
    }
  }
};
