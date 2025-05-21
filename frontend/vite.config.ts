import { defineConfig, UserConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

const config: UserConfig = defineConfig({ plugins: [react()] });

export default config;
