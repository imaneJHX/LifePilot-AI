from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

COUNTRIES = ("Germany", "Netherlands", "France", "Sweden", "Ireland", "Portugal")
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class StudyArea(StrEnum):
    COMPUTER_SCIENCE = "Computer Science"
    DATA_SCIENCE = "Data Science"
    BUSINESS_ANALYTICS = "Business Analytics"
    ENGINEERING = "Engineering"


class Weights(Contract):
    affordability: float = Field(default=0.35, ge=0, le=100)
    academic_fit: float = Field(default=0.30, ge=0, le=100)
    career_outlook: float = Field(default=0.20, ge=0, le=100)
    student_experience: float = Field(default=0.15, ge=0, le=100)

    @model_validator(mode="after")
    def positive_total(self):
        if sum(self.model_dump().values()) <= 0:
            raise ValueError("At least one priority must be greater than zero.")
        return self


class ProfileInput(Contract):
    name: ShortText
    study_area: StudyArea
    gpa: float = Field(ge=0, le=4)
    annual_budget_eur: int = Field(ge=1000, le=200000)
    countries: list[ShortText] = Field(default_factory=list, max_length=6)
    goals: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
    weights: Weights = Field(default_factory=Weights)

    @model_validator(mode="after")
    def valid_countries(self):
        if len(set(self.countries)) != len(self.countries):
            raise ValueError("Countries must be unique.")
        if any(country not in COUNTRIES for country in self.countries):
            raise ValueError(f"Supported demonstration countries: {', '.join(COUNTRIES)}.")
        return self


class ProfileOut(ProfileInput):
    id: UUID
    created_at: datetime


class Program(Contract):
    id: str
    university: str
    program: str
    country: str
    city: str
    study_area: StudyArea
    tuition_eur: int = Field(ge=0)
    living_cost_eur: int = Field(ge=0)
    duration_months: int = Field(gt=0)
    language: str
    curriculum: list[str]
    academic_index: float = Field(ge=0, le=100)
    career_index: float = Field(ge=0, le=100)
    experience_index: float = Field(ge=0, le=100)
    synthetic: Literal[True]
    provenance: str

    @property
    def annual_cost(self) -> int:
        return self.tuition_eur + self.living_cost_eur


class RecommendationRequest(Contract):
    profile_id: UUID
    weights: Weights | None = None
    limit: int = Field(default=6, ge=1, le=20)


class Factor(Contract):
    criterion: str
    label: str
    value: float
    weight: float
    ideal_distance_component: float
    anti_ideal_distance_component: float
    explanation: str


class RankedProgram(Contract):
    rank: int
    program: Program
    score: float = Field(ge=0, le=1)
    annual_cost_eur: int
    budget_remaining_eur: int
    factors: list[Factor]


class RecommendationResponse(Contract):
    results: list[RankedProgram]
    considered: int
    excluded_over_budget: int
    excluded_preferences: int
    weights: dict[str, float]
    methodology: str
    disclaimer: str
    synthetic: Literal[True] = True


class ChatMessage(Contract):
    role: Literal["user", "assistant"]
    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)
    ]

    @model_validator(mode="after")
    def user_message_limit(self):
        if self.role == "user" and len(self.content) > 4000:
            raise ValueError("User messages must not exceed 4,000 characters.")
        return self


class ChatRequest(Contract):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    profile_id: UUID | None = None

    @model_validator(mode="after")
    def ends_with_user(self):
        if self.messages[-1].role != "user":
            raise ValueError("The last message must be from the user.")
        if sum(len(message.content) for message in self.messages) > 24000:
            raise ValueError("Conversation exceeds 24,000 characters. Start a new conversation.")
        return self


class ChatResponse(Contract):
    message: ChatMessage
    model: str
    synthetic_context: Literal[True] = True
