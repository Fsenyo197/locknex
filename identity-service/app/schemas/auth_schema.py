from pydantic import BaseModel, ConfigDict
from app.schemas.user_schema import UserResponse

class LoginResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str

    model_config = ConfigDict(from_attributes=True)
