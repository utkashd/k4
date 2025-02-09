import re
from typing import Annotated

import asyncpg  # type: ignore[import-untyped,unused-ignore]
from backend_commons import PostgresTableManager
from fastapi import HTTPException, status
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


class ExtensionMetadata(BaseModel):
    installed_version: str


class GitUrl(RootModel[str]):
    root: Annotated[str, AfterValidator(validate_git_repo_url)]

    def __str__(self) -> str:
        return self.root


class ExtensionInDb(BaseModel):
    extension_id: int
    name: str
    git_repo_url: GitUrl
    metadata: Json[ExtensionMetadata]


class ExtensionsManager(PostgresTableManager):
    @property
    def create_table_queries(self) -> list[str]:
        return [
            """
        CREATE TABLE IF NOT EXISTS extensions (
            extension_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            git_repo_url VARCHAR(255) NOT NULL UNIQUE,
            metadata JSONB NOT NULL
        )
            """
        ]

    @property
    def create_indexes_queries(self) -> list[str]:
        return []

    async def add_extension(self, git_repo_url: GitUrl) -> ExtensionInDb:
        try:
            async with self.get_transaction_connection() as connection:
                new_row = await connection.fetchrow(
                    "INSERT INTO extensions (name, git_repo_url, metadata) VALUES ($1, $2, $3) RETURNING *",
                    str(git_repo_url),
                    str(git_repo_url),
                    ExtensionMetadata(installed_version="0.0.1").model_dump_json(),
                )
                return ExtensionInDb(**new_row)
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


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
