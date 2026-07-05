from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time

app = FastAPI()

EMAIL = "24f2006741@ds.study.iitm.ac.in"
TOTAL_ORDERS = 46
RATE_LIMIT = 16
WINDOW = 10

# -------------------------
# CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Storage
# -------------------------
orders_by_key = {}
client_requests = {}

# -------------------------
# Rate Limiter
# -------------------------
def rate_limit(request: Request):
    client_id = request.headers.get("X-Client-ID", "anonymous")
    now = time.time()

    if client_id not in client_requests:
        client_requests[client_id] = []

    # Keep only requests in last WINDOW seconds
    client_requests[client_id] = [
        t for t in client_requests[client_id]
        if now - t < WINDOW
    ]

    if len(client_requests[client_id]) >= RATE_LIMIT:
        retry_after = max(
            1,
            int(WINDOW - (now - client_requests[client_id][0]))
        )

        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": str(retry_after)
            },
            content={
                "detail": "Rate limit exceeded"
            }
        )

    client_requests[client_id].append(now)
    return None


# -------------------------
# POST /orders
# -------------------------
@app.post("/orders", status_code=201)
async def create_order(
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):

    limited = rate_limit(request)
    if limited:
        return limited

    if idempotency_key in orders_by_key:
        return orders_by_key[idempotency_key]

    order = {
        "id": len(orders_by_key) + 1,
        "email": EMAIL
    }

    orders_by_key[idempotency_key] = order

    return JSONResponse(
        status_code=201,
        content=order
    )


# -------------------------
# GET /orders
# -------------------------
@app.get("/orders")
async def get_orders(
    request: Request,
    limit: int = 10,
    cursor: Optional[str] = None
):

    limited = rate_limit(request)
    if limited:
        return limited

    if limit < 1:
        limit = 1

    start = 1 if cursor is None else int(cursor)

    if start < 1:
        start = 1

    end = min(start + limit - 1, TOTAL_ORDERS)

    items = [{"id": i} for i in range(start, end + 1)]

    next_cursor = None

    if end < TOTAL_ORDERS:
        next_cursor = str(end + 1)

    return {
        "items": items,
        "next_cursor": next_cursor
    }


# -------------------------
# Root
# -------------------------
@app.get("/")
async def root():
    return {
        "status": "ok"
    }
