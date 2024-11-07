import { useState } from "react";
import "./App.css";
import { useCookies } from "react-cookie";
import MainPanelContents from "./components/MainPanelContents";

function App() {
    const [cookies, setCookie, _removeCookie] = useCookies([
        "serverUrl",
        "currentUser",
    ]);
    const [serverUrl, setServerUrl] = useState(
        cookies["serverUrl"] as URL | null
    );
    const [currentUser, setCurrentUser] = useState(
        cookies["currentUser"] as User | null
    );

    function setServerUrlAndCookie(url: URL | null) {
        setCookie("serverUrl", url);
        setServerUrl(url);
    }

    function setCurrentUserAndCookie(user: User | null) {
        setCookie("currentUser", user);
        setCurrentUser(user);
    }

    return (
        <>
            <div className="app-container">
                <div className="left-side-panel">
                    <img src="./gh.png" className="logo-test" alt="logo"></img>
                </div>
                <div className="main-panel">
                    <MainPanelContents
                        serverUrl={serverUrl}
                        setServerUrlAndCookie={setServerUrlAndCookie}
                        currentUser={currentUser}
                        setCurrentUserAndCookie={setCurrentUserAndCookie}
                    />
                </div>
                <div className="right-side-panel">right side panel here</div>
            </div>
        </>
    );
}

export default App;
