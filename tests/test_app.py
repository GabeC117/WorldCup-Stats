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


