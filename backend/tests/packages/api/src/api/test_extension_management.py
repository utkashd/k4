from api.extension_management import is_valid_git_repo_url


def test_is_valid_git_repo_url() -> None:
    valid_git_repos = [
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

    for git_repo in valid_git_repos:
        assert is_valid_git_repo_url(git_repo)

    assert not is_valid_git_repo_url("")
