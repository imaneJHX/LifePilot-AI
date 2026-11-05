from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.profile import Profile
from app.schemas.contracts import ProfileInput, ProfileOut


def serialize(profile: Profile) -> ProfileOut:
    return ProfileOut(**profile.data, id=profile.id, created_at=profile.created_at)


class ProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: ProfileInput) -> ProfileOut:
        profile = Profile(data=data.model_dump(mode="json"))
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return serialize(profile)

    def get(self, profile_id: UUID) -> ProfileOut:
        profile = self.session.get(Profile, str(profile_id))
        if profile is None:
            raise AppError("profile_not_found", "Profile not found. Create a new profile.", 404)
        return serialize(profile)
