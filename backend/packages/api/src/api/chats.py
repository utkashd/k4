from typing import Literal

from extensibles import ParamsForAlreadyExistingChat, get_complete_chat_for_llm
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from k4.llm_provider_management import K4LlmProvider
from pydantic import BaseModel

from k4 import ChatMessage

from ._dependencies import get_current_active_non_admin_user, k4, messages_manager
from .message_management import Chat, ChatPreview
from .user_management import NonAdminUser

chats_router = APIRouter()


class LlmStreamingStart(BaseModel):
    chat_id: int
    chunk_type: Literal["msg_start"] = "msg_start"


class LlmStreamingChunk(BaseModel):
    chat_id: int
    chunk_type: Literal["text"] = "text"
    chunk: str


@chats_router.get("/chat")
async def get_chat_by_chat_id(
    chat_id: int,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> Chat:
    if not await messages_manager.does_user_own_this_chat(
        user_id=current_user.user_id, chat_id=chat_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't access a different user's chats.",
        )
    return await messages_manager.get_chat(chat_id=chat_id)


@chats_router.get("/chat_previews")
async def get_chat_previews(
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> list[ChatPreview]:
    return await messages_manager.get_user_chat_previews(current_user.user_id, 20)


@chats_router.delete("/chat")
async def delete_chat(
    chat_id: int,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> None:
    if not await messages_manager.does_user_own_this_chat(
        user_id=current_user.user_id, chat_id=chat_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't delete someone else's chat.",
        )
    await messages_manager.delete_chat(chat_id=chat_id)


class CreateNewChatRequestBody(BaseModel):
    message: str
    llm_provider: K4LlmProvider
    llm_model_name: str


@chats_router.post("/chat")
async def create_new_chat_with_message_stream(
    create_new_chat_request_body: CreateNewChatRequestBody,
    background_tasks: BackgroundTasks,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> StreamingResponse:
    complete_chat = await get_complete_chat_for_llm(
        new_message_from_user=create_new_chat_request_body.message,
        existing_chat_params=None,
    )
    will_ask_succeed, failure_detail = k4.will_ask_succeed_with_detail(
        complete_chat=complete_chat,
        llm_provider=create_new_chat_request_body.llm_provider,
        model=create_new_chat_request_body.llm_model_name,
    )
    if not will_ask_succeed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=failure_detail,
        )
    chat_in_db = await messages_manager.create_new_chat(
        user_id=current_user.user_id, title=""
    )
    return await get_and_stream_and_store_k4_response(
        user_id=current_user.user_id,
        chat_id=chat_in_db.chat_id,
        complete_chat=complete_chat,
        llm_model_name=create_new_chat_request_body.llm_model_name,
        background_tasks=background_tasks,
    )


class SendMessageRequestBody(CreateNewChatRequestBody):
    chat_id: int


@chats_router.post("/message")
async def send_message_to_k4_stream(
    send_message_request_body: SendMessageRequestBody,
    background_tasks: BackgroundTasks,
    current_user: NonAdminUser = Depends(get_current_active_non_admin_user),
) -> StreamingResponse:
    chat_in_db = await messages_manager.get_chat_in_db(
        send_message_request_body.chat_id
    )
    if current_user.user_id != chat_in_db.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can't access another user's chats.",
        )

    complete_chat = await get_complete_chat_for_llm(
        new_message_from_user=send_message_request_body.message,
        existing_chat_params=ParamsForAlreadyExistingChat(
            chat_id=send_message_request_body.chat_id,
            get_messages_of_chat=messages_manager.get_messages_of_chat,
        ),
    )

    will_ask_succeed, failure_detail = k4.will_ask_succeed_with_detail(
        complete_chat=complete_chat,
        llm_provider=send_message_request_body.llm_provider,
        model=send_message_request_body.llm_model_name,
    )
    if not will_ask_succeed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=failure_detail
        )

    return await get_and_stream_and_store_k4_response(
        user_id=current_user.user_id,
        chat_id=send_message_request_body.chat_id,
        complete_chat=complete_chat,
        llm_model_name=send_message_request_body.llm_model_name,
        background_tasks=background_tasks,
    )


async def save_k4_response_to_db(chat_id: int, all_k4_responses: list[str]) -> None:
    k4_response: str = "".join(all_k4_responses)
    await messages_manager.save_k4_message_to_db(chat_id=chat_id, text=k4_response)


async def get_and_stream_and_store_k4_response(
    user_id: int,
    chat_id: int,
    complete_chat: list[ChatMessage],
    llm_model_name: str,
    background_tasks: BackgroundTasks,
) -> StreamingResponse:
    text = complete_chat[-1].get("unmodified_content")
    if not text:
        text = complete_chat[-1]["content"]
    user_message = await messages_manager.save_client_message_to_db(
        chat_id=chat_id, user_id=user_id, text=text
    )

    all_k4_response_tokens: list[str] = []

    def _format_pydantic_instance_for_stream_response(
        pydantic_instance: BaseModel,
    ) -> str:
        return f"{pydantic_instance.model_dump_json()}\n"

    async def stream_response_and_async_write_to_db():  # type: ignore[no-untyped-def]
        yield _format_pydantic_instance_for_stream_response(user_message)
        yield _format_pydantic_instance_for_stream_response(
            LlmStreamingStart(chat_id=chat_id)
        )
        async for response_token in k4.ask_stream(
            messages=complete_chat,
            model=llm_model_name,
        ):
            if isinstance(response_token, str):
                # ignore the final chunk, which is `None`
                yield _format_pydantic_instance_for_stream_response(
                    LlmStreamingChunk(chunk=response_token, chat_id=chat_id)
                )
                all_k4_response_tokens.append(response_token)

    background_tasks.add_task(
        # I believe this is guaranteed to run AFTER this the generator is consumed. We
        # need that guarantee, otherwise `all_k4_responses` is incomplete.
        # https://fastapi.tiangolo.com/tutorial/background-tasks/
        save_k4_response_to_db,
        chat_id=chat_id,
        all_k4_responses=all_k4_response_tokens,
    )
    return StreamingResponse(
        stream_response_and_async_write_to_db(),  # type: ignore[no-untyped-call]
        media_type="text/event-stream",
    )
