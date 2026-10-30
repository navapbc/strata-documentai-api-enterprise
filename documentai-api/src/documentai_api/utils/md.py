def to_table(headers: list[str], rows: list[list[str]]) -> str:
    """Return a markdown table string for the given headers and rows."""
    header = "| " + " | ".join(headers) + " |"
    sep = "|---" * len(headers) + "|"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, sep, *body])
