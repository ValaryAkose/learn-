from dotenv import load_dotenv
import config  # noqa: F401
from config import settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers.sync_event import router as sync_event_router
from core.exceptions import AppError
from core.security import InvalidToken
from routers.ai_tutor_interactions import router as ai_tutor_interactions_router
from routers.learner_lesson_progress import router as learner_lesson_progress_router
from routers.offline_package import router as offline_package_router
from routers.user import router as user_router
from routers.topic import router as topic_router


load_dotenv()
app = FastAPI(title="Redu", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_tutor_interactions_router)
app.include_router(offline_package_router, prefix="/api/v1")
app.include_router(sync_event_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(topic_router, prefix="/api/v1")
app.include_router(learner_lesson_progress_router, prefix="/api/v1")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(InvalidToken)
async def invalid_token_handler(
    request: Request,
    exc: InvalidToken,
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": "Invalid or expired access token"},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
