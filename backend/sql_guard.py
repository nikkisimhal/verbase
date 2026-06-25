
import re
import sqlparse

BLOCKED_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate", "grant",
    "revoke", "create", "replace", "attach", "detach", "pragma", "vacuum",
    "exec", "execute", "call",
}


class UnsafeQueryError(Exception):
    pass


def validate_and_cap(sql: str, max_rows: int = 200) -> str:
    sql = sql.strip().rstrip(";")

    statements = [s for s in sqlparse.parse(sql) if s.tokens]
    if len(statements) != 1:
        raise UnsafeQueryError("Only a single SQL statement is allowed.")

    stmt = statements[0]
    stmt_type = stmt.get_type()  # e.g. SELECT, INSERT, UNKNOWN

    lowered = sql.lower()
    first_word = lowered.split(None, 1)[0] if lowered.split() else ""

    is_select = stmt_type == "SELECT" or first_word in ("select", "with")
    if not is_select:
        raise UnsafeQueryError(
            f"Only read-only SELECT queries are allowed. Got: {stmt_type or first_word}"
        )

    tokens_lower = re.findall(r"[a-zA-Z_]+", lowered)
    hit = BLOCKED_KEYWORDS.intersection(tokens_lower)
    if hit:
        raise UnsafeQueryError(f"Query contains a disallowed keyword: {', '.join(hit)}")

    if not re.search(r"\blimit\s+\d+", lowered):
        sql = f"{sql}\nLIMIT {max_rows}"

    return sql
