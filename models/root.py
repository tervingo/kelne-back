from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class Degree(str, Enum):
    normal = "normal"
    fuerte = "fuerte"
    largo = "largo"


class WordType(str, Enum):
    nombre = "nombre"
    verbo = "verbo"


class Voice(str, Enum):
    activa = "activa"
    media = "media"


class Conjugation(str, Enum):
    agentiva = "agentiva"
    receptiva = "receptiva"


class DerivedWord(BaseModel):
    word: str
    translation: str
    word_class: str = Field(..., alias="wordClass")

    model_config = {"populate_by_name": True}


class Base(BaseModel):
    degree: Degree
    type: WordType
    voice: Optional[Voice] = None
    conjugation: Optional[Conjugation] = None
    translation: str
    derived_words: list[DerivedWord] = Field(default=[], alias="derivedWords")

    model_config = {"populate_by_name": True}


class RootCreate(BaseModel):
    root: str
    notes: Optional[str] = None
    bases: list[Base] = []


class RootUpdate(BaseModel):
    root: Optional[str] = None
    notes: Optional[str] = None
    bases: Optional[list[Base]] = None


class RootOut(RootCreate):
    id: str = Field(alias="_id")

    model_config = {"populate_by_name": True}
