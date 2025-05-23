module.exports = {
    env: { browser: true },
    extends: [
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended",
        "plugin:react-hooks/recommended",
    ],
    ignorePatterns: [
        "dist",
        "build",
        ".eslintrc.cjs",
        "package.json",
        "package-lock.json",
        "*.md",
        "public/",
    ],
    parser: "@typescript-eslint/parser",
    plugins: ["react-refresh"],
    rules: {
        "react-refresh/only-export-components": [
            "warn",
            { allowConstantExport: true },
        ],
    },
};
