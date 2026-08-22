from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    # Amazon Nova Pro: first-party AWS model, no Anthropic use-case-details
    # approval step, confirmed working with zero setup. Also fits this
    # hackathon's spirit (AWS-run event, AWS's own judges) better than a
    # third-party model. Claude Sonnet 4.5 also ran this pipeline correctly on
    # this account (inference profile us.anthropic.claude-sonnet-4-5-20250929-v1:0,
    # after the one-time Anthropic use-case form). Swap is this one line.
    bedrock_model_id: str = "amazon.nova-pro-v1:0"
    plaid_sandbox_client_id: str = ""
    plaid_sandbox_secret: str = ""
    approval_token_signing_key: str = "dev-only-change-me"
    demo_actor_id: str = "sarla-demo-001"


settings = Settings()
