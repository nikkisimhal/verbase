
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from nl2sql import generate_sql
from schema_introspector import get_schema_snapshot, schema_to_prompt_block
from sql_guard import UnsafeQueryError, validate_and_cap

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///verbase_demo.db")
MAX_ROWS = int(os.environ.get("MAX_ROWS", "200"))

if DATABASE_URL.startswith("sqlite") and "verbase_demo.db" in DATABASE_URL:
    db_file = DATABASE_URL.split("///")[-1]
    if not os.path.exists(db_file):
        from seed_db import build_demo_db
        build_demo_db(db_file)

_state = {"engine": create_engine(DATABASE_URL)}

app = FastAPI(title="Verbase", description="Ask your database questions in plain English.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class ConnectRequest(BaseModel):
    db_url: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/connect")
def connect_db(req: ConnectRequest):
    """Hot-swap the active database connection without restarting the server."""
    db_url = req.db_url.strip()
    if not db_url:
        raise HTTPException(status_code=400, detail="db_url cannot be empty.")

    try:
        new_engine = create_engine(db_url)
        with new_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _state["engine"] = new_engine
        snapshot = get_schema_snapshot(new_engine)
        return {
            "status": "connected",
            "db_url": db_url,
            "table_count": len(snapshot["tables"]),
            "schema": snapshot,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}")


@app.get("/api/schema")
def schema():
    snapshot = get_schema_snapshot(_state["engine"])
    return snapshot


@app.post("/api/query")
def query(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    engine = _state["engine"]
    snapshot = get_schema_snapshot(engine)
    schema_block = schema_to_prompt_block(snapshot)

    try:
        raw_sql = generate_sql(question, schema_block)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    try:
        safe_sql = validate_and_cap(raw_sql, max_rows=MAX_ROWS)
    except UnsafeQueryError as e:
        raise HTTPException(status_code=400, detail=f"Rejected unsafe query: {e}")

    start = time.time()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(safe_sql))
            columns = list(result.keys())
            rows = [list(r) for r in result.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {e}")

    elapsed_ms = round((time.time() - start) * 1000, 1)

    return {
        "question": question,
        "sql": safe_sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "elapsed_ms": elapsed_ms,
    }
