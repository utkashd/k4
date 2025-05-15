export interface ChatPreview {
    chat_in_db: ChatInDb;
    most_recent_message_in_db: MessageInDb;
}

export interface ChatInDb {
    chat_id: number;
    is_archived: boolean;
    last_message_timestamp: string;
    title: string;
    user_id: number;
}

export interface MessageInDb {
    chat_id: number;
    inserted_at: string;
    message_id: number;
    text: string;
    user_id: number | null;
}

export interface Chat {
    chat_in_db: ChatInDb;
    messages: MessageInDb[];
}

export interface LlmStreamingStart {
    chat_id: number;
    chunk_type: "msg_start";
}

export interface LlmStreamingChunk {
    chat_id: number;
    chunk_type: "text";
    chunk: string;
}
