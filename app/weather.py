import base64
import math
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

ET_TZ = ZoneInfo("America/New_York")

BASE_OBS      = "https://api.weather.com/v2/pws/observations/current"
BASE_DAILY    = "https://api.weather.com/v2/pws/dailysummary/date"
BASE_FORECAST = "https://api.weather.com/v3/wx/forecast/daily/5day"


def _env_list(var, default):
    return [s.strip() for s in os.environ.get(var, default).split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Weather condition icons  (pure SVG, 100×100 viewBox, encoded as <img> tags)
# Thick strokes for e-ink legibility. White fills used to knock out overlaps.
# ---------------------------------------------------------------------------

_CP = (                                         # reusable cloud outline path
    "M 18 52 Q 6 52 6 40 Q 6 28 18 26 "
    "Q 19 12 32 12 Q 40 4 50 12 "
    "Q 58 4 68 12 Q 84 12 84 28 "
    "Q 94 32 90 44 Q 88 54 76 52 Z"
)

_RAW_ICONS = {
    "sunny": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="16" fill="none" stroke="#000" stroke-width="6"/>'
        '<line x1="50" y1="6"  x2="50" y2="22" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '<line x1="50" y1="78" x2="50" y2="94" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '<line x1="6"  y1="50" x2="22" y2="50" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '<line x1="78" y1="50" x2="94" y2="50" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '<line x1="18" y1="18" x2="30" y2="30" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '<line x1="70" y1="70" x2="82" y2="82" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '<line x1="18" y1="82" x2="30" y2="70" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '<line x1="70" y1="30" x2="82" y2="18" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
        '</svg>'
    ),
    "moon": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<path d="M 62 16 A 34 34 0 1 0 62 84 A 24 24 0 1 1 62 16 Z"'
        ' fill="none" stroke="#000" stroke-width="6"/>'
        '</svg>'
    ),
    "cloudy": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<path d="M 18 65 Q 6 65 6 53 Q 6 41 18 39 Q 19 25 32 25 Q 40 17 50 25'
        ' Q 58 17 68 25 Q 84 25 84 41 Q 94 45 90 57 Q 88 67 76 65 Z"'
        ' fill="none" stroke="#000" stroke-width="5.5"/>'
        '</svg>'
    ),
    "partly_cloudy": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        # Sun (upper-left)
        '<circle cx="34" cy="28" r="13" fill="none" stroke="#000" stroke-width="4.5"/>'
        '<line x1="34" y1="8"  x2="34" y2="17" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="34" y1="39" x2="34" y2="48" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="14" y1="28" x2="23" y2="28" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="45" y1="28" x2="54" y2="28" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="21" y1="15" x2="28" y2="22" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="40" y1="34" x2="47" y2="41" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        # Cloud in foreground (white fill knocks out sun behind)
        '<path d="M 22 82 Q 12 82 12 72 Q 12 62 22 60 Q 22 50 33 50'
        ' Q 40 44 48 50 Q 55 44 65 50 Q 80 50 80 64 Q 88 68 85 78 Q 83 86 72 83 Z"'
        ' fill="white" stroke="#000" stroke-width="5"/>'
        '</svg>'
    ),
    "partly_cloudy_night": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        # Crescent moon (upper-left)
        '<path d="M 44 10 A 22 22 0 1 0 44 50 A 14 14 0 1 1 44 10 Z"'
        ' fill="none" stroke="#000" stroke-width="5"/>'
        # Cloud in foreground
        '<path d="M 22 82 Q 12 82 12 72 Q 12 62 22 60 Q 22 50 33 50'
        ' Q 40 44 48 50 Q 55 44 65 50 Q 80 50 80 64 Q 88 68 85 78 Q 83 86 72 83 Z"'
        ' fill="white" stroke="#000" stroke-width="5"/>'
        '</svg>'
    ),
    "rain": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<path d="{_CP}" fill="none" stroke="#000" stroke-width="5"/>'
        '<line x1="26" y1="62" x2="20" y2="80" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="42" y1="62" x2="36" y2="80" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="58" y1="62" x2="52" y2="80" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '<line x1="74" y1="62" x2="68" y2="80" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
        '</svg>'
    ),
    "snow": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<path d="{_CP}" fill="none" stroke="#000" stroke-width="5"/>'
        # Three snowflake asterisks
        '<g stroke="#000" stroke-width="3" stroke-linecap="round">'
        '<line x1="24" y1="62" x2="24" y2="80"/><line x1="15" y1="71" x2="33" y2="71"/>'
        '<line x1="17" y1="65" x2="31" y2="77"/><line x1="31" y1="65" x2="17" y2="77"/>'
        '<line x1="50" y1="62" x2="50" y2="80"/><line x1="41" y1="71" x2="59" y2="71"/>'
        '<line x1="43" y1="65" x2="57" y2="77"/><line x1="57" y1="65" x2="43" y2="77"/>'
        '<line x1="76" y1="62" x2="76" y2="80"/><line x1="67" y1="71" x2="85" y2="71"/>'
        '<line x1="69" y1="65" x2="83" y2="77"/><line x1="83" y1="65" x2="69" y2="77"/>'
        '</g>'
        '</svg>'
    ),
    "thunder": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<path d="{_CP}" fill="none" stroke="#000" stroke-width="5"/>'
        '<polygon points="54,56 44,72 52,72 38,94 64,70 54,70" fill="#000"/>'
        '</svg>'
    ),
    "fog": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<line x1="8"  y1="18" x2="92" y2="18" stroke="#000" stroke-width="5.5" stroke-linecap="round"/>'
        '<line x1="18" y1="34" x2="82" y2="34" stroke="#000" stroke-width="5.5" stroke-linecap="round"/>'
        '<line x1="8"  y1="50" x2="92" y2="50" stroke="#000" stroke-width="5.5" stroke-linecap="round"/>'
        '<line x1="18" y1="66" x2="82" y2="66" stroke="#000" stroke-width="5.5" stroke-linecap="round"/>'
        '<line x1="8"  y1="82" x2="92" y2="82" stroke="#000" stroke-width="5.5" stroke-linecap="round"/>'
        '</svg>'
    ),
}


