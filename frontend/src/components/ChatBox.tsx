import { useEffect, useRef, useState } from "react";
import "./ChatBox.css";
import axios from "axios";
import Markdown from "react-markdown";
import Collapsible from "react-collapsible";
import { v4 as uuidv4 } from "uuid";

interface Message {
    text: string;
    sender_id: string;
}

function ChatBox({
    user,
    chatWsEndpoint,
}: {
    user: User;
    chatWsEndpoint: URL;
}) {
    const [messages, setMessages] = useState([] as Message[]);
    const [clientId, setClientId] = useState(null as string | null);
    const [isInputDisabled, setIsInputDisabled] = useState(true);
    const [textAreaValue, setTextAreaValue] = useState("");

    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // let socket: WebSocket | null = null;
    const ws = useRef(null as WebSocket | null);

    useEffect(() => {
        ws.current = new WebSocket(chatWsEndpoint);
        // ws.current.onopen = () => {};
        ws.current.onmessage = (event) => {
            const receivedMessage = JSON.parse(event.data);
            console.log(receivedMessage);
            if (receivedMessage["session_id"]) {
                setClientId(receivedMessage.session_id);
                ws.current?.send(
                    JSON.stringify({
                        client_generated_message_uuid: uuidv4().toString(),
                        text: "sup??",
                        sender_id: user.user_id,
                        chat_id: 1,
                    })
                );
            }

            // if (typeof receivedMessage.client_id === "string") {
            //     setClientId(receivedMessage.client_id);
            //     ws.current!.send(
            //         JSON.stringify({
            //             sender_id: receivedMessage.client_id + "_system",
            //             text: "start_chat " + user.user_id,
            //         })
            //     );
            // } else if (receivedMessage.ready === true) {
            //     setIsInputDisabled(false);
            // } else if (typeof receivedMessage.connection_status !== "string") {
            //     setMessages((currentMessages) => {
            //         return [...currentMessages, receivedMessage];
            //     });
            // }
        };

        const cleanup = () => {
            ws.current?.close();
            ws.current = null;
            setMessages([]);
            // If you're getting a warning that leads you here, it's because in
            // development, React strict mode causes some wonkiness. You can ignore the warning.
            // https://stackoverflow.com/questions/12487828/what-does-websocket-is-closed-before-the-connection-is-established-mean

            // TODO tell them to refresh or something
        };
        const logAndCleanup = (event: Event) => {
            console.log(event);
            cleanup();
        };

        ws.current.onerror = logAndCleanup;

        ws.current.onclose = logAndCleanup;

        return cleanup;
    }, [user]);

    // useEffect(() => {
    //     const socket = new WebSocket(chatWsEndpoint);

    //     socket.onmessage = (event) => {
    //         console.log(event.data);
    //     };

    //     return () => {
    //         socket.close();
    //     };
    // }, []);

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
                    "http://localhost:8000/ask_cyris",
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
            <div className="cyris-chatbox">
                <div className="cyris-chatbox-padded">
                    {messages.map((message: Message, index) => {
                        if (["cyris", clientId].includes(message.sender_id)) {
                            return (
                                <div
                                    key={index}
                                    className={
                                        message.sender_id === "cyris"
                                            ? "msg received"
                                            : "msg sent"
                                    }
                                >
                                    <Markdown>{message.text}</Markdown>
                                </div>
                            );
                        }
                        // else, it's a system message (cyris_system)
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
                <div className="cyris-chatbox-message-sender">
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
