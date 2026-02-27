import os
import time

from flask import Flask, render_template

from weather import get_weather_data

app = Flask(__name__)

REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", 600))

# Simple in-memory cache so rapid browser reloads don't hammer the WU API.
# Data is considered fresh for the same duration as the page refresh interval.
_cache = {"data": None, "timestamp": 0.0}


@app.route("/")
def index():
    now = time.monotonic()
    age = now - _cache["timestamp"]

    if _cache["data"] is None or age >= REFRESH_INTERVAL:
        _cache["data"] = get_weather_data()
        _cache["timestamp"] = now

    return render_template(
        "index.html",
        data=_cache["data"],
        refresh=REFRESH_INTERVAL,
    )


if __name__ == "__main__":
    # Used when running directly (e.g. local dev outside Docker).
    # In Docker, gunicorn is used instead (see Dockerfile CMD).
    app.run(host="0.0.0.0", port=5000, debug=False)
