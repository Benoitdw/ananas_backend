"""Application FastAPI.

Le front vit dans un depot separe et parle a cette API en cross-origin: le
cookie de session impose donc `allow_credentials=True` et une liste d'origines
explicite (le joker '*' est refuse par les navigateurs avec des credentials).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ananas.api import admin, auth, channels, companies, jobs, profile, saved
from ananas.config import settings
from ananas.ai.registry import load_providers
from ananas.notifiers.registry import load_notifiers
from ananas.scrapers.registry import load_scrapers

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s | %(message)s")

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Peuple les registres au demarrage: l'API a besoin de savoir quels
    # transports sont disponibles et quelles entreprises ont un scraper.
    load_scrapers()
    load_notifiers()
    load_providers()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Ananas API",
    version="0.1.0",
    description="Veille emploi geolocalisee: entreprises, favoris, offres, notifications.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(saved.router)
app.include_router(jobs.router)
app.include_router(channels.router)
app.include_router(profile.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "version": app.version}
