from shellix.cli.commands import app
from dotenv import load_dotenv



def main() -> None:
    """Application entry point."""

    load_dotenv()
    app()


if __name__ == "__main__":
    main()