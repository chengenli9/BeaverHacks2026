from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.is_shutting_down = False
    try:
        yield
    finally:
        app.state.is_shutting_down = True


app = FastAPI(title="Scenerio Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
