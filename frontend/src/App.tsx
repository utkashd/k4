import { useEffect, useState } from "react";
import "./assets/App.css";
import { useCookies } from "react-cookie";
import { Setup, Login } from "./components/MainPanelContents";
import LeftSidePanelContents from "./components/LeftSidePanelContents";
import RightSidePanelContents from "./components/RightSidePanelContents";
import Server from "./model/Server";
import axios from "axios";
import {
    BrowserRouter as Router,
    Routes,
    Route,
    useNavigate,
} from "react-router-dom";
import { SetServer } from "./components/MainPanelContents";
import AdminPanel from "./components/AdminPanel";
import ChatBox from "./components/ChatBox";
import { ChatPreview } from "./model/Chat";
import { User } from "./model/User";

function App() {
    const [cookies, setCookie] = useCookies(["serverUrl", "currentUser"]);
    const [serverUrl, setServerUrl] = useState(
        cookies["serverUrl"] as URL | null
    );
    const [server, setServer] = useState(
        serverUrl
            ? {
                  url: serverUrl,
                  api: axios.create({
                      baseURL: serverUrl ? serverUrl.toString() : undefined,
                  }),
              }
            : (null as Server | null)
    );
    const [currentUser, setCurrentUser] = useState(
        cookies["currentUser"] as User | null
    );
    function setServerUrlAndCookie(serverUrl: URL | null) {
        let server: Server | null = null;
        if (serverUrl) {
            server = {
                url: serverUrl,
                api: axios.create({
                    baseURL: serverUrl ? serverUrl.toString() : undefined,
                }),
            };
            setServer(server);
        }
        setServer(server);
        setCookie("serverUrl", serverUrl);
        setServerUrl(serverUrl);
    }
    function setCurrentUserAndCookie(user: User | null) {
        setCookie("currentUser", user);
        setCurrentUser(user);
    }

    return (
        <Router>
            <Routes>
                <Route
                    path="/"
                    element={<Home server={server} currentUser={currentUser} />}
                />
                <Route
                    path="/chats"
                    element={
                        <Chats
                            currentUser={currentUser}
                            setCurrentUserAndCookie={setCurrentUserAndCookie}
                            server={server}
                            setServerUrlAndCookie={setServerUrlAndCookie}
                        />
                    }
                />
                <Route
                    path="/set_server"
                    element={
                        <SetServer
                            server={server}
                            setServerUrlAndCookie={setServerUrlAndCookie}
                        />
                    }
                />
                <Route
                    path="/setup"
                    element={
                        <Setup
                            server={server}
                            setCurrentUserAndCookie={setCurrentUserAndCookie}
                        />
                    }
                />
                <Route
                    path="/login"
                    element={
                        <Login
                            server={server}
                            currentUser={currentUser}
                            setServerUrlAndCookie={setServerUrlAndCookie}
                            setCurrentUserAndCookie={setCurrentUserAndCookie}
                        />
                    }
                />
                <Route
                    path="/admin_panel"
                    element={
                        <AdminPanel
                            currentUser={currentUser}
                            server={server}
                            setCurrentUserAndCookie={setCurrentUserAndCookie}
                        />
                    }
                />
                <Route path="/test_sentry" element={<SentryTest />} />
            </Routes>
        </Router>
    );
}

function SentryTest() {
    return (
        <>
            This page exists for testing Sentry.
            <br />
            <button
                onClick={(event) => {
                    event.preventDefault();
                    throw new Error("Intentional error from the frontend!");
                }}
            >
                Click me to raise an error that *should* get captured by Sentry
            </button>
        </>
    );
}

function Home({
    server,
    currentUser,
}: {
    server: Server | null;
    currentUser: User | null;
}) {
    const navigate = useNavigate();
    useEffect(() => {
        if (!server) {
            navigate("/set_server");
            return;
        }
        async function setupIfNecessary(server: Server) {
            const response = await server.api.get<boolean>(
                "/is_setup_required"
            );
            const isInitialSetupRequired = response.data;
            if (isInitialSetupRequired) {
                navigate("/setup");
                return;
            }
        }
        if (server) {
            setupIfNecessary(server);
        }
        if (!currentUser) {
            navigate("/login");
            return;
        } else if (currentUser.is_user_an_admin) {
            navigate("/admin_panel");
            return;
        }
        navigate("/chats");
        return;
    }, [server, currentUser, navigate]);
    return <>If you're seeing this message, something went wrong 🥲</>;
}

function Chats({
    currentUser,
    setCurrentUserAndCookie,
    server,
}: {
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    server: Server | null;
    setServerUrlAndCookie: (url: URL | null) => void;
}) {
    const [chatPreviews, setChatPreviews] = useState<ChatPreview[]>([]);
    const [selectedChatPreview, setSelectedChatPreview] = useState(
        null as ChatPreview | null
    ); // `selectedChatPreview === null` means "create a new chat"
    const navigate = useNavigate();
    useEffect(() => {
        if (!server || !currentUser || currentUser.is_user_an_admin) {
            navigate("/");
            return;
        }
    }, [navigate, server, currentUser]);

    if (!server || !currentUser || currentUser.is_user_an_admin) {
        return null;
    }

    return (
        <div className="app-container">
            <div className="left-side-panel">
                <LeftSidePanelContents
                    currentUser={currentUser}
                    setCurrentUserAndCookie={setCurrentUserAndCookie}
                    server={server}
                    selectedChatPreview={selectedChatPreview}
                    setSelectedChatPreview={setSelectedChatPreview}
                    chatPreviews={chatPreviews}
                    setChatPreviews={setChatPreviews}
                />
            </div>
            <div className="main-panel">
                <ChatBox
                    user={currentUser}
                    server={server}
                    selectedChatPreview={selectedChatPreview}
                    setSelectedChatPreview={setSelectedChatPreview}
                    setChatPreviews={setChatPreviews}
                />
            </div>
            <div className="right-side-panel">
                <RightSidePanelContents
                    currentUser={currentUser}
                    server={server}
                    setCurrentUserAndCookie={setCurrentUserAndCookie}
                />
            </div>
        </div>
    );
}

export default App;
