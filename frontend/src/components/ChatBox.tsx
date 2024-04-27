import { useEffect, useRef, useState } from "react";
import "./ChatBox.css";
import Markdown from "react-markdown";

interface Message {
    text: string;
    sender_id: string;
}

function ChatBox({ user }: { user: User | null }) {
    const [messages, setMessages] = useState([] as Message[]);
    const [clientId, setClientId] = useState(null as string | null);
    const [isInputDisabled, _setIsInputDisabled] = useState(false);
    const [textAreaValue, setTextAreaValue] = useState("");

    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    let socket: WebSocket | null = null;

    useEffect(() => {
        if (!user) return;
        socket = new WebSocket("ws://localhost:8000/chat");

        socket.onopen = () => {};

        socket.onmessage = (event) => {
            // console.log("message received: ", event);
            const receivedMessage = JSON.parse(event.data);
            if (typeof receivedMessage.client_id === "string") {
                setClientId(receivedMessage.client_id);
                socket!.send(
                    JSON.stringify({
                        sender_id: receivedMessage.client_id + "_system",
                        text: "start_chat " + user.user_id,
                    })
                );
            } else if (typeof receivedMessage.connection_status !== "string") {
                setMessages((currentMessages) => {
                    return [...currentMessages, ...receivedMessage];
                });
            }
        };

        socket.onerror = () => {
            if (socket) {
                // TODO tell them to refresh or something
                socket.close();
            }
        };

        socket.onclose = () => {
            console.log(
                "disconnected. not currently handled. refresh the page, and if you still have problems, ensure the backend is running"
            );
        };

        return () => {
            // component unmounted, so we should close the websocket
            if (socket) {
                // TODO read this and fix: https://stackoverflow.com/questions/12487828/what-does-websocket-is-closed-before-the-connection-is-established-mean
                socket.close();
            }
        };
    }, [user]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const submitHumanInput = async () => {
        // setIsInputDisabled(true);
        const humanInput = textAreaValue;
        setTextAreaValue("");

        if (humanInput && clientId && socket) {
            const humanMessage: Message = {
                text: humanInput,
                sender_id: clientId,
            };
            socket.send(JSON.stringify(humanMessage));
            setMessages((currentMessages) => [
                ...currentMessages,
                humanMessage,
            ]);
            // setIsInputDisabled(false);
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
                        return (
                            <div
                                key={index}
                                className={
                                    ["gpt_home", "system"].includes(
                                        message.sender_id
                                    )
                                        ? "msg received"
                                        : "msg sent"
                                }
                            >
                                <Markdown>{message.text}</Markdown>
                                {/* <div
                                            data-time="2:30"
                                            className="msg sent"
                                        >
                                            asdfasdf
                                        </div> */}
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef}></div>
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

// import { useState, useRef } from "react";
// import MessageComponent from "./MessageComponent";

// type Message = {
//     senderId: string;
//     text: string;
// };

// function ChatBox() {
//     const [messages, setMessages] = useState([]);
//     const scroll = useRef();

//     return (
//         <main className="chatbox">
//             <div className="msg-wrapper">
//                 {messages?.map((message: Message) => {
//                     return (
//                         <MessageComponent
//                             senderId={message.senderId}
//                             text={message.text}
//                             userId="Utkash"
//                         />
//                     );
//                 })}
//             </div>
//             <span ref={scroll}></span>
//             <SendMessage scroll={scroll} />
//         </main>
//     );
// }

// export default ChatBox;
