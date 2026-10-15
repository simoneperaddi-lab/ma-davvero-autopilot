import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("I test non devono usare rete, credenziali reali o servizi a pagamento.")
    monkeypatch.setattr("socket.socket.connect", blocked)
    monkeypatch.setattr("socket.getaddrinfo", blocked)


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, mad_data_dir=tmp_path, mad_provider="demo", mad_storage="sqlite", mad_auth_mode="local")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), client=("127.0.0.1", 50000)) as client:
        yield client
