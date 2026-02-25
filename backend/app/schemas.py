from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# --- Store ---

class StoreBase(BaseModel):
    name: str
    category: Optional[str] = None
    normalized_name: str


class StoreOut(BaseModel):
    id: UUID
    name: str
    category: Optional[str] = None
    normalized_name: str

    model_config = {"from_attributes": True}


# --- Mall ---

class MallBase(BaseModel):
    name: str
    address: Optional[str] = None
    region: Optional[str] = None
    website: Optional[str] = None


class MallOut(BaseModel):
    id: UUID
    name: str
    address: Optional[str] = None
    region: Optional[str] = None
    website: Optional[str] = None
    last_updated: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MallStoreEntry(BaseModel):
    store_id: UUID
    store_name: str
    category: Optional[str] = None
    floor: Optional[str] = None
    unit_number: Optional[str] = None

    model_config = {"from_attributes": True}


class MallDetail(MallOut):
    stores: list[MallStoreEntry] = []


# --- Search ---

class SearchRequest(BaseModel):
    stores: list[str]


class MatchedStore(BaseModel):
    requested: str
    matched_id: Optional[UUID] = None
    matched_name: Optional[str] = None
    found: bool = False


class MallSearchResult(BaseModel):
    mall: MallOut
    matched_count: int
    total_requested: int
    matched_stores: list[MatchedStore]


class SearchResponse(BaseModel):
    results: list[MallSearchResult]
    unmatched_stores: list[str]


# --- Data Gathering ---

class GatherResponse(BaseModel):
    message: str
    job_id: str


class StatusResponse(BaseModel):
    job_id: str
    status: str  # "idle" | "running" | "done" | "error"
    total_malls: int
    completed_malls: int
    current_mall: Optional[str] = None
    error: Optional[str] = None
