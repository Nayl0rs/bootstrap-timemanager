from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings

# format : driver://user:password@host:port/database. l'URL vient du .env (pas écrite en dur ici)
DATABASE_URL = settings.database_url

# engine = la connexion à PostgreSQL (un pool de connexions). il ne se connecte qu'au 1er appel réel.
engine = create_engine(DATABASE_URL)
# SessionLocal = une "usine" à sessions : SessionLocal() renvoie une nouvelle session liée à l'engine.
# autoflush=False : SQLAlchemy n'envoie pas les changements en attente à la base tout seul avant une requête.
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# dépendance FastAPI : une session par requête. "yield" donne la session à la route ; le "finally"
# s'exécute APRÈS la réponse, même en cas d'erreur, et ferme la session.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
