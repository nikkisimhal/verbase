
import os
import re

from groq import Groq

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a SQL generation engine embedded inside a product called Verbase.
You will be given the exact schema of a SQL database and a user's question written in plain
English or Hinglish. Your only job is to output ONE valid, read-only SQL SELECT statement that
answers the question, using only the tables and columns provided.

Rules:
- Output SQL only. No explanation, no markdown code fences, no comments.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, or any statement other than SELECT.
- Only reference tables and columns that appear in the schema below.
- If the question is ambiguous, make the most reasonable assumption and proceed.
- If the question cannot be answered with the given schema, output exactly: NO_QUERY_POSSIBLE

Schema:
{schema}
"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```sql\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text)
    return text.strip()


def generate_sql(question: str, schema_block: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(schema=schema_block)},
            {"role": "user", "content": question},
        ],
    )

    raw = response.choices[0].message.content or ""
    sql = _strip_code_fences(raw)

    if sql.strip().upper() == "NO_QUERY_POSSIBLE":
        raise ValueError(
            "Verbase couldn't map that question to the current schema. "
            "Try rephrasing, or ask what data is available."
        )

    return sql
