import pytest
from unittest.mock import MagicMock, patch
from app.main import app
from app.dependencies import verify_token, get_redis


@pytest.fixture(autouse=True)
def override_redis():
    """Substitui Redis por mock em todos os testes."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = 1
    app.dependency_overrides[get_redis] = lambda: mock_redis
    yield mock_redis
    app.dependency_overrides.pop(get_redis, None)


@pytest.fixture(autouse=True)
def mock_celery_task():
    """Impede conexao real com broker Celery em todos os testes."""
    with patch("app.routers.ingest.process_document") as mock_task:
        mock_task.apply_async.return_value = MagicMock(id="j_test000000")
        yield mock_task


@pytest.fixture
def mock_redis(override_redis):
    """Alias nomeado para testes que precisam configurar o mock Redis."""
    return override_redis


@pytest.fixture
def auth_override():
    """Aplica override de auth e limpa ao final."""
    app.dependency_overrides[verify_token] = lambda: {"sub": "test-client"}
    yield
    app.dependency_overrides.pop(verify_token, None)
