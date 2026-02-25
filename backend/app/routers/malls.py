from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Mall, Store, MallStore
from ..schemas import MallOut, MallDetail, MallStoreEntry, StoreOut

router = APIRouter(prefix="/api", tags=["malls"])


@router.get("/malls", response_model=list[MallOut])
def list_malls(db: Session = Depends(get_db)):
    return db.query(Mall).order_by(Mall.name).all()


@router.get("/malls/{mall_id}", response_model=MallDetail)
def get_mall(mall_id: UUID, db: Session = Depends(get_db)):
    mall = db.query(Mall).filter(Mall.id == mall_id).first()
    if not mall:
        raise HTTPException(status_code=404, detail="Mall not found")

    store_entries = []
    for ms in mall.mall_stores:
        store_entries.append(MallStoreEntry(
            store_id=ms.store.id,
            store_name=ms.store.name,
            category=ms.store.category,
            floor=ms.floor,
            unit_number=ms.unit_number,
        ))

    return MallDetail(
        id=mall.id,
        name=mall.name,
        address=mall.address,
        region=mall.region,
        website=mall.website,
        last_updated=mall.last_updated,
        stores=store_entries,
    )


@router.get("/stores", response_model=list[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).order_by(Store.name).all()
