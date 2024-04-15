import { useState, useRef } from "react";
import MessageComponent from "./MessageComponent";

type Message = {
    senderId: string;
    text: string;
};

function ChatBox() {
    const [messages, setMessages] = useState([]);
    const scroll = useRef();

    return (
        <main className="chatbox">
            <div className="msg-wrapper">
                {messages?.map((message: Message) => {
                    return (
                        <MessageComponent
                            senderId={message.senderId}
                            text={message.text}
                            userId="Utkash"
                        />
                    );
                })}
            </div>
            <span ref={scroll}></span>
            <SendMessage scroll={scroll} />
        </main>
    );
}

export default ChatBox;
