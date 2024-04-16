import mongoose from "mongoose";

const connectDB = async () => {
  try {
    const DB_OPTIONS = {
      useNewUrlParser: true,
    };
    await mongoose.connect(
      "mongodb+srv://yashvidhar:2XANDDqacLjGIGYM@cluster0.lpxr8zy.mongodb.net/",
      DB_OPTIONS
    );
    console.log("Connected to Database");
  } catch (error) {
    console.log(error);
  }
};

export default connectDB;