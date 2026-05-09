from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from bson import ObjectId
from db import words_collection
from models.word import WordCreate, WordUpdate, WordOut, WordCat

router = APIRouter(prefix="/api/words", tags=["words"])


def serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("", response_model=list[WordOut])
async def list_words(
    q:    str = Query(default=""),
    cat:  Optional[WordCat] = Query(default=None),
    raiz: Optional[str]     = Query(default=None),
):
    query: dict = {}
    if q:
        query["$or"] = [
            {"kelne": {"$regex": q, "$options": "i"}},
            {"trad":  {"$regex": q, "$options": "i"}},
        ]
    if cat:
        query["cat"] = cat
    if raiz:
        query["raiz"] = raiz
    cursor = words_collection.find(query).sort("kelne", 1)
    return [serialize(doc) async for doc in cursor]


@router.get("/{word_id}", response_model=WordOut)
async def get_word(word_id: str):
    doc = await words_collection.find_one({"_id": ObjectId(word_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Palabra no encontrada")
    return serialize(doc)


@router.post("", response_model=WordOut, status_code=201)
async def create_word(data: WordCreate):
    result = await words_collection.insert_one(data.model_dump(exclude_none=True))
    doc = await words_collection.find_one({"_id": result.inserted_id})
    return serialize(doc)


@router.patch("/{word_id}", response_model=WordOut)
async def update_word(word_id: str, data: WordUpdate):
    update = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    result = await words_collection.update_one(
        {"_id": ObjectId(word_id)}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Palabra no encontrada")
    doc = await words_collection.find_one({"_id": ObjectId(word_id)})
    return serialize(doc)


@router.delete("/{word_id}", status_code=204)
async def delete_word(word_id: str):
    result = await words_collection.delete_one({"_id": ObjectId(word_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Palabra no encontrada")
