"""HTTP entry point: the API routes, then the screens in app/static/.

Routes only call services, like specs, which open their own database connections.
"""

from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from workbench import db, specs
from workbench.config import Settings, load_settings
from workbench.schemas import Character, SpecEdit, SpecView

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class NoCacheStaticFiles(StaticFiles):
    """Makes the browser revalidate each file, so an edited file never shows stale."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def error_response(status: int):
    """A handler that sends a service error's message, which the screens show as is."""

    async def handle(request: Request, error: Exception) -> JSONResponse:
        content = {"detail": str(error)}
        if isinstance(error, specs.SpecInvalid):
            # The draft field to fix, so the Spec editor can move focus to it.
            content["field"] = error.field
        return JSONResponse(status_code=status, content=content)

    return handle


async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
    # FastAPI's default answer echoes the request back. This one only says where it went wrong.
    places = sorted({".".join(str(part) for part in item["loc"][1:]) or "body" for item in error.errors()})
    return JSONResponse(
        status_code=422,
        content={"detail": f"The request has a missing or wrong value at {', '.join(places)}."},
    )


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Character Consistency Workbench")
    app.state.settings = settings

    # Startup work runs here, not in a lifespan handler, because TestClient
    # only runs lifespan inside a with block.
    database = db.Database(settings.workbench_db_path)
    with database.connect() as conn:
        db.migrate(conn)
    specs.seed(database)
    app.state.database = database

    app.add_exception_handler(specs.SpecNotFound, error_response(404))
    app.add_exception_handler(specs.SpecConflict, error_response(409))
    app.add_exception_handler(specs.SpecInvalid, error_response(422))
    app.add_exception_handler(RequestValidationError, invalid_request)

    @app.get("/api/health")
    def health() -> dict:
        # Says whether a key is set, never the key itself.
        return {
            "status": "ok",
            "provider": settings.workbench_provider,
            "key_set": bool(settings.gemini_api_key.get_secret_value()),
        }

    @app.get("/api/characters", response_model=list[Character])
    def characters() -> list[Character]:
        return specs.list_characters(database)

    # Declared before the numbered route, so "latest" is never read as a version.
    @app.get("/api/characters/{slug}/specs/latest", response_model=SpecView)
    def latest_spec(slug: str) -> SpecView:
        return specs.get_spec(database, slug)

    @app.get("/api/characters/{slug}/specs/{version}", response_model=SpecView)
    def spec_version(slug: str, version: int) -> SpecView:
        return specs.get_spec(database, slug, version)

    @app.post("/api/characters/{slug}/specs", response_model=SpecView, status_code=201)
    def save_spec(slug: str, edit: SpecEdit) -> SpecView:
        return specs.save_edit(database, slug, edit)

    # Mounted last, so the API routes above win over file paths.
    app.mount("/", NoCacheStaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


def main() -> None:
    settings = load_settings()
    # One process and one worker.
    uvicorn.run(create_app(settings), host=settings.workbench_host, port=settings.workbench_port)


if __name__ == "__main__":
    main()
