import { sentryVitePlugin } from "@sentry/vite-plugin";
import { defineConfig, UserConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import dotenv from "dotenv";

let config: UserConfig;

// TODO read these from environment variables instead
dotenv.config({ path: ".env.sentry-build-plugin" });

const org = process.env.SENTRY_ORG ?? "";
const project = process.env.SENTRY_PROJECT ?? "";

if (org && project && process.env.K4_ENVIRONMENT === "production") {
    config = defineConfig({
        plugins: [
            react(),
            sentryVitePlugin({
                org: org,
                project: project,
            }),
        ],
        build: {
            sourcemap: true,
        },
    });
} else {
    config = defineConfig({ plugins: [react()] });
}

export default config;
