from __future__ import annotations


def detect_priority_questions(text: str) -> tuple[str, ...]:
    seen: set[str] = set()
    questions: list[str] = []

    for line in text.splitlines():
        clean = line.strip(" -\t")
        if not clean.endswith("?"):
            continue

        key = clean.casefold()
        if key not in seen:
            seen.add(key)
            questions.append(clean)

    return tuple(questions)
