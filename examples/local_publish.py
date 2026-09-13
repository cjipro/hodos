"""Minimal runnable demo of hodos.publish.

    python examples/local_publish.py

Writes a small HTML file into ./published/ using LocalAdapter, then
reads it back to prove round-trip. No network, no credentials.
"""
from hodos.publish import get_adapter


def main() -> None:
    adapter = get_adapter({"adapter": "local", "local": {"root_dir": "./published"}})

    ok, message = adapter.publish(
        "demo/index.html",
        "<html><body><h1>Hello from Hodos</h1></body></html>\n",
    )
    print(f"publish ok={ok}: {message}")

    written = (adapter.root / "demo" / "index.html").read_text(encoding="utf-8")
    print("--- content written ---")
    print(written)


if __name__ == "__main__":
    main()
