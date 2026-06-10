import os
import requests
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# TheSportsDB public API — no key required
TSDB_SEARCH = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"

_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>World Cup Player Search</title>
  <style>
    body { font-family: sans-serif; max-width: 860px; margin: 40px auto; padding: 0 20px; background: #f9f9f9; }
    h1 { color: #BF5700; }
    form { display: flex; gap: 10px; margin-bottom: 30px; }
    input[type=text] { flex: 1; padding: 10px; font-size: 1rem; border: 1px solid #ccc; border-radius: 4px; }
    button { padding: 10px 20px; background: #BF5700; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1rem; }
    button:hover { background: #a04800; }
    .grid { display: flex; flex-wrap: wrap; gap: 20px; }
    .card { background: white; border: 1px solid #ddd; border-radius: 8px; padding: 16px; width: 180px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
    .card img { width: 120px; height: 120px; object-fit: cover; border-radius: 50%; background: #eee; }
    .card .name { font-weight: bold; margin: 10px 0 4px; font-size: 0.95rem; }
    .card .meta { color: #666; font-size: 0.82rem; line-height: 1.5; }
    .none { color: #888; }
    .error { color: red; }
  </style>
</head>
<body>
  <h1>&#9917; World Cup Player Search</h1>
  <form method="get" action="/">
    <input type="text" name="q" placeholder="Search a player (e.g. Mbappe, Haaland, Messi)..."
           value="{{ query | e }}" autofocus>
    <button type="submit">Search</button>
  </form>

  {% if error %}
    <p class="error">{{ error }}</p>
  {% elif query and players %}
    <div class="grid">
      {% for p in players %}
      <div class="card">
        {% if p.strThumb %}
          <img src="{{ p.strThumb }}" alt="{{ p.strPlayer }}">
        {% else %}
          <img src="" alt="No photo" style="background:#ddd;">
        {% endif %}
        <div class="name">{{ p.strPlayer }}</div>
        <div class="meta">
          {{ p.strNationality or "Unknown" }}<br>
          {{ p.strPosition or "—" }}
        </div>
      </div>
      {% endfor %}
    </div>
  {% elif query %}
    <p class="none">No players found for "{{ query | e }}".</p>
  {% else %}
    <p class="none">Enter a player name above to search.</p>
  {% endif %}

  <p><small>Data: TheSportsDB &nbsp;|&nbsp; <a href="/health">/health</a></small></p>
</body>
</html>
"""


def _search_players(name: str) -> list:
    resp = requests.get(TSDB_SEARCH, params={"p": name}, timeout=10)
    resp.raise_for_status()
    return resp.json().get("player") or []


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    if not query:
        return render_template_string(_HTML, query="", players=[], error=None)
    try:
        players = _search_players(query)
        return render_template_string(_HTML, query=query, players=players, error=None)
    except Exception as exc:
        return render_template_string(_HTML, query=query, players=[], error=str(exc)), 502


@app.route("/api/search")
def search_json():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter ?q="}), 400
    try:
        return jsonify(_search_players(query))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
