import { useEffect, useRef, useState } from "react";
import "../assets/ChatBox.css";
import axios, { AxiosResponse } from "axios";
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
    selectedChatPreview,
    setSelectedChatPreview,
    setChatPreviews,
}: {
    user: User;
    serverUrl: URL;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    setChatPreviews: React.Dispatch<React.SetStateAction<ChatPreview[]>>;
}) {
    const [messages, setMessages] = useState([] as MessageInDb[]);
    const [isInputDisabled, setIsInputDisabled] = useState(false);
    const [textAreaValue, setTextAreaValue] = useState("");

    const messagesEndRef = useRef<null | HTMLDivElement>(null);
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    const setCursorOnTextbox = () => {
        if (textAreaRef.current) {
            textAreaRef.current.focus();
        }
    };

    const getAndSetMessages = async (selectedChat: ChatPreview) => {
        const response: AxiosResponse<ApiResponse<Chat>> = await axios.get(
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
        if (selectedChatPreview) {
            getAndSetMessages(selectedChatPreview);
        } else {
            setMessages([]);
        }
    }, [selectedChatPreview]);

    useEffect(() => {
        scrollToBottom();
        setCursorOnTextbox();
    }, [messages, isInputDisabled]);

    const textAreaRef = useRef<HTMLTextAreaElement | null>(null);

    const submitHumanInput = async () => {
        setIsInputDisabled(true);
        const humanInputSaved = textAreaValue;
        setTextAreaValue("");

        if (humanInputSaved) {
            if (selectedChatPreview) {
                const response = await fetch(
                    new URL("/message", serverUrl).toString(),
                    {
                        method: "POST",
                        credentials: "include",
                        headers: {
                            "Content-Type": "application/json",
                            // Authorization: api.defaults.headers.common["Authorization"],
                            //   'Accept': 'text/event-stream',
                        },
                        body: JSON.stringify({
                            chat_id: selectedChatPreview.chat_in_db.chat_id,
                            message: humanInputSaved,
                        }),
                    }
                );

                if (!response.ok) {
                    const errorBody = await response.json();
                    throw new Error(
                        `generateImage HTTP error! status: ${response.status} ${
                            response.statusText
                        }. Details: ${JSON.stringify(errorBody)}`
                    );
                }

                const reader = response.body!.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split("\n").filter(Boolean);

                    for (const line of lines) {
                        try {
                            const update = line;
                            console.log(update);
                        } catch (error) {
                            console.error("Error parsing update:", error);
                        }
                    }
                }
                // const response = await axios.post(
                //     new URL("/test", serverUrl).toString(),
                //     {
                //         chat_id: selectedChat?.chat_in_db.chat_id,
                //         message: humanInputSaved,
                //     },
                //     {
                //         withCredentials: true,
                //         responseType: "stream",
                //     }
                // );
                // response.data.on("data", (data: string) => {
                //     console.log(data);
                // });
                // response.data.on("end", () => {
                //     console.log("END");
                // });

                // const response = await axios.post(
                //     new URL("/message", serverUrl).toString(),
                //     {
                //         chat_id: selectedChat?.chat_in_db.chat_id,
                //         message: humanInputSaved,
                //     },
                //     {
                //         withCredentials: true,
                //     }
                // );
                // const receivedMessages: MessageInDb[] = response.data;
                // setMessages((currentMessages) => {
                //     return [...currentMessages, ...receivedMessages];
                // });
                // setChats((existingChats: ChatListItem[]) => {
                //     return existingChats.map((existingChat: ChatListItem) => {
                //         if (existingChat !== selectedChat) {
                //             return existingChat;
                //         }
                //         const updatedCurrentChat = existingChat;
                //         updatedCurrentChat.message_in_db = receivedMessages[1];
                //         return updatedCurrentChat;
                //     });
                // });
            } else {
                const response = await axios.post(
                    new URL("/chat", serverUrl).toString(),
                    { message: humanInputSaved },
                    { withCredentials: true }
                );
                const receivedMessages: MessageInDb[] = response.data;
                const newChatPreview: ChatPreview = {
                    chat_in_db: {
                        chat_id: receivedMessages[0].chat_id,
                        is_archived: false,
                        last_message_timestamp: receivedMessages[1].inserted_at,
                        title: "",
                        user_id: user.user_id,
                    },
                    most_recent_message_in_db: receivedMessages[1],
                };
                setChatPreviews((currentChatPreviews: ChatPreview[]) => {
                    return [newChatPreview, ...currentChatPreviews];
                });
                setSelectedChatPreview(newChatPreview);
                setMessages(receivedMessages);
            }
            setIsInputDisabled(false);
        }
    };

    if (!user) {
        return <p>Select your user to get started.</p>;
    }

    return (
        <>
            <div className="cyris-chatbox">
                <div
                    className="cyris-chatbox-padded"
                    style={selectedChatPreview ? {} : { alignItems: "center" }}
                    onClick={setCursorOnTextbox}
                >
                    {selectedChatPreview ? (
                        messages.map((message: MessageInDb, index) => {
                            return (
                                <div
                                    key={index}
                                    className={
                                        message.user_id === user.user_id
                                            ? "msg sent"
                                            : "msg received"
                                    }
                                    onClick={(event) => {
                                        event.stopPropagation(); // prevent `setCursorOnTextbox`
                                    }}
                                >
                                    <Markdown>{message.text}</Markdown>
                                </div>
                            );
                        })
                    ) : (
                        <div style={{ height: "100%" }}>
                            <div hidden={isInputDisabled}>
                                <h1>Start a chat...</h1>
                            </div>
                            <div hidden={!isInputDisabled}>
                                <h3>Please wait...</h3>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} style={{ height: "0%" }}></div>
                </div>
                <div className="cyris-chatbox-message-sender">
                    <textarea
                        className="chat-input chat-input-textarea"
                        placeholder="Your message here..."
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
