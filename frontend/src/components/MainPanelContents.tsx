import { useEffect, useState } from "react";
import "../assets/SetServerForm.css";
import Server from "../model/Server";
import { useNavigate } from "react-router-dom";

export function SetServer({
    setServerUrlAndCookie,
    server,
}: {
    setServerUrlAndCookie: (url: URL | null) => void;
    server: Server | null;
}) {
    const navigate = useNavigate();
    useEffect(() => {
        if (server) {
            navigate("/");
            return;
        }
    }, [navigate, server]);
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

export const Setup = ({
    server,
    setCurrentUserAndCookie,
}: {
    server: Server | null;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    const navigate = useNavigate();
    useEffect(() => {
        if (!server) {
            navigate("/");
            return;
        }
    }, [navigate, server]);
    if (!server) {
        return null;
    }
    const [firstAdminUsernameInput, setFirstAdminUsernameInput] = useState("");
    const [firstAdminPasswordInput, setFirstAdminPasswordInput] = useState("");

    const createFirstAdmin = async () => {
        await server.api.post("/first_admin", {
            desired_user_email: firstAdminUsernameInput,
            desired_user_password: firstAdminPasswordInput,
        });
        // TODO this is a copy/paste of the login code. maybe don't do that lol
        await server.api.post(
            "/token",
            new URLSearchParams({
                username: firstAdminUsernameInput,
                password: firstAdminPasswordInput,
            }),
            { withCredentials: true }
        );
        const currentUserRequestResponse = await server.api.get<User>(
            "/user/me",
            { withCredentials: true }
        );
        setCurrentUserAndCookie(currentUserRequestResponse.data);
        navigate("/");
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
                        createFirstAdmin();
                    }}
                >
                    Create Admin
                </button>
            </div>
        </>
    );
};

export const Login = ({
    server,
    currentUser,
    setServerUrlAndCookie,
    setCurrentUserAndCookie,
}: {
    server: Server | null;
    currentUser: User | null;
    setServerUrlAndCookie: (url: URL | null) => void;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    const navigate = useNavigate();
    useEffect(() => {
        if (!server) {
            navigate("/");
            return;
        }
        if (currentUser) {
            navigate("/");
            return;
        }
    }, [server, currentUser, navigate]);

    if (!server) {
        return null;
    }

    const clearServerUrl = () => {
        setServerUrlAndCookie(null);
    };
    const [usernameInput, setUsernameInput] = useState("");
    const [passwordInput, setPasswordInput] = useState("");

    const submitLogin = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        e.stopPropagation();
        await server.api.post(
            "/token",
            new URLSearchParams({
                username: usernameInput,
                password: passwordInput,
            }),
            { withCredentials: true }
        );
        const currentUserRequestResponse = await server.api.get<User>(
            "/user/me",
            { withCredentials: true }
        );
        setCurrentUserAndCookie(currentUserRequestResponse.data);
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
                        Login to {server.url.toString()}
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
