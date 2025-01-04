import { useState } from "react";
import "./App.css";
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
    const [selectedChat, setSelectedChat] = useState(
        null as ChatListItem | null
    );
    const [chats, setChats] = useState([] as ChatListItem[]);

    return (
        <>
            <div className="app-container">
                <div className="left-side-panel">
                    <LeftSidePanelContents
                        user={currentUser}
                        serverUrl={serverUrl}
                        selectedChat={selectedChat}
                        setSelectedChat={setSelectedChat}
                        chats={chats}
                        setChats={setChats}
                    />
                </div>
                <div className="main-panel">
                    <MainPanelContents
                        serverUrl={serverUrl}
                        setServerUrlAndCookie={setServerUrlAndCookie}
                        currentUser={currentUser}
                        setCurrentUserAndCookie={setCurrentUserAndCookie}
                        selectedChat={selectedChat}
                        setSelectedChat={setSelectedChat}
                        setChats={setChats}
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
