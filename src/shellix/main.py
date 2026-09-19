import os
import platform


def main():
    print()
    print("⚡ Shellix - AI Terminal Assistant")
    print()

    print(f"OS: {platform.system()}")
    print(f"Shell: {os.environ.get('SHELL', 'Unknown')}")
    print(f"Directory: {os.getcwd()}")
    print()

    while True:
        try:
            user_input = input("shellix ❯ ").strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            print(f"\nYou asked: {user_input}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()