import datetime
import random
from typing import Any, Callable

DEFAULT_HISTORY_DAYS = 5


def get_history_days(raw_value: Any, default_days: int = DEFAULT_HISTORY_DAYS) -> int:
    """Return a validated history window size."""
    try:
        history_days = int(raw_value)
        if history_days < 1:
            raise ValueError
        return history_days
    except (TypeError, ValueError):
        return default_days


def parse_iso_date(date_str: str) -> datetime.date | None:
    """Parse an ISO date string."""
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        return None


def normalize_history_data(raw: Any) -> dict:
    """
    Normalize history structure to:
    {"users": {"<user_id>": [{"date": "YYYY-MM-DD", "pig_id": "xxx"}]}}
    """
    users = raw.get("users") if isinstance(raw, dict) else None
    if not isinstance(users, dict):
        return {"users": {}}

    normalized_users: dict[str, list[dict[str, str]]] = {}
    for user_id, records in users.items():
        if not isinstance(records, list):
            continue

        normalized_records = []
        for record in records:
            if not isinstance(record, dict):
                continue
            date_str = record.get("date")
            pig_id = record.get("pig_id")
            if isinstance(date_str, str) and isinstance(pig_id, str):
                normalized_records.append({"date": date_str, "pig_id": pig_id})

        normalized_users[str(user_id)] = normalized_records

    return {"users": normalized_users}


def cleanup_user_history(
    records: list[dict], today: datetime.date, history_days: int
) -> list[dict]:
    """Keep only recent (history_days + today) records, one entry per day."""
    cleaned_records = []
    seen_dates = set()

    def sort_key(record: dict) -> datetime.date:
        record_date = parse_iso_date(record.get("date", ""))
        return record_date or datetime.date.min

    # Keep the latest entry for the same date.
    for record in sorted(records, key=sort_key, reverse=True):
        date_str = record.get("date")
        pig_id = record.get("pig_id")
        if not isinstance(date_str, str) or not isinstance(pig_id, str):
            continue

        record_date = parse_iso_date(date_str)
        if not record_date:
            continue

        delta_days = (today - record_date).days
        if delta_days < 0 or delta_days > history_days:
            continue

        if date_str in seen_dates:
            continue

        seen_dates.add(date_str)
        cleaned_records.append({"date": date_str, "pig_id": pig_id})

    cleaned_records.reverse()
    return cleaned_records


def get_recent_pig_ids(
    records: list[dict], today: datetime.date, history_days: int
) -> set[str]:
    """Return pig IDs drawn in the past history_days days (excluding today)."""
    recent_pig_ids = set()
    for record in records:
        record_date = parse_iso_date(record.get("date", ""))
        if not record_date:
            continue

        delta_days = (today - record_date).days
        if 1 <= delta_days <= history_days:
            pig_id = record.get("pig_id")
            if isinstance(pig_id, str) and pig_id:
                recent_pig_ids.add(pig_id)
    return recent_pig_ids


def get_yesterday_pig_id(records: list[dict], today: datetime.date) -> str | None:
    """Return yesterday's pig ID if exists."""
    yesterday_str = (today - datetime.timedelta(days=1)).isoformat()
    for record in reversed(records):
        if record.get("date") != yesterday_str:
            continue
        pig_id = record.get("pig_id")
        if isinstance(pig_id, str) and pig_id:
            return pig_id
    return None


def pick_pig_for_user(
    pig_list: list[dict],
    history_data: dict,
    user_id: str,
    today: datetime.date,
    history_days: int,
    rng_choice: Callable[[list[dict]], dict] = random.choice,
) -> tuple[dict, dict]:
    """Select a pig for a user with recent-history dedup and fallback rules."""
    normalized_history_data = normalize_history_data(history_data)
    users = normalized_history_data["users"]
    user_history = users.get(user_id, [])
    if not isinstance(user_history, list):
        user_history = []
    user_history = cleanup_user_history(user_history, today, history_days)

    recent_pig_ids = get_recent_pig_ids(user_history, today, history_days)
    candidates = [pig for pig in pig_list if pig.get("id") not in recent_pig_ids]

    if candidates:
        selected_pig = rng_choice(candidates)
    else:
        yesterday_pig_id = get_yesterday_pig_id(user_history, today)
        if yesterday_pig_id:
            non_yesterday_candidates = [
                pig for pig in pig_list if pig.get("id") != yesterday_pig_id
            ]
            selected_pig = (
                rng_choice(non_yesterday_candidates)
                if non_yesterday_candidates
                else rng_choice(pig_list)
            )
        else:
            selected_pig = rng_choice(pig_list)

    selected_pig_id = selected_pig.get("id")
    if isinstance(selected_pig_id, str) and selected_pig_id:
        today_str = today.isoformat()
        user_history = [
            record for record in user_history if record.get("date") != today_str
        ]
        user_history.append({"date": today_str, "pig_id": selected_pig_id})

    users[user_id] = cleanup_user_history(user_history, today, history_days)
    return selected_pig, normalized_history_data

