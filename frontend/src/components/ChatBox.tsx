import { useEffect, useRef, useState } from "react";
import "./ChatBox.css";
import axios from "axios";
import Markdown from "react-markdown";
// import Collapsible from "react-collapsible";
// import { v4 as uuidv4 } from "uuid";

// class MessageInDb(BaseModel):
// message_id: int
// chat_id: int
// user_id: int | None
// text: str
// inserted_at: datetime.datetime

interface MessageInDb {
    message_id: number;
    chat_id: number;
    user_id: number | null;
    text: string;
    inserted_at: string;
}

function ChatBox({
    user,
    serverUrl,
    selectedChat,
    setSelectedChat,
    setChats,
}: {
    user: User;
    serverUrl: URL;
    selectedChat: ChatListItem | null;
    setSelectedChat: React.Dispatch<React.SetStateAction<ChatListItem | null>>;
    setChats: React.Dispatch<React.SetStateAction<ChatListItem[]>>;
}) {
    const [messages, setMessages] = useState([] as MessageInDb[]);
    // const [clientId, setClientId] = useState(null as string | null);
    const [isInputDisabled, setIsInputDisabled] = useState(false);
    const [textAreaValue, setTextAreaValue] = useState("");

    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // let socket: WebSocket | null = null;
    // const ws = useRef(null as WebSocket | null);

    // useEffect(() => {
    //     ws.current = new WebSocket(chatWsEndpoint);
    //     // ws.current.onopen = () => {};
    //     ws.current.onmessage = (event) => {
    //         const receivedMessage = JSON.parse(event.data);
    //         console.log(receivedMessage);
    //         if (receivedMessage["session_id"]) {
    //             setClientId(receivedMessage.session_id);
    //             ws.current?.send(
    //                 JSON.stringify({
    //                     client_generated_message_uuid: uuidv4().toString(),
    //                     text: "sup??",
    //                     sender_id: user.user_id,
    //                     chat_id: 1,
    //                 })
    //             );
    //         }

    //         // if (typeof receivedMessage.client_id === "string") {
    //         //     setClientId(receivedMessage.client_id);
    //         //     ws.current!.send(
    //         //         JSON.stringify({
    //         //             sender_id: receivedMessage.client_id + "_system",
    //         //             text: "start_chat " + user.user_id,
    //         //         })
    //         //     );
    //         // } else if (receivedMessage.ready === true) {
    //         //     setIsInputDisabled(false);
    //         // } else if (typeof receivedMessage.connection_status !== "string") {
    //         //     setMessages((currentMessages) => {
    //         //         return [...currentMessages, receivedMessage];
    //         //     });
    //         // }
    //     };

    //     const cleanup = () => {
    //         ws.current?.close();
    //         ws.current = null;
    //         setMessages([]);
    //         // If you're getting a warning that leads you here, it's because in
    //         // development, React strict mode causes some wonkiness. You can ignore the warning.
    //         // https://stackoverflow.com/questions/12487828/what-does-websocket-is-closed-before-the-connection-is-established-mean

    //         // TODO tell them to refresh or something
    //     };
    //     const logAndCleanup = (event: Event) => {
    //         console.log(event);
    //         cleanup();
    //     };

    //     ws.current.onerror = logAndCleanup;

    //     ws.current.onclose = logAndCleanup;

    //     return cleanup;
    // }, [user]);

    const getAndSetMessages = async (selectedChat: ChatListItem) => {
        const response = await axios.get(
            new URL("/chat", serverUrl).toString(),
            {
                withCredentials: true,
                params: {
                    chat_id: selectedChat.chat_in_db.chat_id,
                },
            }
        );
        setMessages(response.data);
    };

    useEffect(() => {
        if (selectedChat) {
            getAndSetMessages(selectedChat);
        } else {
            setMessages([]);
        }
    }, [selectedChat]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const submitHumanInput = async () => {
        setIsInputDisabled(true);
        const humanInputSaved = textAreaValue;
        setTextAreaValue("");

        if (humanInputSaved) {
            if (selectedChat) {
                const response = await axios.post(
                    new URL("/message", serverUrl).toString(),
                    {
                        chat_id: selectedChat?.chat_in_db.chat_id,
                        message: humanInputSaved,
                    },
                    {
                        withCredentials: true,
                    }
                );
                const receivedMessages: MessageInDb[] = response.data;
                setMessages((currentMessages) => {
                    return [...currentMessages, ...receivedMessages];
                });
            } else {
                const response = await axios.post(
                    new URL("/chat", serverUrl).toString(),
                    {
                        message: humanInputSaved,
                    },
                    {
                        withCredentials: true,
                    }
                );
                const receivedMessages: MessageInDb[] = response.data;
                const newChatListItem: ChatListItem = {
                    chat_in_db: {
                        chat_id: receivedMessages[0].chat_id,
                        is_archived: false,
                        last_message_timestamp: receivedMessages[1].inserted_at,
                        title: "",
                        user_id: user.user_id,
                    },
                    message_in_db: receivedMessages[1],
                };
                setChats((currentChats: ChatListItem[]) => {
                    return [newChatListItem, ...currentChats];
                });
                setSelectedChat(newChatListItem);
                setMessages(receivedMessages);
            }
            setIsInputDisabled(false);
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
                    {messages.map((message: MessageInDb, index) => {
                        if (message.user_id === user.user_id) {
                            return (
                                <div key={index} className={"msg sent"}>
                                    <Markdown>{message.text}</Markdown>
                                </div>
                            );
                        } else {
                            return (
                                <div key={index} className={"msg received"}>
                                    <Markdown>{message.text}</Markdown>
                                </div>
                            );
                        }
                        // else, it's a system message (cyris_system)
                        // return (
                        //     <div key={index} className="system-message">
                        //         <a
                        //             href=""
                        //             onClick={(event) => {
                        //                 event.preventDefault();
                        //             }}
                        //         >
                        //             <Collapsible trigger=" > System messages">
                        //                 <Markdown>{message.text}</Markdown>
                        //             </Collapsible>
                        //         </a>
                        //     </div>
                        // );
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
