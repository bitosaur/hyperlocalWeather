# hyperlocalWeather

A minimal weather display server designed for the **Kindle Gen 3 (Kindle Keyboard)** experimental browser. Repurposes the e-ink screen as a live, hyperlocal weather dashboard — no JavaScript, no HTML5, no app required.

![layout: weather icon + feels-like temperature, wind compass, today high/low]

---

## What it shows

| Section | Data |
|---|---|
| **Feels Like** | NWS wind chill (≤50 °F) or Rothfusz heat index (≥80 °F) — in large font as centrepiece |
| **Condition icon** | SVG icon: sun, moon, partly cloudy, cloudy, rain, snow, thunderstorm, fog |
| **Actual temp + humidity** | Shown alongside feels-like when temp is outside the 50–80 °F comfort range |
| **Wind compass** | CSS rotating needle — no JavaScript; direction from circular (vector) mean of nearby stations |
| **Wind speed / gusts** | Arithmetic average across nearby stations; missing stations silently ignored |
| **Today high / low** | Observed so far today from your primary PWS |
| **Footer** | Last updated time in Eastern Time, refresh interval |

Temperature and humidity come from your own PWS. Wind comes from a configurable list of nearby stations, combined using the correct **circular (vector) mean** for direction and arithmetic mean for speed/gusts. Feels-like deliberately mixes both sources — your station's temperature with the neighbours' wind — because your station has no anemometer.

---

## Requirements

- Docker + Docker Compose
- A [Weather Underground](https://www.wunderground.com/member/api-keys) personal API key
- Your PWS station ID and a list of nearby station IDs

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/bitosaur/hyperlocalWeather.git
cd hyperlocalWeather

# 2. Create secrets file
cp secrets.env.example secrets.env
```

Edit `secrets.env`:

```env
WU_API_KEY=your_wunderground_api_key_here
MY_PWS_ID=KCTSTAMF61
NEARBY_PWS_IDS=KCTSTAMF161,KCTSTAMF182,KCTSTAMF152,KCTSTAMF158,KCTNEWCA41,KCTSTAMF117
```

```bash
# 3. Start
docker compose up -d

# 4. Open in any browser
http://localhost:5000
```

Point the Kindle browser at `http://<your-server-ip>:5000`.

---

## Configuration

All tuneable settings live in two files — no code changes needed.

### `secrets.env` — sensitive values (never committed to git)

| Variable | Description |
|---|---|
| `WU_API_KEY` | Weather Underground API key |
| `MY_PWS_ID` | Your primary PWS (temperature, humidity, pressure source) |
| `NEARBY_PWS_IDS` | Comma-separated list of nearby stations used for wind data |

### `docker-compose.yml` — runtime settings

| Variable | Default | Description |
|---|---|---|
| `REFRESH_INTERVAL` | `600` | Page auto-refresh in **seconds** (meta http-equiv refresh) |

Change the refresh interval without rebuilding the image — just edit the value and run `docker compose up -d`.

---

## Deploying to another server

```bash
git clone https://github.com/bitosaur/hyperlocalWeather.git
cd hyperlocalWeather
cp secrets.env.example secrets.env
# fill in secrets.env
docker compose up -d
```

The image builds from source in ~30 seconds. No registry required.

---

## Project structure

```
hyperlocalWeather/
├── app/
│   ├── app.py              Flask server with in-memory cache
│   ├── weather.py          WU API calls, circular-mean wind, feels-like, SVG icons
│   └── templates/
│       └── index.html      HTML 4.01 page (Kindle-safe, meta-refresh, CSS compass)
├── requirements.txt
├── Dockerfile              python:3.12-slim, runs gunicorn
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── secrets.env.example     Template — copy to secrets.env and fill in
└── setup.sh                Optional local-dev venv setup (outside Docker)
```

---

## Keeping the Kindle Gen 3 screen awake

By default the Kindle goes to screensaver after a few minutes, interrupting the display. Use the hidden **`~ds` (disable screensaver)** command to prevent this.

### Steps

1. Go to the **Home screen**.
2. Using the keyboard, type **`~ds`** — it will appear in the search bar.
3. Press **Enter** (select "Search everywhere" or similar if prompted).
4. The screen may flicker briefly. The Kindle will no longer enter screensaver mode.

### Important limitations

- **Resets on reboot.** The setting is lost whenever the Kindle restarts or the battery dies completely. You must re-enter `~ds` each time.
- **Battery drain.** With the screen always on and Wi-Fi active for refreshing, battery drains faster than normal. **Keep the Kindle plugged in** while using it as a display.
- **Older firmware only.** This command works on Kindle Gen 3 (Kindle Keyboard) and similarly aged devices. It does not work on newer Kindles.
- **Magnetic cases.** If `~ds` seems to have no effect, check whether you are using a magnetic cover — the magnet can continuously trigger the sleep sensor and override the setting.

### Tip

Set the Kindle's browser **bookmark** to `http://<your-server-ip>:5000` so it opens directly to the weather page after each reboot.

---

## Wind direction — why circular mean?

Wind direction is circular data (0°–360°). A regular arithmetic mean breaks at the North boundary: the average of 350° and 10° arithmetically is 180° (South), when the correct answer is 0° (North). This app uses the **vector (circular) mean**:

1. Convert each direction to unit-vector components (`sin θ`, `cos θ`).
2. Average the components across all reporting stations.
3. Convert back to degrees with `atan2`.

This is the standard meteorological approach and handles the wraparound correctly.

---

## License

MIT
