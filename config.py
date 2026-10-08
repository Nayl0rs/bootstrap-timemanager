from pydantic_settings import BaseSettings, SettingsConfigDict

# lit les variables de configuration (du fichier .env ou de l'environnement) et les valide.
# chaque attribut correspond à une variable, sans tenir compte des majuscules : database_url <- DATABASE_URL.
# si une variable obligatoire manque, Settings() échoue au démarrage avec un message clair.
class Settings(BaseSettings):
    database_url: str  # obligatoire (pas de valeur par défaut) : doit être dans le .env
    secret_key: str    # obligatoire : sert à signer les JWT (openssl rand -hex 32). ne JAMAIS la committer
    # env_file = fichier à lire. extra="ignore" : sans ça, les variables du .env qu'on ne déclare pas
    # ici (POSTGRES_USER...) feraient planter. le chemin ".env" est relatif au dossier d'où on lance la commande.
    model_config = SettingsConfigDict(env_file = ".env", extra = "ignore")
    algorithm: str = "HS256"  # les champs avec une valeur par défaut sont optionnels dans le .env
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

settings = Settings() # type: ignore[call-arg]  # une seule instance, importée partout (from config import settings)
