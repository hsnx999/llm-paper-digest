from langchain_core.language_models.chat_models import BaseChatModel

from core.config import Config


def get_llm() -> BaseChatModel:
    cfg = Config()

    from langchain_groq import ChatGroq

    return ChatGroq(model=cfg.model_name, temperature=0, groq_api_key=cfg.GROQ_API_KEY)
