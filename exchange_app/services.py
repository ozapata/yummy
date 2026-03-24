from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import requests
from flask import current_app

from .db import get_db


class ExchangeRateError(RuntimeError):
    pass


@dataclass
class ExchangeRateService:
    base_url: str
    session: requests.Session | requests.sessions.Session

    @classmethod
    def from_app(cls, app):
        session = app.config.get("HTTP_SESSION") or requests.Session()
        return cls(base_url=app.config["EXCHANGE_API_BASE_URL"], session=session)

    def ensure_seed_data(self, days: int) -> None:
        if self._has_history():
            return
        start_date = date.today() - timedelta(days=days - 1)
        self._fetch_and_store_range(start_date=start_date, end_date=date.today())

    def refresh_latest_rates(self) -> None:
        payload = self._get_json(f"{self.base_url}/latest", params={"base": "USD", "symbols": "MXN,CAD"})
        rate_date = payload["date"]
        rates = payload["rates"]
        self._upsert_rate(
            rate_date=rate_date,
            usd_to_mxn=float(rates["MXN"]),
            usd_to_cad=float(rates["CAD"]),
            fetched_at=self._now_iso(),
        )

    def build_dashboard_payload(self, days: int) -> dict:
        rows = self._get_recent_history(days=days)
        if not rows:
            try:
                self.ensure_seed_data(days=days)
            except ExchangeRateError:
                return {
                    "latest": {
                        "date": None,
                        "usd_to_mxn": None,
                        "usd_to_cad": None,
                        "fetched_at": "No data loaded yet.",
                    },
                    "history": [],
                    "chart": {
                        "labels": [],
                        "usd_to_mxn": [],
                        "usd_to_cad": [],
                    },
                }
            rows = self._get_recent_history(days=days)

        latest = rows[-1] if rows else None
        return {
            "latest": {
                "date": latest["rate_date"] if latest else None,
                "usd_to_mxn": latest["usd_to_mxn"] if latest else None,
                "usd_to_cad": latest["usd_to_cad"] if latest else None,
                "fetched_at": latest["fetched_at"] if latest else "No data loaded yet.",
            },
            "history": [
                {
                    "date": row["rate_date"],
                    "usd_to_mxn": row["usd_to_mxn"],
                    "usd_to_cad": row["usd_to_cad"],
                    "fetched_at": row["fetched_at"],
                }
                for row in rows
            ],
            "chart": {
                "labels": [row["rate_date"] for row in rows],
                "usd_to_mxn": [row["usd_to_mxn"] for row in rows],
                "usd_to_cad": [row["usd_to_cad"] for row in rows],
            },
        }

    def _fetch_and_store_range(self, start_date: date, end_date: date) -> None:
        payload = self._get_json(
            f"{self.base_url}/{start_date.isoformat()}..{end_date.isoformat()}",
            params={"base": "USD", "symbols": "MXN,CAD"},
        )
        fetched_at = self._now_iso()
        rates_by_date = payload.get("rates", {})
        if not rates_by_date:
            raise ExchangeRateError("The exchange rate service returned no historical data.")

        for rate_date, rates in sorted(rates_by_date.items()):
            self._upsert_rate(
                rate_date=rate_date,
                usd_to_mxn=float(rates["MXN"]),
                usd_to_cad=float(rates["CAD"]),
                fetched_at=fetched_at,
            )

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise ExchangeRateError("Unable to reach the exchange rate service right now.") from exc
        except ValueError as exc:
            raise ExchangeRateError("The exchange rate service returned an invalid response.") from exc

    def _has_history(self) -> bool:
        row = get_db().execute("SELECT 1 FROM exchange_rates LIMIT 1").fetchone()
        return row is not None

    def _upsert_rate(self, rate_date: str, usd_to_mxn: float, usd_to_cad: float, fetched_at: str) -> None:
        db = get_db()
        db.execute(
            """
            INSERT INTO exchange_rates (rate_date, usd_to_mxn, usd_to_cad, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(rate_date) DO UPDATE SET
                usd_to_mxn = excluded.usd_to_mxn,
                usd_to_cad = excluded.usd_to_cad,
                fetched_at = excluded.fetched_at
            """,
            (rate_date, usd_to_mxn, usd_to_cad, fetched_at),
        )
        db.commit()

    def _get_recent_history(self, days: int) -> list:
        rows = get_db().execute(
            """
            SELECT rate_date, usd_to_mxn, usd_to_cad, fetched_at
            FROM (
                SELECT rate_date, usd_to_mxn, usd_to_cad, fetched_at
                FROM exchange_rates
                ORDER BY rate_date DESC
                LIMIT ?
            )
            ORDER BY rate_date ASC
            """,
            (days,),
        ).fetchall()
        return list(rows)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()
