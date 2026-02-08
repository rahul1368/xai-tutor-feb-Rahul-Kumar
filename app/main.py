from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.rate_limiter import limiter
from app.routes import health_router, items_router, invoices_router

app = FastAPI(title="Backend Exercise API", version="1.0.0")

# Register Rate Limiter Exception Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register routers
app.include_router(health_router)
app.include_router(items_router)
app.include_router(invoices_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
