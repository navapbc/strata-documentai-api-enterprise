import noUnsanitized from "eslint-plugin-no-unsanitized";

export default [
  {
    files: ["src/**/*.js", "tests/**/*.js", "e2e/**/*.js"],
    plugins: {
      "no-unsanitized": noUnsanitized,
    },
    rules: {
      "no-unsanitized/method": "error",
      "no-unsanitized/property": "error",
      "no-unused-vars": ["error", {
        varsIgnorePattern: "^_",
        argsIgnorePattern: "^_",
        caughtErrorsIgnorePattern: "^_",
      }],
    },
  },
];
