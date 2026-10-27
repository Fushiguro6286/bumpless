from bumpless.settings import Settings


def test_empty_env_values_mean_default(monkeypatch):
    # An Action input left empty arrives as NEBIUS_BASE_URL="" and must not replace the default endpoint.
    monkeypatch.setenv("NEBIUS_BASE_URL", "")
    monkeypatch.setenv("MODEL_NANO", "")
    monkeypatch.setenv("MODEL_ULTRA", "nvidia/nemotron-3-ultra-550b-a55b")
    s = Settings.from_env()
    assert s.nebius_base_url == "https://api.tokenfactory.nebius.com/v1/"
    assert s.models["nano"] == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    assert s.models["ultra"] == "nvidia/nemotron-3-ultra-550b-a55b"
