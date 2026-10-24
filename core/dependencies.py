from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from sqlalchemy import select


async def get_current_active_user(db: Session = Depends(get_db)) -> User:
    """Temporary local helper until teammate's auth branch is merged."""
    result = db.execute(select(User)).scalars().first()
    return result
