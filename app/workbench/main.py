"""HTTP entry point: the API routes, then the screens in app/static/."""

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from workbench.config import Settings, load_settings

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class NoCacheStaticFiles(StaticFiles):
    """Makes the browser revalidate each file, so an edited file never shows stale."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Character Consistency Workbench")
    app.state.settings = settings

    @app.get("/api/health")
    def health() -> dict:
        # Says whether a key is set, never the key itself.
        return {
            "status": "ok",
            "provider": settings.workbench_provider,
            "key_set": bool(settings.gemini_api_key.get_secret_value()),
        }

    # Mounted last, so the API routes above win over file paths.
    app.mount("/", NoCacheStaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


def main() -> None:
    settings = load_settings()
    # One process and one worker.
    uvicorn.run(create_app(settings), host=settings.workbench_host, port=settings.workbench_port)


if __name__ == "__main__":
    main()
