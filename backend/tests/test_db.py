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
