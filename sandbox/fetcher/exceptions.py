"""Custom exceptions for the fetch engine."""


class FetchError(Exception):
    """Wraps all fetch-related failures, optionally preserving the original exception."""

    def __init__(self, message: str, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original

    def __str__(self) -> str:
        base = super().__str__()
        if self.original is not None:
            return f"{base} [caused by: {type(self.original).__name__}: {self.original}]"
        return base


if __name__ == "__main__":
    err = FetchError("a connection timed out")
    print(f"plain → {err}")

    try:
        raise ConnectionError("refused")
    except ConnectionError as e:
        wrapped = FetchError("fetch failed", original=e)
        print(f"wrapped → {wrapped}")
