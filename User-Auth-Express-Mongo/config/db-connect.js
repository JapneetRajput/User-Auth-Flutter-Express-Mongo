import mongoose from "mongoose";

const connectDB = async () => {
  try {
    const DB_OPTIONS = {
      useNewUrlParser: true,
    };
    await mongoose.connect(
      "mongodb+srv://japneet:japneetquiz@quiz.9h5qyr9.mongodb.net/",
      DB_OPTIONS
    );
    console.log("Connected to Database");
  } catch (error) {
    console.log(error);
  }
};

export default connectDB;
