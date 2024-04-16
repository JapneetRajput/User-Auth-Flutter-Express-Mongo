import express from "express";
import cors from "cors";
import connectDB from "./config/db-connect.js";

const app = express();
connectDB();

app.use(cors());
app.use(express.json());

app.get("/test", (req, res) => {
  return res.json(`Hello! Testing the HomeService Server API`);
});

import usersRoutes from "./routes/users.js";
app.use("/users", usersRoutes);

const PORT = 3001;
app.listen(PORT, () => {
  console.log("Server listening on port " + PORT + "...");
});
