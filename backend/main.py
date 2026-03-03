from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api import register
from api import hosts
from api import jobs
from api import agent_proxy

app = FastAPI()
import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for agent .deb download)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/api/health")
def health():
    return {"status": "ok"}

app.include_router(register.router)
app.include_router(hosts.router)
app.include_router(jobs.router)
app.include_router(agent_proxy.router)
