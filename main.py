from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 46

# ----------------------------
# Idempotency
# ----------------------------
orders = []
idempotency_store = {}

# ----------------------------
# Rate limiting
# ----------------------------
RATE_LIMIT = 16
WINDOW = 10
clients = {}

@app.post("/orders", status_code=201)
async def create_order(
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": len(orders) + 1,
        "email": "24f2006741@ds.study.iitm.ac.in"
    }

    orders.append(order)
    idempotency_store[idempotency_key] = order

    return order


@app.get("/orders")
async def get_orders(
    request: Request,
    limit: int = 10,
    cursor: Optional[str] = None
):
    client = request.headers.get("X-Client-ID", "anonymous")
    now = time.time()

    if client not in clients:
        clients[client] = []

    clients[client] = [
        t for t in clients[client]
        if now - t < WINDOW
    ]

    if len(clients[client]) >= RATE_LIMIT:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
        response.headers["Retry-After"] = "10"
        return response

    clients[client].append(now)

    start = int(cursor) if cursor else 1

    end = min(start + limit - 1, TOTAL_ORDERS)

    items = [{"id": i} for i in range(start, end + 1)]

    next_cursor = None

    if end < TOTAL_ORDERS:
        next_cursor = str(end + 1)

    return {
        "items": items,
        "next_cursor": next_cursor
    }
