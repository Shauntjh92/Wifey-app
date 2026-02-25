from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SearchRequest, SearchResponse
from ..services.store_matcher import match_and_search

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search_malls(req: SearchRequest, db: Session = Depends(get_db)):
    if not req.stores:
        raise HTTPException(status_code=400, detail="Provide at least one store name")
    return match_and_search(db, req.stores)
