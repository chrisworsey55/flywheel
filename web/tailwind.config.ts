import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07090d",
        panel: "#10141b",
        line: "#26313f",
        steel: "#9aa7b6",
        signal: "#47d18c",
        warn: "#ffcc66",
        bad: "#ff5f70"
      }
    }
  },
  plugins: []
};

export default config;

