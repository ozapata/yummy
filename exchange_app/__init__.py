from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template

from .db import close_db, get_db, init_db
from .services import ExchangeRateError, ExchangeRateService


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=Path(app.instance_path) / "exchange_rates.sqlite",
        EXCHANGE_API_BASE_URL="https://api.frankfurter.dev/v1",
        HISTORY_DAYS=30,
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()
        service = ExchangeRateService.from_app(app)
        try:
            service.ensure_seed_data(days=app.config["HISTORY_DAYS"])
        except ExchangeRateError:
            pass

    @app.route("/")
    def index():
        service = ExchangeRateService.from_app(app)
        payload = service.build_dashboard_payload(days=app.config["HISTORY_DAYS"])
        return render_template("index.html", data=payload)

    @app.route("/api/rates")
    def get_rates():
        service = ExchangeRateService.from_app(app)
        return jsonify(service.build_dashboard_payload(days=app.config["HISTORY_DAYS"]))

    @app.route("/api/refresh", methods=["POST"])
    def refresh_rates():
        service = ExchangeRateService.from_app(app)
        try:
            service.refresh_latest_rates()
        except ExchangeRateError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify(service.build_dashboard_payload(days=app.config["HISTORY_DAYS"]))

    return app
