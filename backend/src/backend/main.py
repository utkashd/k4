import uvicorn
from utils import is_development_environment


def main() -> None:
    uvicorn.run(
        "cyris_api_server:app",
        host="127.0.0.1",  # localhost only, not 0.0.0.0
        port=8000,
        reload=is_development_environment(),
    )


if __name__ == "__main__":
    main()
