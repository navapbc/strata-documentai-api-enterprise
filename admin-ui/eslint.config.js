import noUnsanitized from "eslint-plugin-no-unsanitized";

export default [
  {
    files: ["js/**/*.js"],
    plugins: {
      "no-unsanitized": noUnsanitized,
    },
    rules: {
      "no-unsanitized/method": "error",
      "no-unsanitized/property": "error",
    },
  },
];
