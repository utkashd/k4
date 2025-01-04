import { useEffect, useRef, useState } from "react";
import "./ChatBox.css";
import axios from "axios";
import Markdown from "react-markdown";

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
    const [isInputDisabled, setIsInputDisabled] = useState(false);
    const [textAreaValue, setTextAreaValue] = useState("");

    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

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
        if (textAreaRef.current) {
            textAreaRef.current.focus();
        }
    }, [messages, isInputDisabled]);

    const textAreaRef = useRef<HTMLTextAreaElement | null>(null);

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
                setChats((existingChats: ChatListItem[]) => {
                    return existingChats.map((existingChat: ChatListItem) => {
                        if (existingChat !== selectedChat) {
                            return existingChat;
                        }
                        const updatedCurrentChat = existingChat;
                        updatedCurrentChat.message_in_db = receivedMessages[1];
                        return updatedCurrentChat;
                    });
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
                        ref={textAreaRef}
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
