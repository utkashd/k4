import { useState } from "react";
import Server from "../model/Server";

function CreateUser({
    refreshUsers,
    server,
}: {
    refreshUsers: () => void;
    server: Server;
}) {
    const [humanNameInput, setHumanNameInput] = useState("");
    const [aiNameInput, setAiNameInput] = useState("");

    const submitCreateUser = async (
        event: React.MouseEvent<HTMLElement, MouseEvent>
    ) => {
        event.preventDefault();

        const openAiNameRegex = /^[a-zA-Z0-9_-]+$/;

        if (!openAiNameRegex.test(humanNameInput)) {
            alert("username must match ^[a-zA-Z0-9_-]+$");
            return;
        }

        if (!openAiNameRegex.test(aiNameInput)) {
            alert("username must match ^[a-zA-Z0-9_-]+$");
            return;
        }

        setHumanNameInput("");
        setAiNameInput("");

        if (aiNameInput && humanNameInput) {
            try {
                await server.api.post(
                    "/user",
                    {
                        ai_name: aiNameInput,
                        human_name: humanNameInput,
                    },
                    {
                        headers: {
                            Accept: "application/json",
                            "Content-Type": "application/json",
                        },
                    }
                );
                refreshUsers();
            } catch (error) {
                console.error(
                    "couldn't fetch users. the backend is probably down",
                    error
                );
            }
        }
    };

    return (
        <>
            <div className="createUser">
                <div className="inputs">
                    <div className="input">
                        <input
                            type="text"
                            className="humanNameInput"
                            placeholder="Your name"
                            value={humanNameInput}
                            onChange={(event) => {
                                setHumanNameInput(event.target.value);
                            }}
                        />
                    </div>
                    <div className="input">
                        <input
                            type="text"
                            className="aiNameInput"
                            placeholder="Your AI assistant's name"
                            value={aiNameInput}
                            onChange={(event) => {
                                setAiNameInput(event.target.value);
                            }}
                        />
                    </div>
                </div>
                <br></br>
                <div className="submitCreateUser">
                    <button
                        onClick={(event) => {
                            submitCreateUser(event);
                        }}
                    >
                        Create User
                    </button>
                </div>
            </div>
        </>
    );
}

export default CreateUser;
