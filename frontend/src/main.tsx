import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./assets/index.css";
import { StrictMode } from "react";
import { CookiesProvider } from "react-cookie";
import * as Sentry from "@sentry/react";
import { isProductionEnvironment } from "./utils/utils.tsx";

if (isProductionEnvironment()) {
    if (import.meta.env.VITE_K4_FRONTEND_SENTRY_DSN) {
        Sentry.init({
            dsn: import.meta.env.VITE_K4_FRONTEND_SENTRY_DSN,
            integrations: [Sentry.replayIntegration()],
            // Session Replay
            replaysSessionSampleRate: 0.1, // This sets the sample rate at 10%. You may want to change it to 100% while in development and then sample at a lower rate in production.
            replaysOnErrorSampleRate: 1.0, // If you're not already sampling the entire session, change the sample rate to 100% when sampling sessions where errors occur.
        });
    }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <CookiesProvider>
            <App />
        </CookiesProvider>
    </StrictMode>
);
