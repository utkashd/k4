import uvicorn
from cyris_api_server import app


def main() -> None:
    uvicorn.run(app, port=8000)


if __name__ == "__main__":
    main()
