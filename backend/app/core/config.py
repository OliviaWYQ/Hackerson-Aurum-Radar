from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_ENV: str = "local"
    APP_NAME: str = "Aurum Radar"
    APP_DEBUG: bool = False
    API_PREFIX: str = "/api"

    DATABASE_URL: str

    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET: str = ""
    OSS_ENDPOINT: str = ""

    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = ""
    # model tiering — architecture.md §12
    DASHSCOPE_MODEL_LIGHT: str = "qwen-flash"      # 轻量任务（逐条评估校验）
    DASHSCOPE_MODEL_EXTRACT: str = "qwen-plus"     # 事件抽取
    DASHSCOPE_MODEL_SUMMARY: str = "qwen-plus"     # 研判 / 简报
    DASHSCOPE_MODEL_ACTION: str = "qwen-plus"
    DASHSCOPE_MODEL_REASONING: str = "qwen-max"    # 复杂推理（战略沙盘 / 逻辑审查）

    SCHEDULER_ENABLED: bool = False

    DATA_PROBE_OUTPUT_DIR: str = "../data_probe/output/normalized"


settings = Settings()
