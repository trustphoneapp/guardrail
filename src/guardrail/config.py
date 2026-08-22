from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_region: str = "us-east-1"
    # Amazon Nova Pro: first-party AWS model, no Anthropic use-case-details
    # approval step, confirmed working with zero setup. Also fits this
    # hackathon's spirit (AWS-run event, AWS's own judges) better than a
    # third-party model. Claude Sonnet 4.5/5 both work on this account too (see
    # git history) if you'd rather trade the AWS-native angle for stronger
    # tool-use reasoning — swap back with one line, nothing else changes.
    bedrock_model_id: str = "amazon.nova-pro-v1:0"
    plaid_sandbox_client_id: str = ""
    plaid_sandbox_secret: str = ""
    approval_token_signing_key: str = "dev-only-change-me"
    demo_actor_id: str = "sarla-demo-001"


settings = Settings()
