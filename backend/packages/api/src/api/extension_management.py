import re
from pathlib import Path
from typing import Annotated

import asyncpg
from backend_commons import PostgresTableManager
from extensibles import (
    GetCompleteChatDefaultImplementation,
    plugin_manager,
    replace_plugin_with_external_plugin,
)
from fastapi import HTTPException, status
from git import Repo
from k4_logger import log
from pydantic import AfterValidator, BaseModel, Json, RootModel


def git_repo_url_validator(value: str) -> str:
    if not is_valid_git_repo_url(git_url=value):
        raise ValueError(
            f"Invalid git repository URL: {value=}. There's a good chance this error is wrong, please open an issue if you believe that to be so.",
        )
    return value


def is_valid_git_repo_url(git_url: str) -> bool:
    git_url_regexes = [
        re.compile(regex_str)
        for regex_str in (
            # took these regexes somewhat blindly from https://stackoverflow.com/a/2514986
            # these are raw strings, `/` doesn't need escaping here
            r"^file://(.*)$",
            r"^(\w+://)(.+@)*([\w\d\.-]+)(:[\d]+){0,1}/*(.*)$",
            r"^(.+@)*([\w\d\.-]+):(.*)$",
            r"^[~|/]?[\w\d/-]*\.git[/]?$",
        )
    ]
    return any(git_url_regex.match(git_url) for git_url_regex in git_url_regexes)


class GitUrl(RootModel[str]):
    root: Annotated[str, AfterValidator(git_repo_url_validator)]

    def __str__(self) -> str:
        return self.root


class ExtensionMetadata(BaseModel):
    installed_version: str
    git_repo_url: GitUrl


class ExtensionInDb(BaseModel):
    extension_id: int
    name: str
    local_path: Path
    metadata: Json[ExtensionMetadata]


class ExtensionsManager(PostgresTableManager):
    @property
    def create_table_queries(self) -> list[str]:
        return [
            """
        CREATE TABLE IF NOT EXISTS extensions (
            extension_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            local_path VARCHAR(255) NOT NULL UNIQUE,
            metadata JSONB NOT NULL
        )
            """
        ]

    @property
    def create_indexes_queries(self) -> list[str]:
        return []

    async def set_connection_pool_and_start(
        self, connection_pool: "asyncpg.Pool[asyncpg.Record]"
    ) -> None:
        await super().set_connection_pool_and_start(connection_pool)
        plugin_manager.register(
            GetCompleteChatDefaultImplementation(), name="get_complete_chat_for_llm"
        )
        installed_extensions = await self.get_installed_extensions()
        if installed_extensions:
            replace_plugin_with_external_plugin(
                "get_complete_chat_for_llm", installed_extensions[-1].local_path
            )

    async def get_installed_extensions(self) -> list[ExtensionInDb]:
        async with self.get_connection() as connection:
            extensions = await connection.fetch("SELECT * FROM extensions LIMIT 10")
            return [ExtensionInDb(**extension) for extension in extensions]

    async def download_extension_to_file_system_if_necessary_and_get_local_path(
        self, git_repo_url: GitUrl
    ) -> Path:
        k4_extensions_directory_path = Path.home().joinpath(".k4/extensions")
        k4_extensions_directory_path.mkdir(
            exist_ok=True,
            parents=True,
        )  # create the directories if they don't already exist
        repo_name = str(git_repo_url).split("/")[-1]
        local_path_of_extension = k4_extensions_directory_path.joinpath(repo_name)
        if local_path_of_extension.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An extension with {repo_name=} is already downloaded.",
            )
        Repo.clone_from(str(git_repo_url), local_path_of_extension)
        return local_path_of_extension

    async def add_extension(self, git_repo_url: GitUrl) -> ExtensionInDb:
        local_path_of_extension = await self.download_extension_to_file_system_if_necessary_and_get_local_path(
            git_repo_url
        )
        try:
            async with self.get_transaction_connection() as connection:
                new_row = await connection.fetchrow(
                    "INSERT INTO extensions (name, local_path, metadata) VALUES ($1, $2, $3) RETURNING *",
                    str(git_repo_url),
                    str(local_path_of_extension),
                    ExtensionMetadata(
                        installed_version="0.0.1", git_repo_url=git_repo_url
                    ).model_dump_json(),
                )
                if not new_row:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Unexpectedly could not add extension to the database.",
                    )
                replace_plugin_with_external_plugin(
                    "get_complete_chat_for_llm", local_path_of_extension
                )
                return ExtensionInDb(**new_row)
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already added this extension.",
            )

    async def remove_extension(self, extension_id: int) -> ExtensionInDb:
        # TODO this method is not completely implemented!!
        async with self.get_transaction_connection() as connection:
            query_result = await connection.fetchrow(
                "SELECT * FROM extensions WHERE extension_id=$1", extension_id
            )
            if not query_result:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No extension with {extension_id=} was found in the database.",
                )
            extension_in_db = ExtensionInDb(**query_result)
            await connection.execute(
                "DELETE FROM extensions WHERE extension_id=$1", extension_id
            )
            log.info(
                f"Would have deleted this directory: {extension_in_db.local_path=}"
            )
            # extension_in_db.local_path.rmdir()
            # remove the plugin and replace with the default function
            return extension_in_db
