from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    DEFAULT_CATEGORIES: str = "cs.AI,cs.LG,cs.CL,cs.CV"
    DEFAULT_TOPICS: str = "large language models,agents,RAG,reasoning,multimodal"
    PAPERS_PER_RUN: int = 60
    TOP_N_PAPERS: int = 10
    DAYS_LOOKBACK: int = 7
    OUTPUT_DIR: str = "./output"
    DATA_DIR: str = "./data"
    LOG_LEVEL: str = "INFO"

    @property
    def model_name(self) -> str:
        return "llama-3.3-70b-versatile"

    @property
    def effective_categories(self) -> list[str]:
        return [c.strip() for c in self.DEFAULT_CATEGORIES.split(",") if c.strip()]

    @property
    def effective_topics(self) -> list[str]:
        return [t.strip() for t in self.DEFAULT_TOPICS.split(",") if t.strip()]
