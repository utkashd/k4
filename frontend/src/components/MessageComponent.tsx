function MessageComponent(props: {
    senderId: string;
    userId: string;
    text: string;
}) {
    return (
        <div
            className={`chat-bubble ${
                props.senderId === props.userId ? "right" : "left"
            }`}
        ></div>
    );
}

export default MessageComponent;
