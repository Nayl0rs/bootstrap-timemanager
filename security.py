from pwdlib import PasswordHash
from config import settings
from datetime import datetime, timedelta, timezone
import jwt

# PasswordHash.recommended() = l'algorithme de hash conseillé par pwdlib (Argon2). il est volontairement
# lent, pour qu'un attaquant qui volerait la base ne puisse pas tester des millions de mots de passe.
password_hash = PasswordHash.recommended()

# un hash ne peut pas être "déchiffré". chaque appel produit un résultat différent (un "sel" aléatoire
# est ajouté et stocké dans le hash lui-même).
def hash_password(password: str) -> str:
    return password_hash.hash(password)

# re-hache "plain" avec les paramètres et le sel lus dans "hashed", puis compare. renvoie True/False.
def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

# fonction générale qui fabrique n'importe quel token. les 2 fonctions en dessous sont des "préréglages".
def create_token(user_id: int, token_type: str, expires_delta: timedelta) -> str:
    claims: dict = {
        "sub": str(user_id),  # "subject" : à qui appartient le token. DOIT être une chaîne pour PyJWT
        "exp": datetime.now(timezone.utc) + expires_delta,  # date d'expiration ; jwt.decode la vérifie tout seul
        "type": token_type  # "access" ou "refresh" : permet de refuser un refresh token à la place d'un access token
    }
    # signe les claims avec la clé secrète. le payload est lisible par tous (base64), seule la signature est secrète
    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)

def create_access_token(user_id) -> str:
    return create_token(user_id, "access", timedelta(minutes=settings.access_token_expire_minutes))

def create_refresh_token(user_id) -> str:
    return create_token(user_id, "refresh", timedelta(days=settings.refresh_token_expire_days))

# vérifie la signature et l'expiration, puis renvoie les claims. lève jwt.InvalidTokenError si invalide.
# algorithms=[...] est obligatoire : liste blanche des algorithmes acceptés (empêche les tokens "alg: none").
def decode_token(token:str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
