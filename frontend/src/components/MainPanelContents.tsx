import { useEffect, useState } from "react";
import "./SetServerForm.css";
import axios from "axios";
import ChatBox from "./ChatBox";
import AdminPanel from "./AdminPanel";

function SetServerForm({
    setServerUrlAndCookie,
}: {
    setServerUrlAndCookie: (url: URL | null) => void;
}) {
    // setServerUrlAndCookie(new URL("http://localhost:8000"));
    const [serverUrlInput, setServerUrlInput] = useState("http://");

    const submitSetServerUrl = async (
        event: React.MouseEvent<HTMLElement, MouseEvent>
    ) => {
        event.preventDefault();
        try {
            const serverUrl = new URL(serverUrlInput);
            setServerUrlAndCookie(serverUrl);
        } catch (error) {
            alert(`"${serverUrlInput}" is not a valid URL.`);
            setServerUrlInput("http://");
        }
    };

    return (
        <>
            <div className="setServerUrl">
                <p>
                    No server URL detected. Please set your server URL. This
                    will be saved to your device.
                </p>
                <div className="input">
                    <input
                        type="text"
                        className="serverUrlInput"
                        placeholder="http://"
                        value={serverUrlInput}
                        onChange={(event) => {
                            setServerUrlInput(event.target.value);
                        }}
                    />
                </div>
                <br></br>
                <div className="submitSetServerUrl">
                    <button
                        onClick={(event) => {
                            submitSetServerUrl(event);
                        }}
                    >
                        Set Server URL
                    </button>
                </div>
            </div>
        </>
    );
}

const CreateFirstAdminForm = ({ serverUrl }: { serverUrl: URL }) => {
    const [firstAdminUsernameInput, setFirstAdminUsernameInput] = useState("");
    const [firstAdminPasswordInput, setFirstAdminPasswordInput] = useState("");

    const submitLogin = async () => {
        try {
            await axios.post(new URL("/first_admin", serverUrl).toString(), {
                desired_user_email: firstAdminUsernameInput,
                desired_user_password: firstAdminPasswordInput,
            });
        } catch (error) {
            console.log(error);
            console.log("TODO deal w dis unhandled error 78465132");
        }
    };
    return (
        <>
            Create the first admin account. After this, an admin account will be
            required to create any users.
            <div className="inputs">
                <input
                    type="text"
                    placeholder="username"
                    value={firstAdminUsernameInput}
                    onChange={(event) => {
                        setFirstAdminUsernameInput(event.target.value);
                    }}
                ></input>
                <br />
                <input
                    type="password"
                    placeholder="password"
                    value={firstAdminPasswordInput}
                    onChange={(event) => {
                        setFirstAdminPasswordInput(event.target.value);
                    }}
                ></input>
            </div>
            <br />
            <div className="submitLogin">
                <button
                    onClick={(_event) => {
                        submitLogin();
                    }}
                >
                    Create Admin
                </button>
            </div>
        </>
    );
};

const LoginForm = ({
    serverUrl,
    setServerUrlAndCookie,
    setCurrentUserAndCookie,
}: {
    serverUrl: URL;
    setServerUrlAndCookie: (url: URL | null) => void;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    const clearServerUrl = () => {
        setServerUrlAndCookie(null);
    };
    const [usernameInput, setUsernameInput] = useState("");
    const [passwordInput, setPasswordInput] = useState("");

    const submitLogin = async () => {
        try {
            await axios.post(
                new URL("/token", serverUrl).toString(),
                new URLSearchParams({
                    username: usernameInput,
                    password: passwordInput,
                }),
                { withCredentials: true }
            );
            const currentUserRequestResponse = await axios.get(
                new URL("/user/me", serverUrl).toString(),
                { withCredentials: true }
            );
            setCurrentUserAndCookie(currentUserRequestResponse.data);
        } catch (error) {
            console.log(error);
            console.log("TODO deal w dis unhandled error 874512");
        }
    };

    return (
        <>
            <div className="inputs">
                <input
                    type="text"
                    placeholder="username"
                    value={usernameInput}
                    onChange={(event) => {
                        setUsernameInput(event.target.value);
                    }}
                ></input>
                <br />
                <input
                    type="password"
                    placeholder="password"
                    value={passwordInput}
                    onChange={(event) => {
                        setPasswordInput(event.target.value);
                    }}
                ></input>
            </div>
            <br />
            <div className="submitLogin">
                <button
                    onClick={(_event) => {
                        submitLogin();
                    }}
                >
                    Login to {serverUrl.toString()}
                </button>
            </div>
            <p>
                <a href="" onClick={clearServerUrl}>
                    Change server
                </a>
            </p>
        </>
    );
};

const MainPanelContents = ({
    serverUrl,
    setServerUrlAndCookie,
    currentUser,
    setCurrentUserAndCookie,
    selectedChat,
    setSelectedChat,
    setChats,
}: {
    serverUrl: URL | null;
    setServerUrlAndCookie: (url: URL | null) => void;
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    selectedChat: ChatListItem | null;
    setSelectedChat: React.Dispatch<React.SetStateAction<ChatListItem | null>>;
    setChats: React.Dispatch<React.SetStateAction<ChatListItem[]>>;
}) => {
    const [isInitialSetupRequired, setIsInitialSetupRequired] = useState(true);

    useEffect(() => {
        async function learnWhetherInitialSetupIsRequired(serverUrl: URL) {
            const response = await axios.get(
                new URL("/is_setup_required", serverUrl).toString()
            );
            setIsInitialSetupRequired(response.data === true);
        }
        if (serverUrl) {
            learnWhetherInitialSetupIsRequired(serverUrl);
        }
    }, [serverUrl]);

    if (!serverUrl) {
        return <SetServerForm setServerUrlAndCookie={setServerUrlAndCookie} />;
    }

    if (isInitialSetupRequired) {
        return <CreateFirstAdminForm serverUrl={serverUrl} />;
    }

    if (!currentUser) {
        return (
            <LoginForm
                serverUrl={serverUrl}
                setServerUrlAndCookie={setServerUrlAndCookie}
                setCurrentUserAndCookie={setCurrentUserAndCookie}
            />
        );
    }

    if (currentUser.is_user_an_admin) {
        return (
            <AdminPanel currentAdminUser={currentUser} serverUrl={serverUrl} />
        );
    }

    const chatEndpointBaseUrl = new URL(serverUrl);
    chatEndpointBaseUrl.protocol = chatEndpointBaseUrl.protocol.replace(
        "http",
        "ws"
    );
    return (
        <ChatBox
            user={currentUser}
            serverUrl={serverUrl}
            selectedChat={selectedChat}
            setSelectedChat={setSelectedChat}
            setChats={setChats}
        />
    );
};

export default MainPanelContents;
