"""LiteLLM pricing fetcher and cost calculator."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen


LITELLM_PRICING_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

DEFAULT_PROVIDER_PREFIXES = [
    "anthropic/",
    "claude-3-5-",
    "claude-3-",
    "claude-",
    "openai/",
    "azure/",
    "openrouter/openai/",
]


@dataclass
class LiteLLMModelPricing:
    input_cost_per_token: Optional[float] = None
    output_cost_per_token: Optional[float] = None
    cache_creation_input_token_cost: Optional[float] = None
    cache_read_input_token_cost: Optional[float] = None
    input_cost_per_token_above_200k_tokens: Optional[float] = None
    output_cost_per_token_above_200k_tokens: Optional[float] = None
    cache_creation_input_token_cost_above_200k_tokens: Optional[float] = None
    cache_read_input_token_cost_above_200k_tokens: Optional[float] = None


class LiteLLMPricingCache:
    """Fetch and cache LiteLLM pricing data."""

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        ttl_seconds: int = 24 * 60 * 60,
    ) -> None:
        self.cache_path = (
            cache_path
            if cache_path is not None
            else Path("~/.cache/agentop/litellm_pricing.json").expanduser()
        )
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(60, ttl_seconds)
        self._dataset: Optional[Dict[str, LiteLLMModelPricing]] = None
        self._fetched_at: Optional[float] = None

    def get_dataset(self) -> Dict[str, LiteLLMModelPricing]:
        if self._dataset and self._fetched_at and not self._is_expired(self._fetched_at):
            return self._dataset

        cached = self._load_cache()
        if cached:
            self._dataset, self._fetched_at = cached
            if self._fetched_at and not self._is_expired(self._fetched_at):
                return self._dataset

        if os.environ.get("AGENTOP_PRICING_OFFLINE") == "1":
            return self._dataset or {}

        fetched = self._fetch_pricing()
        if fetched:
            self._dataset = fetched
            self._fetched_at = time.time()
            self._save_cache(self._dataset, self._fetched_at)
            return self._dataset

        return self._dataset or {}

    def _is_expired(self, fetched_at: float) -> bool:
        return (time.time() - fetched_at) > self.ttl_seconds

    def _fetch_pricing(self) -> Optional[Dict[str, LiteLLMModelPricing]]:
        try:
            req = Request(LITELLM_PRICING_URL, headers={"User-Agent": "agentop"})
            with urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

        if not isinstance(data, dict):
            return None

        dataset: Dict[str, LiteLLMModelPricing] = {}
        for key, value in data.items():
            if not isinstance(value, dict):
                continue
            dataset[key] = LiteLLMModelPricing(
                input_cost_per_token=_as_float(value.get("input_cost_per_token")),
                output_cost_per_token=_as_float(value.get("output_cost_per_token")),
                cache_creation_input_token_cost=_as_float(
                    value.get("cache_creation_input_token_cost")
                ),
                cache_read_input_token_cost=_as_float(
                    value.get("cache_read_input_token_cost")
                ),
                input_cost_per_token_above_200k_tokens=_as_float(
                    value.get("input_cost_per_token_above_200k_tokens")
                ),
                output_cost_per_token_above_200k_tokens=_as_float(
                    value.get("output_cost_per_token_above_200k_tokens")
                ),
                cache_creation_input_token_cost_above_200k_tokens=_as_float(
                    value.get("cache_creation_input_token_cost_above_200k_tokens")
                ),
                cache_read_input_token_cost_above_200k_tokens=_as_float(
                    value.get("cache_read_input_token_cost_above_200k_tokens")
                ),
            )
        return dataset

    def _load_cache(self) -> Optional[tuple[Dict[str, LiteLLMModelPricing], Optional[float]]]:
        if not self.cache_path.exists():
            return None
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        fetched_at = _as_float(payload.get("fetched_at"))
        raw = payload.get("data")
        if not isinstance(raw, dict):
            return None
        dataset: Dict[str, LiteLLMModelPricing] = {}
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            dataset[key] = LiteLLMModelPricing(
                input_cost_per_token=_as_float(value.get("input_cost_per_token")),
                output_cost_per_token=_as_float(value.get("output_cost_per_token")),
                cache_creation_input_token_cost=_as_float(
                    value.get("cache_creation_input_token_cost")
                ),
                cache_read_input_token_cost=_as_float(
                    value.get("cache_read_input_token_cost")
                ),
                input_cost_per_token_above_200k_tokens=_as_float(
                    value.get("input_cost_per_token_above_200k_tokens")
                ),
                output_cost_per_token_above_200k_tokens=_as_float(
                    value.get("output_cost_per_token_above_200k_tokens")
                ),
                cache_creation_input_token_cost_above_200k_tokens=_as_float(
                    value.get("cache_creation_input_token_cost_above_200k_tokens")
                ),
                cache_read_input_token_cost_above_200k_tokens=_as_float(
                    value.get("cache_read_input_token_cost_above_200k_tokens")
                ),
            )
        return dataset, fetched_at

    def _save_cache(self, dataset: Dict[str, LiteLLMModelPricing], fetched_at: float) -> None:
        payload = {
            "fetched_at": fetched_at,
            "data": {
                key: {
                    "input_cost_per_token": pricing.input_cost_per_token,
                    "output_cost_per_token": pricing.output_cost_per_token,
                    "cache_creation_input_token_cost": pricing.cache_creation_input_token_cost,
                    "cache_read_input_token_cost": pricing.cache_read_input_token_cost,
                    "input_cost_per_token_above_200k_tokens": pricing.input_cost_per_token_above_200k_tokens,
                    "output_cost_per_token_above_200k_tokens": pricing.output_cost_per_token_above_200k_tokens,
                    "cache_creation_input_token_cost_above_200k_tokens": pricing.cache_creation_input_token_cost_above_200k_tokens,
                    "cache_read_input_token_cost_above_200k_tokens": pricing.cache_read_input_token_cost_above_200k_tokens,
                }
                for key, pricing in dataset.items()
            },
        }
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception:
            return


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class LiteLLMCostCalculator:
    """Calculate cost from tokens using LiteLLM pricing."""

    def __init__(self, cache: Optional[LiteLLMPricingCache] = None) -> None:
        self.cache = cache or LiteLLMPricingCache()

    def get_model_pricing(self, model_name: str) -> Optional[LiteLLMModelPricing]:
        dataset = self.cache.get_dataset()
        if not dataset:
            return None

        candidates = {model_name}
        for prefix in DEFAULT_PROVIDER_PREFIXES:
            candidates.add(f"{prefix}{model_name}")

        for candidate in candidates:
            pricing = dataset.get(candidate)
            if pricing:
                return pricing

        lower = model_name.lower()
        for key, pricing in dataset.items():
            comparison = key.lower()
            if lower in comparison or comparison in lower:
                return pricing

        return None

    def calculate_cost(
        self,
        model_name: Optional[str],
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int,
        cache_read_tokens: int,
    ) -> float:
        if not model_name:
            return 0.0

        pricing = self.get_model_pricing(model_name)
        if not pricing:
            return 0.0

        def tiered_cost(total_tokens: int, base: Optional[float], tiered: Optional[float]) -> float:
            if total_tokens <= 0:
                return 0.0
            threshold = 200_000
            if total_tokens > threshold and tiered is not None:
                below = min(total_tokens, threshold)
                above = max(0, total_tokens - threshold)
                cost = above * tiered
                if base is not None:
                    cost += below * base
                return cost
            if base is not None:
                return total_tokens * base
            return 0.0

        input_cost = tiered_cost(
            input_tokens,
            pricing.input_cost_per_token,
            pricing.input_cost_per_token_above_200k_tokens,
        )
        output_cost = tiered_cost(
            output_tokens,
            pricing.output_cost_per_token,
            pricing.output_cost_per_token_above_200k_tokens,
        )
        cache_creation_cost = tiered_cost(
            cache_creation_tokens,
            pricing.cache_creation_input_token_cost,
            pricing.cache_creation_input_token_cost_above_200k_tokens,
        )
        cache_read_cost = tiered_cost(
            cache_read_tokens,
            pricing.cache_read_input_token_cost,
            pricing.cache_read_input_token_cost_above_200k_tokens,
        )

        return input_cost + output_cost + cache_creation_cost + cache_read_cost
