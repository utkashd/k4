import { useEffect, useState } from "react";
import "../assets/SetServerForm.css";
import ChatBox from "./ChatBox";
import AdminPanel from "./AdminPanel";
import Server from "../model/Server";

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
            setServerUrlAndCookie(new URL(serverUrlInput));
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

const CreateFirstAdminForm = ({ server }: { server: Server }) => {
    const [firstAdminUsernameInput, setFirstAdminUsernameInput] = useState("");
    const [firstAdminPasswordInput, setFirstAdminPasswordInput] = useState("");

    const submitLogin = async () => {
        try {
            await server.api.post("/first_admin", {
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
    server,
    setServerUrlAndCookie,
    setCurrentUserAndCookie,
}: {
    server: Server;
    setServerUrlAndCookie: (url: URL | null) => void;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    const clearServerUrl = () => {
        setServerUrlAndCookie(null);
    };
    const [usernameInput, setUsernameInput] = useState("");
    const [passwordInput, setPasswordInput] = useState("");

    const submitLogin = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        e.stopPropagation();
        try {
            await server.api.post(
                "/token",
                new URLSearchParams({
                    username: usernameInput,
                    password: passwordInput,
                }),
                { withCredentials: true } // Is this necessary?
            );
            const currentUserRequestResponse = await server.api.get<User>(
                "/user/me",
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
            <form onSubmit={submitLogin}>
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
                    <button type="submit">
                        Login to {server.url!.toString()}
                    </button>
                </div>
            </form>
            <p>
                <a href="" onClick={clearServerUrl}>
                    Change server
                </a>
            </p>
        </>
    );
};

const MainPanelContents = ({
    server,
    setServerUrlAndCookie,
    currentUser,
    setCurrentUserAndCookie,
    selectedChatPreview,
    setSelectedChatPreview,
    setChatPreviews,
}: {
    server: Server | null;
    setServerUrlAndCookie: (url: URL | null) => void;
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    setChatPreviews: React.Dispatch<React.SetStateAction<ChatPreview[]>>;
}) => {
    const [isInitialSetupRequired, setIsInitialSetupRequired] = useState(true);

    useEffect(() => {
        async function learnWhetherInitialSetupIsRequired(server: Server) {
            const response = await server.api.get<boolean>(
                "/is_setup_required"
            );
            setIsInitialSetupRequired(response.data === true);
        }
        if (server) {
            learnWhetherInitialSetupIsRequired(server);
        }
    }, [server]);

    if (!server) {
        return <SetServerForm setServerUrlAndCookie={setServerUrlAndCookie} />;
    }

    if (isInitialSetupRequired) {
        return <CreateFirstAdminForm server={server} />;
    }

    if (!currentUser) {
        return (
            <LoginForm
                server={server}
                setServerUrlAndCookie={setServerUrlAndCookie}
                setCurrentUserAndCookie={setCurrentUserAndCookie}
            />
        );
    }

    if (currentUser.is_user_an_admin) {
        return <AdminPanel currentAdminUser={currentUser} server={server} />;
    }

    return (
        <ChatBox
            user={currentUser}
            server={server}
            selectedChatPreview={selectedChatPreview}
            setSelectedChatPreview={setSelectedChatPreview}
            setChatPreviews={setChatPreviews}
        />
    );
};

export default MainPanelContents;
