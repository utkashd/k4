import { useEffect, useRef, useState } from "react";
import "../assets/ChatBox.css";
import Markdown from "react-markdown";
import Server from "../model/Server";

interface MessageInDb {
    message_id: number;
    chat_id: number;
    user_id: number | null;
    text: string;
    inserted_at: string;
}

function ChatBox({
    user,
    server,
    selectedChatPreview,
    setSelectedChatPreview,
    setChatPreviews,
}: {
    user: User;
    server: Server;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    setChatPreviews: React.Dispatch<React.SetStateAction<ChatPreview[]>>;
}) {
    const [chats, setChats] = useState<Record<number, Chat>>({});
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
        if (!(selectedChat.chat_in_db.chat_id in chats)) {
            const response = await server.api.get<Chat>("/chat", {
                withCredentials: true,
                params: {
                    chat_id: selectedChat.chat_in_db.chat_id,
                },
            });
            setChats((existingChats) => {
                return {
                    ...existingChats,
                    [selectedChat.chat_in_db.chat_id]: {
                        chat_in_db: selectedChat.chat_in_db,
                        messages: response.data.messages,
                    },
                };
            });
        }
    };

    useEffect(() => {
        if (selectedChatPreview) {
            getAndSetMessages(selectedChatPreview);
        }
    }, [selectedChatPreview]);

    useEffect(() => {
        scrollToBottom();
        setCursorOnTextbox();
    }, [chats]);

    const textAreaRef = useRef<HTMLTextAreaElement | null>(null);

    const submitHumanInput = async () => {
        setIsInputDisabled(true);
        const humanInputSaved = textAreaValue;
        setTextAreaValue(""); // TODO don't clear this until we start to get a response from the server

        if (humanInputSaved) {
            if (selectedChatPreview) {
                const chatId = selectedChatPreview.chat_in_db.chat_id;
                const response = await fetch(
                    new URL("/message", server.url).toString(),
                    {
                        method: "POST",
                        credentials: "include",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            chat_id: chatId,
                            message: humanInputSaved,
                        }),
                    }
                );

                const reader = response.body!.getReader();
                const decoder = new TextDecoder();

                interface LlmStreamingResponse {
                    chunk_type: "text" | "msg_start";
                    chat_id: number;
                }

                interface LlmStreamingStart extends LlmStreamingResponse {
                    chunk_type: "msg_start";
                }

                interface LlmStreamingChunk extends LlmStreamingResponse {
                    chunk_type: "text";
                    chunk: string;
                }

                let message_so_far = "";
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        setChatPreviews((existingChatPreviews) => {
                            return existingChatPreviews.map(
                                (existingChatPreview) => {
                                    if (
                                        existingChatPreview.chat_in_db
                                            .chat_id === chatId
                                    ) {
                                        const updatedChatPreview = {
                                            ...existingChatPreview,
                                            most_recent_message_in_db: {
                                                ...existingChatPreview.most_recent_message_in_db,
                                                text: message_so_far,
                                            },
                                        };
                                        return updatedChatPreview;
                                    } else {
                                        return existingChatPreview;
                                    }
                                }
                            );
                        });
                        break;
                    }

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split("\n").filter(Boolean);

                    for (const line of lines) {
                        const parsedLine:
                            | MessageInDb
                            | LlmStreamingStart
                            | LlmStreamingChunk = JSON.parse(line);
                        if ("message_id" in parsedLine) {
                            const userMessage = parsedLine;

                            setChats((existingChats) => {
                                const updatedChats = { ...existingChats };
                                const chatMessages = [
                                    ...(updatedChats[userMessage.chat_id]
                                        ?.messages || []),
                                ];

                                if (
                                    !chatMessages.some(
                                        (msg) =>
                                            msg.message_id ===
                                            userMessage.message_id
                                    )
                                ) {
                                    // Prevent duplicate messages
                                    chatMessages.push(userMessage);
                                }

                                updatedChats[userMessage.chat_id] = {
                                    ...updatedChats[userMessage.chat_id],
                                    messages: chatMessages,
                                };
                                return updatedChats;
                            });
                            setChatPreviews((existingChatPreviews) => {
                                return existingChatPreviews.map(
                                    (existingChatPreview) => {
                                        if (
                                            existingChatPreview.chat_in_db
                                                .chat_id === parsedLine.chat_id
                                        ) {
                                            const updatedChatPreview = {
                                                ...existingChatPreview,
                                                most_recent_message_in_db: {
                                                    ...existingChatPreview.most_recent_message_in_db,
                                                    text: parsedLine.text,
                                                },
                                            };
                                            return updatedChatPreview;
                                        } else {
                                            return existingChatPreview;
                                        }
                                    }
                                );
                            });
                        } else if (parsedLine.chunk_type == "msg_start") {
                            setChats((existingChats) => {
                                const updatedChats = { ...existingChats };
                                const chatMessages = [
                                    ...(updatedChats[parsedLine.chat_id]
                                        ?.messages || []),
                                ];

                                chatMessages.push({
                                    message_id: -1,
                                    user_id: null,
                                    chat_id: parsedLine.chat_id,
                                    inserted_at: "",
                                    text: "",
                                });

                                updatedChats[parsedLine.chat_id] = {
                                    ...updatedChats[parsedLine.chat_id],
                                    messages: chatMessages,
                                };
                                return updatedChats;
                            });
                            setChatPreviews((existingChatPreviews) => {
                                return existingChatPreviews.map(
                                    (existingChatPreview) => {
                                        if (
                                            existingChatPreview.chat_in_db
                                                .chat_id === parsedLine.chat_id
                                        ) {
                                            const updatedChatPreview = {
                                                ...existingChatPreview,
                                                most_recent_message_in_db: {
                                                    ...existingChatPreview.most_recent_message_in_db,
                                                    text: "...response started...",
                                                },
                                            };
                                            return updatedChatPreview;
                                        } else {
                                            return existingChatPreview;
                                        }
                                    }
                                );
                            });
                        } else {
                            setChats((existingChats) => {
                                // Check if the chat exists in the current state
                                const chat = existingChats[parsedLine.chat_id];

                                // Update the most recent message
                                const updatedMessages = chat.messages.map(
                                    (message, index) => {
                                        if (
                                            index ===
                                            chat.messages.length - 1
                                        ) {
                                            message_so_far =
                                                message.text + parsedLine.chunk;
                                            return {
                                                ...message,
                                                text: message_so_far,
                                            };
                                        }
                                        return message;
                                    }
                                );

                                return {
                                    ...existingChats,
                                    [parsedLine.chat_id]: {
                                        ...chat,
                                        messages: updatedMessages,
                                    },
                                };
                            });
                            setChatPreviews((existingChatPreviews) => {
                                return existingChatPreviews.map(
                                    (existingChatPreview) => {
                                        if (
                                            existingChatPreview.chat_in_db
                                                .chat_id === parsedLine.chat_id
                                        ) {
                                            const updatedChatPreview = {
                                                ...existingChatPreview,
                                                most_recent_message_in_db: {
                                                    ...existingChatPreview.most_recent_message_in_db,
                                                    text: "...response pending...",
                                                },
                                            };
                                            return updatedChatPreview;
                                        } else {
                                            return existingChatPreview;
                                        }
                                    }
                                );
                            });
                        }
                    }
                }
            } else {
                const response = await server.api.post<MessageInDb[]>(
                    "/chat",
                    { message: humanInputSaved },
                    { withCredentials: true }
                );
                const receivedMessages = response.data;
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
                setChats((existingChats) => {
                    existingChats[receivedMessages[0].chat_id] = {
                        chat_in_db: newChatPreview.chat_in_db,
                        messages: receivedMessages,
                    };
                    return existingChats;
                });
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
                        chats[
                            selectedChatPreview.chat_in_db.chat_id
                        ]?.messages.map((message, index) => {
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
