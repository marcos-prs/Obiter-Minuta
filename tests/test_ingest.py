import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import verify_token


@pytest.fixture
async def client(auth_override):
    """Cliente HTTP com auth mockada. Redis já está mockado via conftest."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def anon_client():
    """Cliente HTTP sem auth (para testar rejeição)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_check(anon_client):
    response = await anon_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


async def test_ingest_requires_auth(anon_client):
    response = await anon_client.post("/ingest")
    assert response.status_code in (401, 403, 422)


async def test_ingest_rejects_non_pdf(client):
    from io import BytesIO
    fake_txt = BytesIO(b"conteudo qualquer")
    files = {"file": ("doc.txt", fake_txt, "text/plain")}
    data = {"tipo_declarado": "inicial"}

    response = await client.post("/ingest", files=files, data=data)
    assert response.status_code == 400


async def test_ingest_rejects_missing_tipo(client):
    from io import BytesIO
    fake_pdf = BytesIO(b"%PDF-1.4 fake content")
    files = {"file": ("peca.pdf", fake_pdf, "application/pdf")}

    response = await client.post("/ingest", files=files)
    assert response.status_code == 422


async def test_status_not_found(client):
    response = await client.get("/status/j_nonexistent")
    assert response.status_code == 404


async def test_result_not_found(client):
    response = await client.get("/result/j_nonexistent")
    assert response.status_code == 404


async def test_delete_job_not_found(client, mock_redis):
    mock_redis.delete.return_value = 0  # nenhuma chave deletada
    response = await client.delete("/job/j_nonexistent")
    assert response.status_code == 404


async def test_delete_job_success(client, mock_redis):
    mock_redis.delete.return_value = 1
    response = await client.delete("/job/j_abc123")
    assert response.status_code == 200
    data = response.json()
    assert data["discarded"] is True


async def test_ingest_success_queues_job(client, mock_redis):
    """PDF valido deve retornar 202, salvar no Redis e enfileirar task sem pdf nos args."""
    from io import BytesIO
    fake_pdf = BytesIO(b"%PDF-1.4 conteudo valido")
    files = {"file": ("peca.pdf", fake_pdf, "application/pdf")}
    data = {"tipo_declarado": "contestacao", "vara": "3a Vara Civel"}

    response = await client.post("/ingest", files=files, data=data)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["job_id"].startswith("j_")
    assert "estimated_seconds" in body

    # PDF deve ter sido salvo no Redis (setex chamado com a chave de PDF)
    calls = [str(c) for c in mock_redis.setex.call_args_list]
    assert any("pdf" in c for c in calls)


async def test_ingest_rejects_oversized_pdf(client):
    """PDF acima de MAX_PDF_SIZE_MB deve retornar 413."""
    from io import BytesIO
    from unittest.mock import patch
    from app.config import Settings

    fake_big_pdf = BytesIO(b"x" * 1024)  # 1KB de conteudo
    files = {"file": ("grande.pdf", fake_big_pdf, "application/pdf")}
    data = {"tipo_declarado": "inicial"}

    # Simula limite de 0MB para forcar rejeicao
    tiny_settings = Settings(max_pdf_size_mb=0)
    with patch("app.routers.ingest.get_settings", return_value=lambda: tiny_settings):
        # Injeta settings com limite zero via dependency override
        from app.config import get_settings
        app.dependency_overrides[get_settings] = lambda: tiny_settings
        response = await client.post("/ingest", files=files, data=data)
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
