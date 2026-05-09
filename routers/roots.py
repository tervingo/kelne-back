from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
from db import roots_collection
from models.root import RootCreate, RootUpdate, RootOut

router = APIRouter(prefix="/api/roots", tags=["roots"])


def serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("", response_model=list[RootOut])
async def list_roots(q: str = Query(default="")):
    query = {}
    if q:
        query = {
            "$or": [
                {"root": {"$regex": q, "$options": "i"}},
                {"bases.translation": {"$regex": q, "$options": "i"}},
                {"bases.derived_words.translation": {"$regex": q, "$options": "i"}},
            ]
        }
    cursor = roots_collection.find(query).sort("root", 1)
    return [serialize(doc) async for doc in cursor]


@router.get("/{root_id}", response_model=RootOut)
async def get_root(root_id: str):
    doc = await roots_collection.find_one({"_id": ObjectId(root_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Raíz no encontrada")
    return serialize(doc)


@router.post("", response_model=RootOut, status_code=201)
async def create_root(data: RootCreate):
    result = await roots_collection.insert_one(
        data.model_dump(by_alias=True)
    )
    doc = await roots_collection.find_one({"_id": result.inserted_id})
    return serialize(doc)


@router.patch("/{root_id}", response_model=RootOut)
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
    return serialize(doc)


@router.delete("/{root_id}", status_code=204)
async def delete_root(root_id: str):
    result = await roots_collection.delete_one({"_id": ObjectId(root_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Raíz no encontrada")
