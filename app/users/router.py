from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories import user_repo
from app.schemas.base import APIResponse
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_my_profile(current_user: User = Depends(get_current_user)):
    user_res = UserResponse.model_validate(current_user)
    return APIResponse(
        success=True,
        message="Profile retrieved successfully",
        data=user_res
    )


@router.patch("/me", response_model=APIResponse[UserResponse])
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    updated_user = await user_repo.update(db, db_obj=current_user, obj_in=data, updated_by=current_user.id)
    await db.commit()
    await db.refresh(updated_user, ["role"])
    
    user_res = UserResponse.model_validate(updated_user)
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=user_res
    )
