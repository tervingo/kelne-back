from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from db import roots_collection, words_collection
from models.root import RootCreate, RootUpdate, RootListItem

router = APIRouter(prefix="/api/roots", tags=["roots"])


def serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


def serialize_word(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


async def populate_words(doc: dict) -> dict:
    """Replace word ID strings in each base's derivedWords with full word documents.
    Entries that are not valid ID strings (e.g. legacy inline dicts) are silently dropped.
    """
    all_ids = [
        ObjectId(wid)
        for base in doc.get("bases", [])
        for wid in base.get("derivedWords", [])
        if isinstance(wid, str) and ObjectId.is_valid(wid)
    ]
    words_map: dict[str, dict] = {}
    if all_ids:
        async for word in words_collection.find({"_id": {"$in": all_ids}}):
            words_map[str(word["_id"])] = serialize_word(word)
    for base in doc.get("bases", []):
        base["derivedWords"] = [
            words_map[wid]
            for wid in base.get("derivedWords", [])
            if isinstance(wid, str) and wid in words_map
        ]
    return doc


@router.get("", response_model=list[RootListItem])
async def list_roots(q: str = Query(default="")):
    query: dict = {}
    if q:
        query = {
            "$or": [
                {"root":             {"$regex": q, "$options": "i"}},
                {"bases.translation": {"$regex": q, "$options": "i"}},
            ]
        }
    cursor = roots_collection.find(query, {"_id": 1, "root": 1, "notes": 1}).sort("root", 1)
    return [serialize(doc) async for doc in cursor]


@router.get("/{root_id}")
async def get_root(root_id: str):
    doc = await roots_collection.find_one({"_id": ObjectId(root_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Raíz no encontrada")
    return await populate_words(serialize(doc))


@router.post("", status_code=201)
async def create_root(data: RootCreate):
    result = await roots_collection.insert_one(data.model_dump(by_alias=True))
    doc = await roots_collection.find_one({"_id": result.inserted_id})
    return await populate_words(serialize(doc))


@router.patch("/{root_id}")
async def update_root(root_id: str, data: RootUpdate):
    update = {k: v for k, v in data.model_dump(by_alias=True, exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    result = await roots_collection.update_one(
        {"_id": ObjectId(root_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Raíz no encontrada")
    doc = await roots_collection.find_one({"_id": ObjectId(root_id)})
    return await populate_words(serialize(doc))


@router.delete("/{root_id}", status_code=204)
async def delete_root(root_id: str):
    doc = await roots_collection.find_one(
        {"_id": ObjectId(root_id)}, {"bases.derivedWords": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Raíz no encontrada")
    # Cascade: borrar todas las palabras asociadas
    word_ids = [
        ObjectId(wid)
        for base in doc.get("bases", [])
        for wid in base.get("derivedWords", [])
        if ObjectId.is_valid(wid)
    ]
    if word_ids:
        await words_collection.delete_many({"_id": {"$in": word_ids}})
    await roots_collection.delete_one({"_id": ObjectId(root_id)})
