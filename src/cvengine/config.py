from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """Configuration for the LLM provider used by agents and extraction."""

    model_config = SettingsConfigDict(env_prefix="CVENGINE_LLM_", extra="ignore")

    provider: str = "ollama"
    model: str = "llama3.1:8b"
    temperature: float = 0.0
    base_url: str = "http://localhost:11434"
    api_key: str | None = None


class EmbeddingSettings(BaseSettings):
    """Configuration for the sentence-transformer embedding model."""

    model_config = SettingsConfigDict(env_prefix="CVENGINE_EMBEDDING_", extra="ignore")

    model: str = "nomic-ai/nomic-embed-text-v1.5"
    dimension: int = 768


class ChromaSettings(BaseSettings):
    """Configuration for the Chroma vector database connection."""

    model_config = SettingsConfigDict(env_prefix="CVENGINE_CHROMA_", extra="ignore")

    host: str = "localhost"
    port: int = 8000
    collection: str = "cvs__nomic-embed-text-v1.5__v1"
    test_collection: str = "cvs__nomic-embed-text-v1.5__v1__test"


class ScoringSettings(BaseSettings):
    """Configuration for the hybrid scoring used in search."""

    model_config = SettingsConfigDict(env_prefix="CVENGINE_SCORING_", extra="ignore")

    alpha: float = 0.8
    beta: float = 0.2
    top_k_per_query: int = 30
    default_top_k: int = 20
    rerank_top_n: int = 100


class Settings(BaseSettings):
    """Application settings, loadable from environment or a .env file."""

    model_config = SettingsConfigDict(
        env_prefix="CVENGINE_",
        env_file=".env",
        extra="ignore",
        nested_model_default_partial_update=True,
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)

    data_dir: str = "cvengine_data"
    log_level: str = "INFO"
