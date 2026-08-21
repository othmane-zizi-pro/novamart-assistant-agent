"""FastAPI application entry point."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="NovaMart Assistant")

    @app.get("/api/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
