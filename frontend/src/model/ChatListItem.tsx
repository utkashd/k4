interface ChatListItem {
    chat_in_db: ChatInDb;
    message_in_db: MessageInDb;
}
interface ChatInDb {
    chat_id: number;
    is_archived: boolean;
    last_message_timestamp: string;
    title: string;
    user_id: number;
}

interface MessageInDb {
    chat_id: number;
    inserted_at: string;
    message_id: number;
    text: string;
    user_id: number | null;
}
