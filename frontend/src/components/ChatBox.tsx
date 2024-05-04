import { useEffect, useRef, useState } from "react";
import "./ChatBox.css";
import axios from "axios";
import Markdown from "react-markdown";
import Collapsible from "react-collapsible";

interface Message {
    text: string;
    sender_id: string;
}

function ChatBox({ user }: { user: User | null }) {
    const [messages, setMessages] = useState([] as Message[]);
    const [clientId, setClientId] = useState(null as string | null);
    const [isInputDisabled, setIsInputDisabled] = useState(true);
    const [textAreaValue, setTextAreaValue] = useState("");

    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    let socket: WebSocket | null = null;

    useEffect(() => {
        if (!user) return;
        setMessages([]);
        socket = new WebSocket("ws://localhost:8001/chat");

        socket.onopen = () => {};

        socket.onmessage = (event) => {
            const receivedMessage = JSON.parse(event.data);
            if (typeof receivedMessage.client_id === "string") {
                setClientId(receivedMessage.client_id);
                socket!.send(
                    JSON.stringify({
                        sender_id: receivedMessage.client_id + "_system",
                        text: "start_chat " + user.user_id,
                    })
                );
            } else if (receivedMessage.ready === true) {
                setIsInputDisabled(false);
            } else if (typeof receivedMessage.connection_status !== "string") {
                setMessages((currentMessages) => {
                    return [...currentMessages, receivedMessage];
                });
            }
        };

        socket.onerror = () => {
            if (socket) {
                // TODO tell them to refresh or something
                socket.close();
            }
        };

        socket.onclose = () => {};

        return () => {
            // component unmounted, so we should close the websocket and reset messages
            if (socket) {
                // TODO read this and fix: https://stackoverflow.com/questions/12487828/what-does-websocket-is-closed-before-the-connection-is-established-mean
                socket.close();
            }
            setMessages([]);
        };
    }, [user]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const submitHumanInput = async () => {
        setIsInputDisabled(true);
        const humanInputSaved = textAreaValue;
        setTextAreaValue("");

        if (humanInputSaved && clientId) {
            const humanMessage: Message = {
                text: humanInputSaved,
                sender_id: clientId,
            };
            setMessages((currentMessages) => {
                return [...currentMessages, humanMessage];
            });
            try {
                const response = await axios.post(
                    "http://localhost:8000/ask_gpt_home",
                    humanMessage,
                    {
                        headers: {
                            Accept: "application/json",
                            "Content-Type": "application/json",
                        },
                    }
                );
                const receivedMessages: Message[] = response.data;
                setMessages((currentMessages) => {
                    return [...currentMessages, ...receivedMessages];
                });
            } catch (error) {
                console.error(
                    "couldn't fetch users. the backend is probably down",
                    error
                );
            } finally {
                setIsInputDisabled(false);
            }
        }
    };

    if (!user) {
        return (
            <>
                <p>Select your user to get started.</p>
            </>
        );
    }

    return (
        <>
            <div className="gpt-home-chatbox">
                <div className="gpt-home-chatbox-padded">
                    {messages.map((message: Message, index) => {
                        if (
                            ["gpt_home", clientId].includes(message.sender_id)
                        ) {
                            return (
                                <div
                                    key={index}
                                    className={
                                        message.sender_id === "gpt_home"
                                            ? "msg received"
                                            : "msg sent"
                                    }
                                >
                                    <Markdown>{message.text}</Markdown>
                                </div>
                            );
                        }
                        // else, it's a system message (gpt_home_system)
                        return (
                            <div key={index} className="system-message">
                                <a
                                    href=""
                                    onClick={(event) => {
                                        event.preventDefault();
                                    }}
                                >
                                    <Collapsible trigger=" > System messages">
                                        <Markdown>{message.text}</Markdown>
                                    </Collapsible>
                                </a>
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef}></div>
                    <div hidden={!isInputDisabled}>
                        <p>Please wait...</p>
                    </div>
                </div>
                <div className="gpt-home-chatbox-message-sender">
                    <textarea
                        className="chat-input chat-input-textarea"
                        placeholder="Your query here"
                        value={textAreaValue}
                        onChange={(event) => {
                            setTextAreaValue(event.target.value);
                        }}
                        onKeyDown={(event) => {
                            if (
                                event.key === "Enter" &&
                                event.shiftKey === false
                            ) {
                                event.preventDefault();
                                submitHumanInput();
                            }
                        }}
                        disabled={isInputDisabled}
                    />
                    <button
                        onClick={(event) => {
                            event.preventDefault();
                            submitHumanInput();
                        }}
                        className="chatbox-send-button"
                    >
                        Send
                    </button>
                </div>
            </div>
        </>
    );
}

export default ChatBox;