def _svg_img(key, size=130):
    """Return an <img> tag with the SVG encoded as a base64 data URI.

    Explicitly injects width/height into the <svg> element so old WebKit
    browsers (e.g. Kindle Gen 3) derive the correct square intrinsic size
    rather than guessing from the viewBox alone.
    """
    svg = _RAW_ICONS.get(key, "")
    if not svg:
        return ""
    # Stamp explicit dimensions on the SVG element itself
    svg = svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
    b64 = base64.b64encode(svg.encode()).decode()
    # Redundant width/height attrs + inline style belt-and-suspenders for old WebKit
    return (
        f'<img src="data:image/svg+xml;base64,{b64}"'
        f' width="{size}" height="{size}"'
        f' style="width:{size}px;height:{size}px;display:block;"'
        f' alt="">'
    )


def get_weather_condition(phrase, hour_et):
    """Map a WU forecast phrase to an icon key. Returns None if unrecognised."""
    if not phrase:
        return None
    p = phrase.lower()
    is_night = hour_et < 6 or hour_et >= 20

    if any(w in p for w in ["thunder", "t-storm", "lightning"]):
        return "thunder"
    if any(w in p for w in ["snow", "flurr", "blizzard", "sleet", "wintry", "hail"]):
        return "snow"
    if any(w in p for w in ["rain", "shower", "drizzl", "sprinkl"]):
        return "rain"
    if any(w in p for w in ["fog", "haze", "mist", "smoke", "dust", "sand"]):
        return "fog"
    if any(w in p for w in ["partly", "few cloud", "scattered", "mostly sun"]):
        return "partly_cloudy_night" if is_night else "partly_cloudy"
    if any(w in p for w in ["cloud", "overcast"]):
        return "cloudy"
    if any(w in p for w in ["clear", "sunny", "fair"]):
        return "moon" if is_night else "sunny"
    return None


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def fetch_observation(station_id, api_key):
    """Current observation for a single PWS. Returns first obs dict or None."""
    try:
        r = requests.get(BASE_OBS, params={
            "stationId": station_id, "format": "json",
            "units": "e", "apiKey": api_key,
        }, timeout=10)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        return obs[0] if obs else None
    except Exception as exc:
        print(f"[weather] obs {station_id}: {exc}")
        return None


def fetch_daily_summary(station_id, api_key):
    """Today's observed high/low from WU PWS daily summary."""
    today = datetime.now(ET_TZ).strftime("%Y%m%d")
    try:
        r = requests.get(BASE_DAILY, params={
            "stationId": station_id, "format": "json",
            "units": "e", "date": today, "apiKey": api_key,
        }, timeout=10)
        r.raise_for_status()
        summaries = r.json().get("summaries", [])
        return summaries[0] if summaries else None
    except Exception as exc:
        print(f"[weather] daily {station_id}: {exc}")
        return None


def fetch_forecast(lat, lon, api_key):
    """5-day forecast by geocode. Returns raw JSON dict or None."""
    try:
        r = requests.get(BASE_FORECAST, params={
            "geocode": f"{lat},{lon}", "format": "json",
            "units": "e", "language": "en-US", "apiKey": api_key,
        }, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        print(f"[weather] forecast ({lat},{lon}): {exc}")
        return None


# ---------------------------------------------------------------------------
# Calculations
# ---------------------------------------------------------------------------

def circular_mean(angles_deg):
    """
    Vector/circular mean for directional data.
    Handles the 0°/360° wraparound correctly (e.g. mean of 350° and 10° = 0°).
    Returns rounded integer degrees or None if list is empty.
    """
    if not angles_deg:
        return None
    sin_sum = sum(math.sin(math.radians(a)) for a in angles_deg)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles_deg)
    return round(math.degrees(math.atan2(sin_sum, cos_sum)) % 360)


def degrees_to_compass(degrees):
    labels = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return labels[round(degrees / 22.5) % 16]


