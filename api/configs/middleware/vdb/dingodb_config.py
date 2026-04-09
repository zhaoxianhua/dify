from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings


class DingoDBConfig(BaseSettings):
    """
    Configuration settings for DingoDB vector database
    """

    DINGODB_HOST: str = Field(
        description="Hostname or IP address of the DingoDB server",
        default="localhost",
    )

    DINGODB_PORT: PositiveInt = Field(
        description="Port number on which the DingoDB server is listening",
        default=3307,
    )

    DINGODB_USER: str = Field(
        description="Username for authenticating with DingoDB",
        default="root",
    )

    DINGODB_PASSWORD: str = Field(
        description="Password for authenticating with DingoDB",
        default="",
    )

    DINGODB_DATABASE: str = Field(
        description="Name of the DingoDB database to connect to",
        default="dify",
    )

    DINGODB_MAX_CONNECTION: PositiveInt = Field(
        description="Max connection of the DingoDB database",
        default=5,
    )

    DINGODB_CHARSET: str = Field(
        description="DINGODB_CHARSET parameter for DingoDB",
        default="utf8mb4",
    )
