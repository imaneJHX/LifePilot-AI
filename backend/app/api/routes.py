from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.catalog import get_catalog
from app.repositories.profiles import ProfileRepository
from app.repositories.real_catalog import list_real_programs
from app.schemas.contracts import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ProfileInput,
    ProfileOut,
    Program,
    RecommendationRequest,
    RecommendationResponse,
    StudyArea,
)
from app.schemas.real_catalog import RealProgramCatalog
from app.services.ollama import OllamaService, get_ollama_service
from app.services.recommendations import recommend

router = APIRouter(prefix="/api")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "version": "0.1.0", "dataset": "synthetic", "chat": "optional"}


@router.post("/profile", response_model=ProfileOut, status_code=201)
def create_profile(data: ProfileInput, db: Session = Depends(get_db)):
    return ProfileRepository(db).create(data)


@router.get("/profile/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: UUID, db: Session = Depends(get_db)):
    return ProfileRepository(db).get(profile_id)


@router.get("/universities", response_model=list[Program])
def universities(
    search: str = Query(default="", max_length=100),
    country: str | None = Query(default=None, max_length=80),
    study_area: StudyArea | None = None,
):
    query = search.strip().casefold()
    return [
        p
        for p in get_catalog()
        if (not country or p.country == country)
        and (not study_area or p.study_area == study_area)
        and (not query or query in f"{p.university} {p.program} {p.city}".casefold())
    ]


@router.get("/real-programs", response_model=RealProgramCatalog)
def real_programs(
    search: str = Query(default="", max_length=100),
    country: str | None = Query(default=None, max_length=80),
    university: str | None = Query(default=None, max_length=200),
    study_area: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
):
    return list_real_programs(
        db, country=country, university=university, study_area=study_area, search=search
    )


@router.post("/recommendations", response_model=RecommendationResponse)
def recommendations(data: RecommendationRequest, db: Session = Depends(get_db)):
    profile = ProfileRepository(db).get(data.profile_id)
    return recommend(profile, get_catalog(), data.weights or profile.weights, data.limit)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    service: OllamaService = Depends(get_ollama_service),
):
    profile = ProfileRepository(db).get(data.profile_id) if data.profile_id else None
    catalog = [
        p.model_dump(mode="json")
        for p in get_catalog()
        if profile is None or p.study_area == profile.study_area
    ]
    content = await service.chat(data.messages, profile, catalog)
    return ChatResponse(
        message=ChatMessage(role="assistant", content=content), model=service.settings.ollama_model
    )
