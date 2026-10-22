from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.exceptions import AppError
from routers.ai_tutor_interactions import router as ai_tutor_interactions_router
from routers.offline_package import router as offline_package_router
from routers.sync_event import router as sync_event_router
from routers.topic import router as topic_router


app = FastAPI(title="Redu", version="0.1.0")


@app.exception_handler(AppError)
async def app_error_handler(
    request: Request,
    exc: AppError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


app.include_router(ai_tutor_interactions_router)
app.include_router(offline_package_router, prefix="/api/v1")
app.include_router(sync_event_router, prefix="/api/v1")
app.include_router(topic_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
