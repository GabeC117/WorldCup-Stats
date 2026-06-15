import pytest
import responses as rsps_lib
from app import app, TSDB_SEARCH

FAKE_PLAYERS = {
    "player": [
        {
            "idPlayer": "34146370",
            "strPlayer": "Lionel Messi",
            "strNationality": "Argentina",
            "strPosition": "Right Winger",
            "strThumb": "https://example.com/messi.jpg",
            "strCutout": None,
        }
    ]
}


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_index_no_query(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Enter a player name" in r.data


def test_search_missing_query(client):
    r = client.get("/api/search")
    assert r.status_code == 400
    assert "error" in r.get_json()


@rsps_lib.activate
def test_search_json_success(client):
    rsps_lib.add(rsps_lib.GET, TSDB_SEARCH, json=FAKE_PLAYERS, status=200)
    r = client.get("/api/search?q=messi")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert data[0]["strPlayer"] == "Lionel Messi"
    assert data[0]["strNationality"] == "Argentina"


@rsps_lib.activate
def test_search_json_upstream_error(client):
    rsps_lib.add(rsps_lib.GET, TSDB_SEARCH, body=Exception("timeout"))
    r = client.get("/api/search?q=messi")
    assert r.status_code == 502
    assert "error" in r.get_json()


@rsps_lib.activate
def test_index_renders_player_card(client):
    rsps_lib.add(rsps_lib.GET, TSDB_SEARCH, json=FAKE_PLAYERS, status=200)
    r = client.get("/?q=messi")
    assert r.status_code == 200
    assert b"Lionel Messi" in r.data
    assert b"Argentina" in r.data


@rsps_lib.activate
def test_index_no_results(client):
    rsps_lib.add(rsps_lib.GET, TSDB_SEARCH, json={"player": None}, status=200)
    r = client.get("/?q=xyznotaplayer")
    assert r.status_code == 200
    assert b"No players found" in r.data


def test_query_too_long(client):
    r = client.get("/api/search?q=" + "a" * 101)
    assert r.status_code == 400
    assert "too long" in r.get_json()["error"]


def test_query_invalid_characters(client):
    r = client.get("/api/search?q=<script>alert(1)</script>")
    assert r.status_code == 400
    assert "invalid characters" in r.get_json()["error"]


def test_index_query_too_long(client):
    r = client.get("/?q=" + "a" * 101)
    assert r.status_code == 400
    assert b"too long" in r.data
