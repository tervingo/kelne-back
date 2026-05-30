from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.roots      import router as roots_router
from routers.words      import router as words_router
from routers.dictionary import router as dictionary_router

app = FastAPI(title="Kelne API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roots_router)
app.include_router(words_router)
app.include_router(dictionary_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
