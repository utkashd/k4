import axios from "axios";
import { useEffect } from "react";
import "../assets/LeftSidePanelContents.css";
import { BsTrash3Fill } from "react-icons/bs";
import Server from "../model/Server";

const CyrisLogo = () => {
    return <img src="./gh.png" className="logo-test" alt="logo"></img>;
};

const ChatsList = ({
    currentUser,
    setCurrentUserAndCookie,
    server,
    selectedChatPreview,
    setSelectedChatPreview,
    chatPreviews,
    setChatPreviews,
}: {
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    server: Server;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    chatPreviews: ChatPreview[];
    setChatPreviews: React.Dispatch<React.SetStateAction<ChatPreview[]>>;
}) => {
    const getUsersChats = async () => {
        if (server) {
            try {
                const response = await server.api.get<ChatPreview[]>(
                    "/chat_previews",
                    { withCredentials: true }
                );
                setChatPreviews(response.data);
            } catch (error: unknown) {
                if (axios.isAxiosError(error)) {
                    if (error.response?.status === 401) {
                        setCurrentUserAndCookie(null);
                    } else {
                        console.error(error);
                    }
                }
            }
        }
    };

    useEffect(() => {
        if (currentUser && !currentUser.is_user_an_admin) {
            getUsersChats();
        } else {
            setChatPreviews([]);
        }
    }, [currentUser, server]);

    const selectThisChat = (chatToSelect: ChatPreview | null) => {
        return () => {
            setSelectedChatPreview(chatToSelect);
        };
    };

    const newChat = () => {
        setSelectedChatPreview(null);
    };

    return (
        <>
            <button onClick={newChat} className="new-chat-button">
                New Chat
            </button>
            <div className="chats-list">
                {chatPreviews.map((chat: ChatPreview, index: number) => {
                    return (
                        <div key={index}>
                            <ChatPreview
                                chat={chat}
                                selectedChatPreview={selectedChatPreview}
                                setSelectedChatPreview={setSelectedChatPreview}
                                selectThisChat={selectThisChat}
                                server={server}
                                setChatPreviews={setChatPreviews}
                            />
                        </div>
                    );
                })}
            </div>
        </>
    );
};

const ChatPreview = ({
    chat,
    selectedChatPreview,
    setSelectedChatPreview,
    selectThisChat,
    server,
    setChatPreviews,
}: {
    chat: ChatPreview;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    selectThisChat: (chatPreview: ChatPreview) => () => void;
    server: Server;
    setChatPreviews: React.Dispatch<React.SetStateAction<ChatPreview[]>>;
}) => {
    const previewText = (
        <div>
            <span className="chat-preview-sender">
                {chat.most_recent_message_in_db.user_id ? "You:" : "Cyris:"}
            </span>
            <br />
            <span className="chat-preview-message">
                {chat.most_recent_message_in_db.text.length > 45
                    ? chat.most_recent_message_in_db.text.substring(0, 50) +
                      "..."
                    : chat.most_recent_message_in_db.text}
            </span>
        </div>
    );
    const deleteChat = async (chatToDelete: ChatPreview) => {
        const areTheySureTheyWantToDeleteTheChat = confirm(
            "Are you sure you want to delete this chat?"
        );
        if (areTheySureTheyWantToDeleteTheChat) {
            await server.api.delete("/chat", {
                params: {
                    chat_id: chatToDelete.chat_in_db.chat_id,
                },
                withCredentials: true,
            });
            setChatPreviews((chats: ChatPreview[]) => {
                return chats.filter((chatPreview: ChatPreview) => {
                    return (
                        chatPreview.chat_in_db.chat_id !==
                        chatToDelete.chat_in_db.chat_id
                    );
                });
            });
            setSelectedChatPreview(null);
        }
    };
    if (chat === selectedChatPreview) {
        return (
            <>
                <div className="chat-preview-selected">
                    {previewText}
                    <BsTrash3Fill
                        className="delete-chat-button"
                        onClick={(event) => {
                            event.preventDefault();
                            deleteChat(chat);
                        }}
                    />
                </div>
            </>
        );
    } else {
        return (
            <div className="chat-preview">
                <div onClick={selectThisChat(chat)}>{previewText}</div>
            </div>
        );
    }
};

const LeftSidePanelContents = ({
    currentUser,
    setCurrentUserAndCookie,
    server,
    selectedChatPreview,
    setSelectedChatPreview,
    chatPreviews,
    setChatPreviews,
}: {
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    server: Server | null;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    chatPreviews: ChatPreview[];
    setChatPreviews: React.Dispatch<React.SetStateAction<ChatPreview[]>>;
}) => {
    return (
        <>
            <CyrisLogo />
            {server ? (
                <ChatsList
                    currentUser={currentUser}
                    setCurrentUserAndCookie={setCurrentUserAndCookie}
                    server={server}
                    selectedChatPreview={selectedChatPreview}
                    setSelectedChatPreview={setSelectedChatPreview}
                    chatPreviews={chatPreviews}
                    setChatPreviews={setChatPreviews}
                />
            ) : (
                <></>
            )}
        </>
    );
};

export default LeftSidePanelContents;
