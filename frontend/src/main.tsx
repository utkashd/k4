import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./assets/index.css";
import { StrictMode } from "react";
import { CookiesProvider } from "react-cookie";

ReactDOM.createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <CookiesProvider>
            <App />
        </CookiesProvider>
    </StrictMode>
);
