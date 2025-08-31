import js from "@eslint/js";

export default [
  { ignores: ["dist"] },
  {
    extends: [js.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        process: "readonly",
        Buffer: "readonly",
        __dirname: "readonly",
        __filename: "readonly",
        global: "readonly",
        module: "readonly",
        require: "readonly",
        exports: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        setImmediate: "readonly",
        clearImmediate: "readonly",
      },
    },
    rules: {
      "no-unused-vars": "warn",
      "no-console": "warn",
    },
  },
  {
    files: ["pages/**/*.{ts,tsx}", "components/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          "patterns": [
            "tests/*",
            "**/*.test",
            "**/*.spec",
            "__tests__/*"
          ]
        }
      ]
    }
  }
]; 