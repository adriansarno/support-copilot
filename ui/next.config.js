const path = require("path");

// Load root .env so UI picks up API_KEY as NEXT_PUBLIC_API_KEY (and other vars)
const rootEnv = path.resolve(__dirname, "../.env");
require("dotenv").config({ path: rootEnv });
if (process.env.API_KEY && !process.env.NEXT_PUBLIC_API_KEY) {
  process.env.NEXT_PUBLIC_API_KEY = process.env.API_KEY;
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
};

module.exports = nextConfig;
