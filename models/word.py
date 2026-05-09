from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class WordCat(str, Enum):
    N  = "N"
    V  = "V"
    PN = "PN"
    DT = "DT"
    AV = "AV"
    AF = "AF"
    CJ = "CJ"
    PT = "PT"


class Voz(str, Enum):
    A = "A"
    M = "M"


class Alin(str, Enum):
    AGT = "AGT"
    RCT = "RCT"


class WordCreate(BaseModel):
    cat:   WordCat
    kelne: str
    trad:  str
    com:   Optional[str] = None
    # tipo: NombreTipo (P/R/DN/DL/DF) | VerboTipo (ND/DN/DL/DF) | AfijoTipo (P/S)
    tipo:  Optional[str] = None
    # clase: NombreClase (AH1/AH2/AA1/UC/V1/C1/I1) | string libre para verbos
    clase: Optional[str] = None
    raiz:  Optional[str] = None   # _id de la raíz asociada
    voz:   Optional[Voz] = None   # solo verbos
    alin:  Optional[Alin] = None  # solo verbos


class WordUpdate(BaseModel):
    cat:   Optional[WordCat] = None
    kelne: Optional[str] = None
    trad:  Optional[str] = None
    com:   Optional[str] = None
    tipo:  Optional[str] = None
    clase: Optional[str] = None
    raiz:  Optional[str] = None
    voz:   Optional[Voz] = None
    alin:  Optional[Alin] = None


class WordOut(WordCreate):
    id: str = Field(alias="_id")

    model_config = {"populate_by_name": True}
