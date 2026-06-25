# Verbase

Ask your database a question in plain English (or Hinglish) and get back the answer — plus the actual SQL it ran.

I built this because I kept seeing the same problem: one person on a team knows SQL, and everyone else just wants an answer from the database *right now*. Verbase sits in between — you type a question, it writes the query, runs it, and shows you the result.

> Example: type `"cancelled orders ka percentage kitna hai"` and it'll write the SQL, run it, and give you the number.

It's not hardcoded to one demo table either. Verbase reads the schema straight from whatever database it's connected to, so if you point it at a different Postgres/SQLite database, it just adapts — no code changes.

## How it works

```
 ┌─────────────┐      question       ┌──────────────────┐
 │  Frontend   │ ──────────────────▶ │   FastAPI backend │
 │ (vanilla JS)│                     │                    │
 └─────────────┘ ◀────────────────── └────────┬───────────┘
   SQL + results                              │
                                               ▼
                                   ┌──────────────────────┐
                                   │ schema_introspector.py│  ← reads live DB schema
                                   └──────────┬────────────┘
                                              ▼
                                   ┌──────────────────────┐
                                   │      nl2sql.py        │  ← Groq API (free), schema-grounded
                                   └──────────┬────────────┘
                                              ▼
                                   ┌──────────────────────┐
                                   │      sql_guard.py      │  ← blocks anything but SELECT
                                   └──────────┬────────────┘
                                              ▼
                                       executes on DB,
                                       returns rows
```

A few decisions I made on purpose:

- **The model always sees the real schema first.** Every time it generates a query, it's looking at the actual table/column names — so it can't make up a column that doesn't exist.
- **SQL safety isn't just one check, it's three.** Before anything touches the database: it confirms the statement is a `SELECT`, runs it past a keyword blocklist (catches `DROP`/`DELETE`/`INSERT` even buried in a subquery), and caps the row count so nothing returns an unbounded result.
- **`schema_introspector.py` doesn't know anything about any specific table.** Change the `DATABASE_URL` and the rest of the app just works — that was the whole point of building it this way.

## Stack

- **Backend:** FastAPI, SQLAlchemy, Groq API (free tier, Llama 3.3 70B)
- **Frontend:** plain HTML/CSS/JS — no build step, just open the file
- **Database:** SQLite by default (seeds itself with demo data), Postgres/MySQL also work, just swap one env var

## Running it

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your free GROQ_API_KEY from console.groq.com/keys
uvicorn main:app --reload --port 8000
```

Then open `frontend/index.html` in a browser (or serve it however you want). It auto-creates a demo e-commerce database (customers, products, orders, order_items) on first run, so there's nothing extra to set up.

Want to point it at your own data? Just change `DATABASE_URL` in `.env`. That's it.

## What I left out, on purpose

- **No write operations.** This is read-only by design — `sql_guard.py` rejects anything that isn't a `SELECT`. Letting a non-technical person *modify* production data through natural language is a much harder safety problem, and not one I wanted to solve in this project.
- **No query history/caching yet.** Easy enough to add later, but I wanted the core NL-to-SQL pipeline to be the focus for now.

## Resume bullets, if you need them

- Built an LLM-powered natural-language-to-SQL engine using schema-aware prompting, letting non-technical users safely query a relational database.
- Designed a three-layer SQL safety guard (statement-type validation, keyword blocklisting, row capping) to enforce read-only access on AI-generated queries.
- Implemented dynamic schema introspection so the backend works against any connected database without code changes.

---

*Built by Divya — a project exploring how to make LLM-to-database interfaces safe.*