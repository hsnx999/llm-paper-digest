from loguru import logger

from langchain_core.language_models.chat_models import BaseChatModel

from core.config import Config


def get_llm() -> BaseChatModel:
    cfg = Config()

    from langchain_groq import ChatGroq

    if not cfg.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set. Attempting to use Groq without explicit key.")
    return ChatGroq(model=cfg.model_name, temperature=0, groq_api_key=cfg.GROQ_API_KEY)