def calculate_feels_like(temp_f, humidity, wind_mph):
    """
    Combined NWS wind chill and Rothfusz heat index.

    Wind Chill applies when T <= 50°F and wind > 3 mph.
    Heat Index applies when T >= 80°F.
    Otherwise returns the actual temperature rounded.

    Intentionally mixes sources: temp/humidity from primary PWS,
    wind from the nearby-station average.
    """
    if temp_f is None:
        return None

    # --- Wind Chill (NWS formula) ---
    if temp_f <= 50 and wind_mph is not None and wind_mph > 3:
        v = wind_mph ** 0.16
        return round(35.74 + 0.6215 * temp_f - 35.75 * v + 0.4275 * temp_f * v)

    # --- Heat Index (Rothfusz regression) ---
    if temp_f >= 80 and humidity is not None:
        T, RH = temp_f, humidity
        simple = 0.5 * (T + 61.0 + (T - 68.0) * 1.2 + RH * 0.094)
        if simple < 80:
            return round(simple)
        hi = (-42.379
              + 2.04901523  * T
              + 10.14333127 * RH
              - 0.22475541  * T   * RH
              - 0.00683783  * T   * T
              - 0.05481717  * RH  * RH
              + 0.00122874  * T   * T   * RH
              + 0.00085282  * T   * RH  * RH
              - 0.00000199  * T   * T   * RH  * RH)
        if RH < 13 and 80 <= T <= 112:
            hi -= ((13 - RH) / 4) * math.sqrt((17 - abs(T - 95)) / 17)
        elif RH > 85 and 80 <= T <= 87:
            hi += ((RH - 85) / 10) * ((87 - T) / 5)
        return round(hi)

    return round(temp_f)


# ---------------------------------------------------------------------------
# Main data fetch
# ---------------------------------------------------------------------------

def get_weather_data():
    api_key = os.environ.get("WU_API_KEY", "")
    my_pws  = os.environ.get("MY_PWS_ID", "KCTSTAMF61")
    nearby  = _env_list(
        "NEARBY_PWS_IDS",
        "KCTSTAMF161,KCTSTAMF182,KCTSTAMF152,KCTSTAMF158,KCTNEWCA41,KCTSTAMF117",
    )

    result = {
        "updated":             datetime.now(ET_TZ).strftime("%-I:%M %p ET"),
        "temp":                None,
        "humidity":            None,
        "dewpt":               None,
        "feels_like":          None,
        "wind_speed_avg":      None,
        "wind_gust_avg":       None,
        "wind_dir_deg":        None,
        "wind_dir_compass":    None,
        "wind_stations_count": 0,
        "temp_high":           None,
        "temp_low":            None,
        "forecast_phrase":     None,
        "weather_icon":        "",
        "error":               None,
    }

    # --- Primary station: temperature, humidity ---
    my_obs = fetch_observation(my_pws, api_key)
    if my_obs:
        imp = my_obs.get("imperial", {})
        result["temp"]     = imp.get("temp")
        result["humidity"] = my_obs.get("humidity")
        result["dewpt"]    = imp.get("dewpt")
        lat = my_obs.get("lat")
        lon = my_obs.get("lon")
    else:
        result["error"] = f"No data from {my_pws}"
        lat = lon = None

    # --- Nearby stations: wind aggregation ---
    wind_speeds, wind_gusts, wind_dirs = [], [], []
    for station_id in nearby:
        obs = fetch_observation(station_id, api_key)
        if not obs:
            continue
        imp  = obs.get("imperial", {})
        spd  = imp.get("windSpeed")
        gst  = imp.get("windGust")
        wdir = obs.get("winddir")
        if spd  is not None: wind_speeds.append(spd)
        if gst  is not None: wind_gusts.append(gst)
        if wdir is not None: wind_dirs.append(wdir)

    if wind_speeds:
        result["wind_speed_avg"] = round(sum(wind_speeds) / len(wind_speeds), 1)
    if wind_gusts:
        result["wind_gust_avg"] = round(sum(wind_gusts) / len(wind_gusts), 1)

    mean_dir = circular_mean(wind_dirs)
    if mean_dir is not None:
        result["wind_dir_deg"]     = mean_dir
        result["wind_dir_compass"] = degrees_to_compass(mean_dir)
    result["wind_stations_count"] = len(wind_dirs)

    # --- Feels Like: temp+humidity from MY PWS, wind from nearby average ---
    result["feels_like"] = calculate_feels_like(
        result["temp"], result["humidity"], result["wind_speed_avg"]
    )

    # --- Today's observed high/low (daily summary) ---
    daily = fetch_daily_summary(my_pws, api_key)
    if daily:
        imp = daily.get("imperial", {})
        result["temp_high"] = imp.get("tempHigh")
        result["temp_low"]  = imp.get("tempLow")

    # --- Forecast condition phrase + icon ---
    if lat and lon:
        fc = fetch_forecast(lat, lon, api_key)
        if fc:
            daypart = fc.get("daypart", [{}])[0]
            phrases = daypart.get("wxPhraseLong", [])
            result["forecast_phrase"] = next((p for p in phrases[:2] if p), None)

    hour_et   = datetime.now(ET_TZ).hour
    condition = get_weather_condition(result["forecast_phrase"], hour_et)
    result["weather_icon"] = _svg_img(condition)

    return result
