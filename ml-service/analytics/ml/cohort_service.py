"""Cached cohort-profile service.

cohort_profile() does clustering + bootstrap stability on every call. It's fast
(~1s on the local data) but there's no reason to recompute it per request, so
we cache the result per k. Pass refresh=True (or ?refresh=1) to recompute.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CohortProfileService:
    _cache: dict = {}

    @classmethod
    def get(cls, k: int | None = None, refresh: bool = False,
            include_clusters: bool = False) -> dict:
        from analytics.ml.profiling import DEFAULT_K, cohort_profile

        key = (k or DEFAULT_K, include_clusters)
        if refresh or key not in cls._cache:
            logger.info("Computing cohort profile %s", key)
            cls._cache[key] = cohort_profile(k=key[0], include_clusters=key[1])
        return cls._cache[key]

    @classmethod
    def clear(cls) -> None:
        cls._cache.clear()
