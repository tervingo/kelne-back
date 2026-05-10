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
    """Sustituye los refs {kelne, cat} de cada base con el documento completo de words.
    Busca por raiz=root.root y hace match por (kelne, cat).
    """
    root_str = doc.get("root", "")
    words_map: dict[tuple, dict] = {}
    if root_str:
        async for word in words_collection.find({"raiz": root_str}):
            key = (word["kelne"], word["cat"])
            words_map[key] = serialize_word(word)

    for base in doc.get("bases", []):
        populated = []
        for ref in base.get("derivedWords", []):
            if isinstance(ref, dict):
                key = (ref.get("kelne", ""), ref.get("cat", ""))
                if key in words_map:
                    populated.append(words_map[key])
        base["derivedWords"] = populated
    return doc


@router.get("", response_model=list[RootListItem])
async def list_roots(q: str = Query(default="")):
    query: dict = {}
    if q:
        query = {
            "$or": [
                {"root":              {"$regex": q, "$options": "i"}},
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
        {"_id": ObjectId(root_id)}, {"root": 1}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Raíz no encontrada")
    # Cascade: borrar todas las palabras cuyo campo raiz coincide con este root string
    await words_collection.delete_many({"raiz": doc["root"]})
    await roots_collection.delete_one({"_id": ObjectId(root_id)})
