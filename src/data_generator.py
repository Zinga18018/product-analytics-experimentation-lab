from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


CHANNELS = ["organic", "paid_search", "social", "referral", "email"]
COUNTRIES = ["US", "India", "Canada", "UK", "Germany"]
DEVICES = ["desktop", "mobile", "tablet"]
VARIANTS = ["control", "treatment"]


@dataclass(frozen=True)
class GenerationConfig:
    users: int = 5000
    days: int = 60
    seed: int = 18018
    experiment_name: str = "onboarding_redesign"


def generate_product_data(config: GenerationConfig = GenerationConfig()) -> dict[str, pd.DataFrame]:
    rng = random.Random(config.seed)
    start = date(2026, 1, 1)

    users = []
    assignments = []
    sessions = []
    events = []

    event_id = 1
    session_id = 1

    for user_id in range(1, config.users + 1):
        signup_offset = rng.randint(0, config.days - 1)
        signup_date = start + timedelta(days=signup_offset)
        channel = _weighted_choice(
            rng,
            {"organic": 0.35, "paid_search": 0.25, "social": 0.18, "referral": 0.12, "email": 0.10},
        )
        country = rng.choice(COUNTRIES)
        device = _weighted_choice(rng, {"desktop": 0.44, "mobile": 0.48, "tablet": 0.08})
        variant = rng.choice(VARIANTS)

        users.append(
            {
                "user_id": user_id,
                "signup_date": signup_date.isoformat(),
                "country": country,
                "acquisition_channel": channel,
                "device": device,
            }
        )
        assignments.append(
            {
                "user_id": user_id,
                "experiment_name": config.experiment_name,
                "variant": variant,
                "assigned_at": datetime.combine(signup_date, datetime.min.time()).isoformat(),
            }
        )

        max_sessions = rng.randint(1, 8)
        for session_number in range(max_sessions):
            session_day = signup_date + timedelta(days=rng.randint(0, max(0, config.days - signup_offset - 1)))
            session_time = datetime.combine(session_day, datetime.min.time()) + timedelta(
                hours=rng.randint(8, 22),
                minutes=rng.randint(0, 59),
            )
            sessions.append(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "session_started_at": session_time.isoformat(),
                    "session_date": session_day.isoformat(),
                    "variant": variant,
                    "device": device,
                }
            )

            purchase_probability = _purchase_probability(channel, device, variant, session_number)
            event_names = ["view_landing", "view_product"]
            if rng.random() < 0.72:
                event_names.append("start_checkout")
            if rng.random() < purchase_probability:
                event_names.append("purchase")

            for step, event_name in enumerate(event_names):
                revenue = round(rng.uniform(18, 180), 2) if event_name == "purchase" else 0.0
                events.append(
                    {
                        "event_id": event_id,
                        "session_id": session_id,
                        "user_id": user_id,
                        "event_name": event_name,
                        "event_time": (session_time + timedelta(minutes=step * rng.randint(1, 6))).isoformat(),
                        "event_date": session_day.isoformat(),
                        "variant": variant,
                        "revenue": revenue,
                    }
                )
                event_id += 1

            session_id += 1

    return {
        "users": pd.DataFrame(users),
        "experiment_assignments": pd.DataFrame(assignments),
        "sessions": pd.DataFrame(sessions),
        "events": pd.DataFrame(events),
    }


def write_sqlite(db_path: Path, tables: dict[str, pd.DataFrame]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        for name, frame in tables.items():
            frame.to_sql(name, conn, index=False)
        _create_indexes(conn)


def build_database(db_path: Path, config: GenerationConfig = GenerationConfig()) -> dict[str, int]:
    tables = generate_product_data(config)
    write_sqlite(db_path, tables)
    return {name: len(frame) for name, frame in tables.items()}


def _weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    choices = list(weights)
    probabilities = list(weights.values())
    return rng.choices(choices, weights=probabilities, k=1)[0]


def _purchase_probability(channel: str, device: str, variant: str, session_number: int) -> float:
    probability = 0.16
    probability += 0.035 if variant == "treatment" else 0
    probability += 0.025 if channel in {"email", "referral"} else 0
    probability -= 0.025 if device == "mobile" else 0
    probability += min(session_number, 3) * 0.015
    return max(0.04, min(0.45, probability))


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX idx_users_signup_date ON users(signup_date);
        CREATE INDEX idx_users_id ON users(user_id);
        CREATE INDEX idx_sessions_user_date ON sessions(user_id, session_date);
        CREATE INDEX idx_events_user_event ON events(user_id, event_name);
        CREATE INDEX idx_events_session ON events(session_id);
        CREATE INDEX idx_assignments_variant ON experiment_assignments(variant);
        CREATE INDEX idx_assignments_experiment_date ON experiment_assignments(experiment_name, assigned_at);
        """
    )
