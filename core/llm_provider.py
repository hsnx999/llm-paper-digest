from langchain_core.language_models.chat_models import BaseChatModel

from core.config import Config


def get_llm() -> BaseChatModel:
    cfg = Config()
    if not cfg.GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set. Create a .env file with GROQ_API_KEY=gsk_..."
        )

    from langchain_groq import ChatGroq

    return ChatGroq(model=cfg.model_name, temperature=0, groq_api_key=cfg.GROQ_API_KEY)
