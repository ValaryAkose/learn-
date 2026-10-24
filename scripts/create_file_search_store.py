import json
import os
from pathlib import Path

from google import genai

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STORE_CONFIG = PROJECT_ROOT / "data" / "gemini_file_search_store.json"


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY")
    display_name = os.getenv(
        "GEMINI_FILE_SEARCH_STORE_NAME",
        "redu-curriculum",
    )

    if not api_key:
        raise SystemExit("GEMINI_API_KEY is missing.")

    if STORE_CONFIG.exists():
        saved = json.loads(STORE_CONFIG.read_text(encoding="utf-8"))
        store_name = saved.get("name")

        if store_name:
            client = genai.Client(api_key=api_key)
            try:
                store = client.file_search_stores.get(name=store_name)
                print("Existing File Search Store verified.")
                print("Store name:", store.name)
                return
            finally:
                client.close()

    client = genai.Client(api_key=api_key)

    try:
        store = client.file_search_stores.create(config={"display_name": display_name})

        if not store.name:
            raise RuntimeError("Google did not return a store name.")

        STORE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        STORE_CONFIG.write_text(
            json.dumps(
                {
                    "name": store.name,
                    "display_name": display_name,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        print("File Search Store created successfully.")
        print("Store name:", store.name)
        print("Local configuration:", STORE_CONFIG)

    finally:
        client.close()


if __name__ == "__main__":
    main()
