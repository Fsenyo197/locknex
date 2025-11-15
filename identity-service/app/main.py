import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.routes import register_routers


app = FastAPI(title="Identity Services API", version="1.0")

register_routers(app)

allowed_hosts = settings.ALLOWED_HOSTS.split(",")
cors_origins = settings.CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

STATIC_DIR = "static"
EXPORTS_DIR = os.path.join(STATIC_DIR, "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def root():
    return {"message": "Welcome to the Identity services API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
