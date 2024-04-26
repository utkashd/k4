import { useEffect, useRef, useState } from "react";
import "./ChatBox.css";
import axios from "axios";
import Markdown from "react-markdown";

interface Message {
    text: string;
    sender_id: string;
}

function ChatBox({ user }: { user: User | null }) {
    const [messages, setMessages] = useState([] as Message[]);
    const [clientId, setClientId] = useState(null as string | null);
    const [isInputDisabled, setIsInputDisabled] = useState(false);
    const [humanInput, setHumanInput] = useState("");

    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    let socket: WebSocket | null = null;

    useEffect(() => {
        if (!user) return;
        socket = new WebSocket("ws://localhost:8001/chat");

        socket.onopen = () => {};

        socket.onmessage = (event) => {
            // console.log("message received: ", event);
            const message = JSON.parse(event.data);
            if (typeof message.client_id === "string") {
                setClientId(message.client_id);
                socket!.send(
                    JSON.stringify({
                        sender_id: message.client_id + "_system",
                        text: "start_chat " + user.user_id,
                    })
                );
            } else if (typeof message.connection_status !== "string") {
                setMessages((msgs) => [...msgs, message]);
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
                "disconnected. not currently handled correctly. refresh the page after ensuring the backend is running"
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
        setIsInputDisabled(true);
        const humanInputSaved = humanInput;
        setHumanInput("");

        if (humanInputSaved && clientId) {
            try {
                const humanMessage: Message = {
                    text: humanInputSaved,
                    sender_id: clientId,
                };
                setMessages([...messages, humanMessage]);
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
                setMessages([...messages, humanMessage, ...receivedMessages]);
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

    // useEffect(() => {}, [user]);

    // useEffect(() => {
    //     const source = axios.CancelToken.source();
    //     const askGptHome = async (message: Message) => {
    //         try {
    //             const response = await axios.post(
    //                 "http://localhost:8000/users"
    //             );
    //             console.log(response.data);
    //             // setUsers(response.data as User[]);
    //         } catch (error) {
    //             console.error(
    //                 "couldn't fetch users. the backend is probably down",
    //                 error
    //             );
    //             // setUsers([] as User[]);
    //         }
    //     };

    //     setTimeout(() => {
    //         askGptHome();
    //     }, 1000);

    //     return () => {
    //         source.cancel();
    //     };
    // }, sentMessages);

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
                        value={humanInput}
                        onChange={(event) => {
                            setHumanInput(event.target.value);
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
