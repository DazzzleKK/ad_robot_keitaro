from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.pages import router as pages_router
from src.database import create_engine, create_sessionmaker
from src.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    engine = create_engine(app_settings.database_url)
    sessionmaker = create_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = app_settings
    app.state.sessionmaker = sessionmaker

    base_dir = Path(__file__).resolve().parent.parent
    app.mount("/static", StaticFiles(directory=base_dir / "static"), name="static")
    app.include_router(pages_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
