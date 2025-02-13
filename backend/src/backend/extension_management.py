import re
from pathlib import Path
from typing import Annotated

import asyncpg  # type: ignore[import-untyped,unused-ignore]
from backend_commons import PostgresTableManager
from cyris_logger import log
from extendables import (
    GetCompleteChatDefaultImplementation,
    plugin_manager,
    replace_plugin_with_external_plugin,
)
from fastapi import HTTPException, status
from git import Repo
from pydantic import AfterValidator, BaseModel, Json, RootModel

git_url_regexes = [
    re.compile(regex_str)
    for regex_str in (
        # these are raw strings, `/` doesn't need escaping here
        r"^(\w+://)(.+@)*([\w\d\.-]+)(:[\d]+){0,1}/*(.*)$",
        r"^file://(.*)$",
        r"^(.+@)*([\w\d\.-]+):(.*)$",
        r"^[~|/]?[\w\d/-]*\.git[/]?$",
    )
]


def validate_git_repo_url(value: str) -> str:
    # took these 3 regexes somewhat blindly from https://stackoverflow.com/a/2514986
    if not any(git_url_regex.match(value) for git_url_regex in git_url_regexes):
        raise ValueError(
            f"Invalid git repository URL: {value=}. There's a good chance this error is wrong, please open an issue if you believe that to be so.",
        )
    return value


class GitUrl(RootModel[str]):
    root: Annotated[str, AfterValidator(validate_git_repo_url)]

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
        self, connection_pool: asyncpg.Pool
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
            extensions = await connection.fetch(
                "SELECT local_path FROM extensions LIMIT 10"
            )
            return [ExtensionInDb(**extension) for extension in extensions]

    async def download_extension_to_file_system_if_necessary_and_get_local_path(
        self, git_repo_url: GitUrl
    ) -> Path:
        cyris_extensions_directory_path = Path.home().joinpath(".cyris_extensions/")
        cyris_extensions_directory_path.mkdir(
            exist_ok=True
        )  # create the dir if it doesn't already exist
        repo_name = str(git_repo_url).split("/")[-1]
        local_path_of_extension = cyris_extensions_directory_path.joinpath(repo_name)
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
        async with self.get_transaction_connection() as connection:
            query_result = await connection.fetchrow(
                "SELECT * FROM extensions WHERE extension_id=$1", extension_id
            )
            extension_in_db = ExtensionInDb(**query_result)
            await connection.execute(
                "DELETE FROM extensions WHERE extension_id=$1", extension_id
            )
            log.info(
                f"Would have deleted this directory: {extension_in_db.local_path=}"
            )
            # extension_in_db.local_path.rmdir()
            return extension_in_db


def test() -> None:
    # TODO move this to a test file
    tests = [
        "ssh://user@host.xz:port/path/to/repo.git/",
        "ssh://user@host.xz/path/to/repo.git/",
        "ssh://host.xz:port/path/to/repo.git/",
        "ssh://host.xz/path/to/repo.git/",
        "ssh://user@host.xz/path/to/repo.git/",
        "ssh://host.xz/path/to/repo.git/",
        "ssh://user@host.xz/~user/path/to/repo.git/",
        "ssh://host.xz/~user/path/to/repo.git/",
        "ssh://user@host.xz/~/path/to/repo.git",
        "ssh://host.xz/~/path/to/repo.git",
        "user@host.xz:/path/to/repo.git/",
        "host.xz:/path/to/repo.git/",
        "user@host.xz:~user/path/to/repo.git/",
        "host.xz:~user/path/to/repo.git/",
        "user@host.xz:path/to/repo.git",
        "host.xz:path/to/repo.git",
        "rsync://host.xz/path/to/repo.git/",
        "git://host.xz/path/to/repo.git/",
        "git://host.xz/~user/path/to/repo.git/",
        "http://host.xz/path/to/repo.git/",
        "https://host.xz/path/to/repo.git/",
        "/path/to/repo.git/",
        "path/to/repo.git/",
        "~/path/to/repo.git",
        "file:///path/to/repo.git/",
        "file://~/path/to/repo.git/",
    ]

    for test in tests:
        GitUrl(test)


if __name__ == "__main__":
    test()
