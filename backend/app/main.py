"""
Image Editor API — FastAPI entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.blur import router as blur_router

app = FastAPI(
    title="Image Editor API",
    description="Upload an image and receive a blurred copy.",
    version="0.1.0",
)

# Allow the static frontend (any local origin) during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(blur_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
