"""User management routes — admin only for create/list, any user for /me."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.models import User
from backend.auth import hash_password
from backend.deps import get_db_session, get_current_user, require_admin
from backend.schemas import UserCreate, UserOut

router = APIRouter()


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=List[UserOut])
def list_users(
    session: Session = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    return session.query(User).all()


@router.post("/", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    session: Session = Depends(get_db_session),
    _: User = Depends(require_admin),
):
    if session.query(User).filter_by(username=body.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user
