from sqlalchemy import text


def test_settings_from_env(monkeypatch):
    url = "sqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_ECHO", "0")

    from app import config
    from app.db import database
    assert config.settings.DATABASE_URL == url
    assert str(database.engine.url) == url
    with database.engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_n8n_settings(monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/test")
    monkeypatch.setenv("N8N_API_KEY", "secret")

    from importlib import reload
    from app import config as config_module

    reload(config_module)

    assert config_module.settings.N8N_WEBHOOK_URL == "http://n8n:5678/webhook/test"
    assert config_module.settings.N8N_API_KEY == "secret"
