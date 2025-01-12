import axios from "axios";
import { useEffect } from "react";
import "../assets/LeftSidePanelContents.css";
import { BsTrash3Fill } from "react-icons/bs";

const CyrisLogo = () => {
    return <img src="./gh.png" className="logo-test" alt="logo"></img>;
};

const ChatsList = ({
    user,
    setCurrentUserAndCookie,
    serverUrl,
    selectedChat,
    setSelectedChat,
    chats,
    setChats,
}: {
    user: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    serverUrl: URL | null;
    selectedChat: ChatListItem | null;
    setSelectedChat: React.Dispatch<React.SetStateAction<ChatListItem | null>>;
    chats: ChatListItem[];
    setChats: React.Dispatch<React.SetStateAction<ChatListItem[]>>;
}) => {
    const getUsersChats = async () => {
        if (serverUrl) {
            try {
                const response = await axios.get(
                    new URL("/chats", serverUrl).toString(),
                    { withCredentials: true }
                );
                setChats(response.data);
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
        if (user && !user.is_user_an_admin) {
            getUsersChats();
        } else {
            setChats([]);
        }
    }, [user, serverUrl]);

    const selectThisChat = (chatToSelect: ChatListItem | null) => {
        return () => {
            setSelectedChat(chatToSelect);
        };
    };

    const newChat = () => {
        setSelectedChat(null);
    };

    return (
        <>
            <button onClick={newChat} className="new-chat-button">
                New Chat
            </button>
            <div className="chats-list">
                {chats.map((chat: ChatListItem, index: number) => {
                    return (
                        <div key={index}>
                            <ChatPreview
                                chat={chat}
                                selectedChat={selectedChat}
                                setSelectedChat={setSelectedChat}
                                selectThisChat={selectThisChat}
                                serverUrl={serverUrl!} // this can't be null when `chats` is a non-empty array
                                setChats={setChats}
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
    selectedChat,
    setSelectedChat,
    selectThisChat,
    serverUrl,
    setChats,
}: {
    chat: ChatListItem;
    selectedChat: ChatListItem | null;
    setSelectedChat: React.Dispatch<React.SetStateAction<ChatListItem | null>>;
    selectThisChat: (chatListItem: ChatListItem) => () => void;
    serverUrl: URL;
    setChats: React.Dispatch<React.SetStateAction<ChatListItem[]>>;
}) => {
    const previewText = (
        <div>
            <span className="chat-preview-sender">
                {chat.message_in_db.user_id ? "You:" : "Cyris:"}
            </span>
            <br />
            <span className="chat-preview-message">
                {chat.message_in_db.text}
            </span>
        </div>
    );
    const deleteChat = async (chatToDelete: ChatListItem) => {
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
            setChats((chats: ChatListItem[]) => {
                return chats.filter((chatListItem: ChatListItem) => {
                    return (
                        chatListItem.chat_in_db.chat_id !==
                        chatToDelete.chat_in_db.chat_id
                    );
                });
            });
            setSelectedChat(null);
        }
    };
    if (chat === selectedChat) {
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
    user,
    setCurrentUserAndCookie,
    serverUrl,
    selectedChat,
    setSelectedChat,
    chats,
    setChats,
}: {
    user: User | null;
    setCurrentUserAndCookie: (user: User | null) => void;
    serverUrl: URL | null;
    selectedChat: ChatListItem | null;
    setSelectedChat: React.Dispatch<React.SetStateAction<ChatListItem | null>>;
    chats: ChatListItem[];
    setChats: React.Dispatch<React.SetStateAction<ChatListItem[]>>;
}) => {
    return (
        <>
            <CyrisLogo />
            <ChatsList
                user={user}
                setCurrentUserAndCookie={setCurrentUserAndCookie}
                serverUrl={serverUrl}
                selectedChat={selectedChat}
                setSelectedChat={setSelectedChat}
                chats={chats}
                setChats={setChats}
            />
        </>
    );
};

export default LeftSidePanelContents;
