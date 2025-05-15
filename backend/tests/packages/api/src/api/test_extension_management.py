from api.extension_management import is_valid_git_repo_url


def test_is_valid_git_repo_url() -> None:
    assert not is_valid_git_repo_url("")
