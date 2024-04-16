import express from "express";
const router = express.Router();

// Import the controller for handling requests
import {
  createUser,
  getUser,
  sendOTP,
  updateUserInfo,
  verifyOTP,
} from "../controller/users.js";

router.post("/create", createUser);
router.post("/send-otp", sendOTP);
router.post("/verify-otp", verifyOTP);
router.post("/update-user-info", updateUserInfo);
router.get("/:id", getUser);

export default router;
