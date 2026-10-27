"""All configuration comes from env vars (optionally a .env file at the repo root)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    nebius_api_key: str
    nebius_base_url: str
    models: dict[str, str]  # tier -> model id
    tavily_api_key: str
    github_token: str
    executor: str
    max_run_cost_usd: float
    demo_daily_budget_usd: float
    demo_password: str
    recipe_max_age_days: int
    db_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        def e(key: str, default: str = "") -> str:
            return os.environ.get(key) or default  # empty (e.g. an unset Action input) means default

        return cls(
            nebius_api_key=e("NEBIUS_API_KEY", ""),
            nebius_base_url=e("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
            models={
                "nano": e("MODEL_NANO", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"),
                "super": e("MODEL_SUPER", "nvidia/nemotron-3-super-120b-a12b"),
                "ultra": e("MODEL_ULTRA", "nvidia/Nemotron-3-Ultra-550b-a55b"),
            },
            tavily_api_key=e("TAVILY_API_KEY", ""),
            github_token=e("GITHUB_TOKEN", ""),
            executor=e("EXECUTOR", "docker"),
            max_run_cost_usd=float(e("MAX_RUN_COST_USD", "0.50")),
            demo_daily_budget_usd=float(e("DEMO_DAILY_BUDGET_USD", "2.00")),
            demo_password=e("DEMO_PASSWORD", ""),
            recipe_max_age_days=int(e("RECIPE_MAX_AGE_DAYS", "14")),
            db_path=Path(e("BUMPLESS_DB", str(ROOT / "data" / "bumpless.db"))),
        )


settings = Settings.from_env()
