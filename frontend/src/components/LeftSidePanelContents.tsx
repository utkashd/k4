import axios from "axios";
import { useEffect } from "react";
import "./LeftSidePanelContents.css";

const CyrisLogo = () => {
    return <img src="./gh.png" className="logo-test" alt="logo"></img>;
};

const ChatsList = ({
    user,
    serverUrl,
    selectedChat,
    setSelectedChat,
    chats,
    setChats,
}: {
    user: User | null;
    serverUrl: URL | null;
    selectedChat: ChatListItem | null;
    setSelectedChat: (selectedChat: ChatListItem | null) => void;
    chats: ChatListItem[];
    setChats: (chatListItems: ChatListItem[]) => void;
}) => {
    const getUsersChats = async () => {
        if (serverUrl) {
            const response = await axios.get(
                new URL("/chats", serverUrl).toString(),
                {
                    withCredentials: true,
                }
            );
            setChats(response.data);
        }
    };

    useEffect(() => {
        if (user && !user.is_user_an_admin) {
            getUsersChats();
        }
    }, [user, serverUrl]);

    const selectThisChat = (chatToSelect: ChatListItem) => {
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
            {chats.map((chat: ChatListItem, index: number) => {
                return (
                    <div key={index}>
                        <ChatPreview
                            chat={chat}
                            selectedChat={selectedChat}
                            key={index}
                            selectThisChat={selectThisChat}
                        />
                    </div>
                );
            })}
        </>
    );
};

const ChatPreview = ({
    chat,
    selectedChat,
    selectThisChat,
}: {
    chat: ChatListItem;
    selectedChat: ChatListItem | null;
    selectThisChat: (chatListItem: ChatListItem) => () => void;
}) => {
    const previewText = (
        <>
            <span className="chat-preview-sender">
                {chat.message_in_db.user_id ? "You:" : "Cyris:"}
            </span>
            <br />
            <span className="chat-preview-message">
                {chat.message_in_db.text}
            </span>
        </>
    );
    if (chat === selectedChat) {
        return <div className="chat-preview-selected">{previewText}</div>;
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
    serverUrl,
    selectedChat,
    setSelectedChat,
    chats,
    setChats,
}: {
    user: User | null;
    serverUrl: URL | null;
    selectedChat: ChatListItem | null;
    setSelectedChat: (selectedChat: ChatListItem | null) => void;
    chats: ChatListItem[];
    setChats: (chatListItems: ChatListItem[]) => void;
}) => {
    return (
        <>
            <CyrisLogo />
            <ChatsList
                user={user}
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
