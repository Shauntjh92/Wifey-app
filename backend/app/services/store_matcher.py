"""
Store matching service.
Uses normalized exact matching to resolve user input against DB store names.
"""
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import Mall, Store, MallStore
from ..schemas import MatchedStore, MallSearchResult, MallOut, SearchResponse

logger = logging.getLogger(__name__)


def match_and_search(db: Session, user_stores: list[str]) -> SearchResponse:
    """
    1. Fetch all store names from DB.
    2. Normalized exact match user input → DB store IDs.
    3. SQL query: malls containing matched stores.
    4. Rank and return results.
    """
    # Fetch all stores
    all_stores = db.query(Store).all()
    if not all_stores:
        return SearchResponse(results=[], unmatched_stores=user_stores)

    store_name_map = {s.normalized_name: s for s in all_stores}

    matched: list[MatchedStore] = _fallback_match(db, user_stores, store_name_map)

    found_matches = [m for m in matched if m.found and m.matched_id]
    unmatched = [m.requested for m in matched if not m.found]

    if not found_matches:
        return SearchResponse(results=[], unmatched_stores=unmatched)

    matched_ids = [m.matched_id for m in found_matches]

    # Find malls containing any of the matched stores
    rows = (
        db.query(MallStore.mall_id, MallStore.store_id)
        .filter(MallStore.store_id.in_(matched_ids))
        .all()
    )

    # Group by mall
    mall_hits: dict[UUID, set[UUID]] = {}
    for mall_id, store_id in rows:
        mall_hits.setdefault(mall_id, set()).add(store_id)

    # Sort by number of hits (descending)
    sorted_malls = sorted(mall_hits.items(), key=lambda x: len(x[1]), reverse=True)

    results = []
    for mall_id, hit_store_ids in sorted_malls:
        mall = db.query(Mall).filter(Mall.id == mall_id).first()
        if not mall:
            continue

        mall_matched = [m for m in found_matches if m.matched_id in hit_store_ids]
        mall_unmatched = [
            MatchedStore(requested=m.requested, found=False)
            for m in found_matches if m.matched_id not in hit_store_ids
        ]

        results.append(MallSearchResult(
            mall=MallOut.model_validate(mall),
            matched_count=len(mall_matched),
            total_requested=len(user_stores),
            matched_stores=mall_matched + mall_unmatched,
        ))

    return SearchResponse(results=results, unmatched_stores=unmatched)


def _fallback_match(db: Session, user_stores: list[str], store_name_map: dict) -> list[MatchedStore]:
    """Simple normalized-name exact match fallback."""
    results = []
    for name in user_stores:
        norm = re.sub(r"[^a-z0-9]", "", name.lower())
        store = store_name_map.get(norm)
        if store:
            results.append(MatchedStore(
                requested=name, matched_id=store.id, matched_name=store.name, found=True
            ))
        else:
            results.append(MatchedStore(requested=name, found=False))
    return results
