import axios from "axios";
import { useEffect } from "react";
import "../assets/LeftSidePanelContents.css";
import { BsTrash3Fill } from "react-icons/bs";

const CyrisLogo = () => {
    return <img src="./gh.png" className="logo-test" alt="logo"></img>;
};

const ChatsList = ({
    currentUser,
    setCurrentUserAndCookie,
    serverUrl,
    selectedChatPreview,
    setSelectedChatPreview,
    chatPreviews,
    setChatPreviews,
}: {
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    serverUrl: URL | null;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    chatPreviews: ChatPreview[];
    setChatPreviews: React.Dispatch<React.SetStateAction<ChatPreview[]>>;
}) => {
    const getUsersChats = async () => {
        if (serverUrl) {
            try {
                const response = await axios.get(
                    new URL("/chat_previews", serverUrl).toString(),
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
    }, [currentUser, serverUrl]);

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
                                serverUrl={serverUrl!} // this can't be null when `chats` is a non-empty array
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
    serverUrl,
    setChatPreviews,
}: {
    chat: ChatPreview;
    selectedChatPreview: ChatPreview | null;
    setSelectedChatPreview: React.Dispatch<
        React.SetStateAction<ChatPreview | null>
    >;
    selectThisChat: (chatPreview: ChatPreview) => () => void;
    serverUrl: URL;
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
            await axios.delete(new URL("/chat", serverUrl).toString(), {
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
    serverUrl,
    selectedChatPreview,
    setSelectedChatPreview,
    chatPreviews,
    setChatPreviews,
}: {
    currentUser: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    serverUrl: URL | null;
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
            <ChatsList
                currentUser={currentUser}
                setCurrentUserAndCookie={setCurrentUserAndCookie}
                serverUrl={serverUrl}
                selectedChatPreview={selectedChatPreview}
                setSelectedChatPreview={setSelectedChatPreview}
                chatPreviews={chatPreviews}
                setChatPreviews={setChatPreviews}
            />
        </>
    );
};

export default LeftSidePanelContents;
