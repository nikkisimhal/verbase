

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def get_schema_snapshot(engine: Engine) -> dict:
    """Returns a structured, JSON-friendly description of the connected database."""
    inspector = inspect(engine)
    snapshot = {"tables": []}

    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
            })

        pk = inspector.get_pk_constraint(table_name).get("constrained_columns", [])

        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            fks.append({
                "column": fk["constrained_columns"],
                "references_table": fk["referred_table"],
                "references_column": fk["referred_columns"],
            })

        snapshot["tables"].append({
            "name": table_name,
            "columns": columns,
            "primary_key": pk,
            "foreign_keys": fks,
        })

    return snapshot


def schema_to_prompt_block(snapshot: dict) -> str:
    """Renders the schema snapshot as a compact text block for the LLM prompt."""
    lines = []
    for table in snapshot["tables"]:
        col_defs = ", ".join(f"{c['name']} {c['type']}" for c in table["columns"])
        lines.append(f"TABLE {table['name']} ({col_defs})")
        for fk in table["foreign_keys"]:
            lines.append(
                f"  -- {table['name']}.{fk['column'][0]} references "
                f"{fk['references_table']}.{fk['references_column'][0]}"
            )
    return "\n".join(lines)
