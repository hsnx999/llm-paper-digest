from core.config import Config


class TestConfig:
    def test_creates_with_defaults(self):
        cfg = Config()
        assert cfg.LLM_PROVIDER == "groq"
        assert cfg.TOP_N_PAPERS == 10
        assert cfg.DAYS_LOOKBACK == 7

    def test_model_name(self):
        assert Config().model_name == "llama-3.3-70b-versatile"

    def test_effective_categories(self):
        cfg = Config()
        cats = cfg.effective_categories
        assert isinstance(cats, list)
        assert len(cats) >= 4

    def test_effective_topics(self):
        cfg = Config()
        topics = cfg.effective_topics
        assert isinstance(topics, list)
        assert len(topics) >= 4
