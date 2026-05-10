from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Libro de Caja"
    database_url: str = "mysql+pymysql://libro_caja_user:change_me@mysql:3306/libro_caja"
    cors_origins: str = "http://localhost:5173"
    smtp_host: str = "smtp.office365.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    smtp_timeout: int = 30
    report_company_name: str = "Libro de Caja"
    report_logo_path: str = ""
    report_privacy_footer: str = (
        "Información tratada conforme a la normativa vigente de protección de datos. "
        "Este documento es confidencial y está destinado únicamente a su receptor."
    )
    auth_secret: str = "change-this-secret"
    auth_token_expire_minutes: int = 720
    initial_admin_username: str = "admin"
    initial_admin_password: str = "admin123"
    initial_admin_full_name: str = "Administrador"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
