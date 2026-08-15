from roomswipe_api.config import Settings


def test_openai_defaults_use_current_flagship_models() -> None:
    settings = Settings(_env_file=None)

    assert settings.openai_image_model == "gpt-image-2"
    assert settings.openai_vision_model == "gpt-5.6-sol"


def test_default_cors_origins_include_vite_development_server() -> None:
    settings = Settings(_env_file=None)

    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins
