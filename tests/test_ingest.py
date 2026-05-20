import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import verify_token


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    app.dependency_overrides[verify_token] = lambda: {"sub": "test"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


async def test_ingest_requires_auth():
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post("/ingest")
        assert response.status_code in (401, 403, 422)
    app.dependency_overrides[verify_token] = lambda: {"sub": "test"}


async def test_ingest_rejects_non_pdf(client):
    from io import BytesIO

    fake_txt = BytesIO(b"not a real pdf but has .txt extension")
    files = {"file": ("doc.txt", fake_txt, "text/plain")}
    data = {"tipo_declarado": "inicial"}

    response = await client.post("/ingest", files=files, data=data)
    assert response.status_code == 400


async def test_status_not_found(client):
    response = await client.get("/status/j_nonexistent")
    assert response.status_code == 404


async def test_result_not_found(client):
    response = await client.get("/result/j_nonexistent")
    assert response.status_code == 404
