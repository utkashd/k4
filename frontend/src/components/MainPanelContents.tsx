import { useState } from "react";
import "./SetServerForm.css";
import axios from "axios";

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

    const submitLogin = async (
        usernameInput: string,
        passwordInput: string
    ) => {
        try {
            const response = await axios.post(
                "http://0.0.0.0:8000/token",
                new URLSearchParams({
                    grant_type: "password",
                    username: usernameInput,
                    password: passwordInput,
                }),
                {
                    headers: {
                        accept: "application/json, text/plain, */*",
                        authorization: "Basic Og==",
                    },
                }
            );
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
                        submitLogin(usernameInput, passwordInput);
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
}: {
    serverUrl: URL | null;
    setServerUrlAndCookie: (url: URL | null) => void;
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
}) => {
    if (!serverUrl) {
        return <SetServerForm setServerUrlAndCookie={setServerUrlAndCookie} />;
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

    return <>{serverUrl ? serverUrl.toString() : "hi"}</>;
};

export default MainPanelContents;
