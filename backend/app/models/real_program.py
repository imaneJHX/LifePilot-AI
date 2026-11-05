"""Independent staging table; its explorer never feeds demonstration recommendations."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RealProgramRecord(Base):
    __tablename__ = "real_university_programs"

    id: Mapped[str] = mapped_column(String(29), primary_key=True)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recommendation_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
