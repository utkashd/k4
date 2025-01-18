import { useState } from "react";
import "./assets/App.css";
import { useCookies } from "react-cookie";
import MainPanelContents from "./components/MainPanelContents";
import LeftSidePanelContents from "./components/LeftSidePanelContents";
import RightSidePanelContents from "./components/RightSidePanelContents";

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
    const [selectedChatPreview, setSelectedChatPreview] = useState(
        null as ChatPreview | null
    ); // `selectedChat === null` means "create a new chat"
    const [chatPreviews, setChatPreviews] = useState([] as ChatPreview[]);

    return (
        <>
            <div className="app-container">
                <div className="left-side-panel">
                    <LeftSidePanelContents
                        currentUser={currentUser}
                        setCurrentUserAndCookie={setCurrentUserAndCookie}
                        serverUrl={serverUrl}
                        selectedChatPreview={selectedChatPreview}
                        setSelectedChatPreview={setSelectedChatPreview}
                        chatPreviews={chatPreviews}
                        setChatPreviews={setChatPreviews}
                    />
                </div>
                <div className="main-panel">
                    <MainPanelContents
                        currentUser={currentUser}
                        serverUrl={serverUrl}
                        setServerUrlAndCookie={setServerUrlAndCookie}
                        setCurrentUserAndCookie={setCurrentUserAndCookie}
                        selectedChatPreview={selectedChatPreview}
                        setSelectedChatPreview={setSelectedChatPreview}
                        setChatPreviews={setChatPreviews}
                    />
                </div>
                <div className="right-side-panel">
                    <RightSidePanelContents
                        currentUser={currentUser}
                        serverUrl={serverUrl}
                        setCurrentUserAndCookie={setCurrentUserAndCookie}
                    />
                </div>
            </div>
        </>
    );
}

export default App;
