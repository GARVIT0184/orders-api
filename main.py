from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL = "24f2006741@ds.study.iitm.ac.in"
TOTAL_ORDERS = 46
RATE_LIMIT = 16
WINDOW = 10

orders = []
idempotency_store = {}
clients = {}

# -----------------------------
# Rate limit helper
# -----------------------------
def check_rate_limit(client_id: str):
    now = time.time()

    if client_id not in clients:
        clients[client_id] = []

    clients[client_id] = [
        t for t in clients[client_id]
        if now - t < WINDOW
    ]

    if len(clients[client_id]) >= RATE_LIMIT:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )
        response.headers["Retry-After"] = "10"
        return response

    clients[client_id].append(now)
    return None


# -----------------------------
# POST /orders
# -----------------------------
@app.post("/orders", status_code=201)
async def create_order(
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):

    client_id = request.headers.get("X-Client-ID", "anonymous")

    limited = check_rate_limit(client_id)
    if limited:
        return limited

    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": len(idempotency_store) + 1,
        "email": EMAIL
    }

    idempotency_store[idempotency_key] = order

    return order


# -----------------------------
# GET /orders
# -----------------------------
@app.get("/orders")
async def list_orders(
    request: Request,
    limit: int = 10,
    cursor: Optional[str] = None,
):

    client_id = request.headers.get("X-Client-ID", "anonymous")

    limited = check_rate_limit(client_id)
    if limited:
        return limited

    start = int(cursor) if cursor else 1
    end = min(start + limit - 1, TOTAL_ORDERS)

    items = [{"id": i} for i in range(start, end + 1)]

    next_cursor = None
    if end < TOTAL_ORDERS:
        next_cursor = str(end + 1)

    return {
        "items": items,
        "next_cursor": next_cursor,
    }
