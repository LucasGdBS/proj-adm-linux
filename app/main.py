from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import os

app = FastAPI(title="Infra Demo API")

Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app)


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=3)


@app.on_event("startup")
def create_table():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id   SERIAL PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
        conn.commit()
    finally:
        conn.close()


class ItemIn(BaseModel):
    name: str


class ItemOut(BaseModel):
    id: int
    name: str


@app.get("/")
def root():
    return {"message": "Hello from FastAPI!", "instance": os.environ.get("HOSTNAME", "unknown")}


@app.get("/health")
def health():
    try:
        conn = get_conn()
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "ok", "db": db_status}


@app.get("/items", response_model=list[ItemOut])
def list_items():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, name FROM items ORDER BY id")
            return cur.fetchall()
    finally:
        conn.close()


@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(item: ItemIn):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO items (name) VALUES (%s) RETURNING id, name",
                (item.name,),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
