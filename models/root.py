from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Degree(str, Enum):
    normal = "normal"
    fuerte = "fuerte"
    largo  = "largo"


class WordType(str, Enum):
    nombre = "nombre"
    verbo  = "verbo"


class Voice(str, Enum):
    activa = "activa"
    media  = "media"


class Conjugation(str, Enum):
    agentiva  = "agentiva"
    receptiva = "receptiva"


class DerivedWordRef(BaseModel):
    """Referencia ligera a una palabra en la colección words."""
    kelne: str
    cat:   str  # WordCat value: N, V, PN, …


class Base(BaseModel):
    degree:      Degree
    type:        WordType
    voice:       Optional[Voice] = None
    conjugation: Optional[Conjugation] = None
    translation: str
    derived_words: list[DerivedWordRef] = Field(default=[], alias="derivedWords")

    model_config = {"populate_by_name": True}


class RootCreate(BaseModel):
    root:  str
    notes: Optional[str] = None
    bases: list[Base] = []


class RootUpdate(BaseModel):
    """root es inmutable — solo notes y bases son actualizables."""
    notes: Optional[str] = None
    bases: Optional[list[Base]] = None


class RootListItem(BaseModel):
    id:    str = Field(alias="_id")
    root:  str
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}
