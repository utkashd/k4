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
    const scrollToBottomOfMessages = () => {
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
        scrollToBottomOfMessages();
        setCursorOnTextbox(); // TODO this isn't working for some reason
    }, [chats]);

    const textAreaRef = useRef<HTMLTextAreaElement | null>(null);

    const submitHumanInput = async () => {
        if (textAreaValue === "") {
            return;
        }
        setIsInputDisabled(true);
        const humanInputSaved = textAreaValue;

        if (humanInputSaved) {
            let response;
            let chatId: number;
            let isNewChat: boolean;
            if (selectedChatPreview) {
                // sending a message in an existing chat; chat_id is known
                isNewChat = false;
                chatId = selectedChatPreview.chat_in_db.chat_id;
                response = await fetch(
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
                            llm_model_name: "gpt-4o-mini",
                            llm_provider: "openai",
                        }),
                    }
                );
            } else {
                // starting a new chat; chat_id is TBD
                isNewChat = true;
                response = await fetch(
                    new URL("/chat", server.url).toString(),
                    {
                        method: "POST",
                        credentials: "include",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                            message: humanInputSaved,
                            llm_model_name: "gpt-4o-mini",
                            llm_provider: "openai",
                        }),
                    }
                );
            }

            if (!response.ok) {
                if (response.status == 400) {
                    alert(
                        "This chat has gotten too long, please start a new one"
                    );
                } else {
                    const errorBody = await response.json();
                    console.log(
                        "unexpected issue with chat response",
                        errorBody
                    );
                }
            } else {
                setTextAreaValue("");
                const reader = response.body!.getReader();
                const decoder = new TextDecoder();

                let response_message_so_far = "";
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) {
                        setChatPreviews((existingChatPreviews) => {
                            return existingChatPreviews.map(
                                (existingChatPreview) => {
                                    if (
                                        chatId &&
                                        existingChatPreview.chat_in_db
                                            .chat_id === chatId
                                    ) {
                                        const updatedChatPreview = {
                                            ...existingChatPreview,
                                            most_recent_message_in_db: {
                                                ...existingChatPreview.most_recent_message_in_db,
                                                text: response_message_so_far,
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
                            // received part 1 of 3: the message we sent. This includes the
                            // chat_id of the (potentially new) chat.
                            const userMessage = parsedLine;
                            chatId = userMessage.chat_id;

                            if (isNewChat) {
                                const newChatInDb: ChatInDb = {
                                    chat_id: userMessage.chat_id,
                                    is_archived: false,
                                    last_message_timestamp:
                                        userMessage.inserted_at,
                                    title: "",
                                    user_id: user.user_id,
                                };
                                setChats((existingChats) => {
                                    return {
                                        ...existingChats,
                                        [userMessage.chat_id]: {
                                            chat_in_db: newChatInDb,
                                            messages: [userMessage],
                                        },
                                    };
                                });
                                const newChatPreview: ChatPreview = {
                                    chat_in_db: newChatInDb,
                                    most_recent_message_in_db: userMessage,
                                };
                                setChatPreviews(
                                    (currentChatPreviews: ChatPreview[]) => {
                                        return [
                                            newChatPreview,
                                            ...currentChatPreviews,
                                        ];
                                    }
                                );
                                setSelectedChatPreview(newChatPreview);
                            } else {
                                setChats((existingChats) => {
                                    const updatedChats = { ...existingChats };
                                    const chatMessages = [
                                        ...updatedChats[userMessage.chat_id]!
                                            .messages,
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
                                                    .chat_id ===
                                                parsedLine.chat_id
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
                            }
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
                                const chat = existingChats[parsedLine.chat_id];
                                const updatedMessages = chat.messages.map(
                                    (message, index) => {
                                        if (
                                            index ===
                                            chat.messages.length - 1
                                        ) {
                                            response_message_so_far =
                                                message.text + parsedLine.chunk;
                                            return {
                                                ...message,
                                                text: response_message_so_far,
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
                                    ref={
                                        index ===
                                        chats[
                                            selectedChatPreview.chat_in_db
                                                .chat_id
                                        ].messages.length -
                                            2
                                            ? messagesEndRef
                                            : null
                                    }
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
