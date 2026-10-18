import re


def strip_markup(value: str) -> str:
    return re.sub(r"\[[ぁ-ゖァ-ヺー\s]+\]", "", value).replace("{{", "").replace("}}", "")


def search_text(content: list[dict]) -> str:
    def walk(value):
        if isinstance(value, str):
            yield strip_markup(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key != "type":
                    yield from walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)

    return " ".join(walk(content))
