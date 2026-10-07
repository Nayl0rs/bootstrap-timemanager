from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# "database" et "models" sont nos propres fichiers (database.py et models.py, dans le même dossier).
# engine = la connexion à PostgreSQL ; get_db = la fonction qui fournit une session par requête.
# Base = le registre de tous les modèles SQLAlchemy ; UserModel = la classe de la table "users".
from database import get_db
from models import UserModel

# --- schémas Pydantic : ce qui circule sur le réseau (JSON), PAS ce qui est dans la base ---

# classe des données envoyées par le client pour créer/modifier un user. est un "BaseModel" de
# pydantic ; cela permet plusieurs choses, comme la validation des types (python ignore les types
# au runtime), la conversion du JSON reçu en objet (et inversement), etc..
# si le client envoie un JSON invalide (ex: "bananes": "abc"), FastAPI renvoie automatiquement
# une erreur 422 sans même appeler notre fonction.
class UserCreate(BaseModel):
    bananes: int
    name: str
    mail: str

# classe qui hérite de "UserCreate". le but est de mettre l'id dans cette classe et pas
# dans UserCreate pour éviter que le client puisse désigner l'id lorsqu'il crée un user.
# on désigne également "response_model=User" si l'on souhaite montrer l'id dans la réponse.
# from_attributes=True : par défaut, pydantic sait lire des dict (obj["name"]) mais pas des objets
# quelconques. avec cette option, il lit aussi les attributs (obj.name), ce qui lui permet de
# convertir un UserModel (objet SQLAlchemy renvoyé par la base) en User (JSON de la réponse).
class User(UserCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

# l'app est une instance de la classe FastAPI
app = FastAPI()

# crée dans PostgreSQL toutes les tables des classes qui héritent de Base (ici "users"),
# mais seulement si elles n'existent pas déjà. ça ne MODIFIE pas une table existante :
# c'est pour ça qu'on passera à Alembic (migrations) plus tard. s'exécute au démarrage du serveur.
# Base.metadata.create_all(bind=engine)
# ^ commented because from now on, alembic is the only thing that creates & changes tables.


# @app.get(...) = décorateur. le get fait référence à la méthode HTTP GET (opération). le "/users"
# représente le path (la partie de l'url après le domaine). la fonction en dessous est appelée
# automatiquement par FastAPI lorsqu'une requête GET arrive sur ce path. response_model permet de
# choisir les champs renvoyés au client ; ici, ça montre tous les champs de tous les utilisateurs,
# y compris l'id. si on voulait cacher l'id, on mettrait "UserCreate" à la place (car id est
# dans User qui hérite de UserCreate).
#
# db: Session = Depends(get_db) : FastAPI appelle get_db() avant la fonction et nous donne la
# session dans "db" (une session = une "conversation" avec la base, propre à cette requête).
# elle est fermée automatiquement après la réponse (le "finally" de get_db).
# on utilise "def" et non "async def" car la session est synchrone : chaque requête SQL bloque
# jusqu'à la réponse de la base. FastAPI exécute les "def" dans des threads séparés, donc le
# serveur reste réactif ; dans un "async def", ça bloquerait tout le serveur.
#
# select(UserModel) = l'équivalent de "SELECT * FROM users". db.scalars(...) l'exécute et
# renvoie des objets UserModel (et non des lignes brutes). .all() les met dans une liste python.
@app.get("/users", response_model=list[User])
def get_users(db: Session = Depends(get_db)):
    return db.scalars(select(UserModel)).all()


# user_id vient de l'URL (/users/4). db.get(Modèle, id) cherche une ligne par sa clé primaire
# et renvoie l'objet, ou None s'il n'existe pas. plus besoin de boucler : la base fait la recherche.
# si on ne trouve rien, on renvoie une erreur HTTP avec code 404 pour not found. le "raise"
# arrête la fonction, donc le "return" n'est atteint que si l'user existe.
# ("is None" et non "== None" : None est un objet unique, on compare l'identité.)
@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    result = db.get(UserModel, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="user not found")
    return result

# 200 -> 299 = success responses. en HTTP, le code 201 correspond à "Created". la fonction
# retourne l'user qui a été créé avec l'id (car User et non UserCreate).
# l'id n'est plus calculé par nous : PostgreSQL le génère tout seul (clé primaire auto-incrémentée).
#
# item.model_dump() est une méthode de Pydantic qui convertit une instance de BaseModel
# en dictionnaire python. le ** qui vient avant "déballe" ce dictionnaire : ses paires
# clé/valeur deviennent des arguments nommés, donc UserModel(**{"name": "a", ...}) revient à
# UserModel(name="a", ...) sans avoir à les réécrire à la main.
#
# db.add(...) met l'objet "en attente" dans la session (rien n'est envoyé à la base).
# db.commit() envoie réellement le INSERT et sauvegarde définitivement ; sans commit, tout
# est annulé à la fermeture de la session. c'est ici que PostgreSQL vérifie les contraintes,
# comme le unique=True sur "mail".
# si le mail existe déjà, la base refuse et SQLAlchemy lève une IntegrityError. on l'attrape
# avec try/except : db.rollback() annule la transaction ratée (obligatoire, sinon la session
# reste inutilisable), puis on renvoie 409 Conflict (la requête entre en conflit avec des
# données existantes). sans ça, le client recevrait un 500 (erreur serveur), ce qui serait faux
# car l'erreur vient du client.
# db.refresh(db_user) recharge l'objet depuis la base : c'est ce qui remplit db_user.id avec
# l'id généré par PostgreSQL.
@app.post("/users", status_code=201, response_model=User)
def create_user(item: UserCreate, db: Session = Depends(get_db)):
    db_user = UserModel(**item.model_dump())
    try:
        db.add(db_user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="mail already exists")

    db.refresh(db_user)
    return db_user

# on récupère l'user en base (404 s'il n'existe pas), puis on remplace tous ses champs par ceux
# du client. user.model_dump().items() donne des paires (clé, valeur), comme ("name", "carl") ;
# setattr(objet, "name", "carl") fait la même chose que objet.name = "carl", mais avec un nom
# d'attribut dynamique, donc une boucle suffit pour les copier tous. l'id, lui, ne change pas
# (il vient de l'URL et n'est pas dans UserCreate).
# les modifications ne sont enregistrées qu'au db.commit(). comme pour le POST, changer le mail
# vers un mail déjà utilisé par quelqu'un d'autre provoque une IntegrityError, d'où le même
# try/except (rollback + 409).
# si on voulait mettre à jour seulement UNE valeur, on utiliserait l'opération PATCH.
@app.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.get(UserModel, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="user not found")
    items = user.model_dump().items()
    for key, value in items:
        setattr(db_user, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="mail already exists")

    db.refresh(db_user)
    return db_user

# on récupère l'user (404 s'il n'existe pas), puis db.delete(...) le met en attente de
# suppression et db.commit() envoie le DELETE à la base. pas de db.refresh ici : la ligne
# n'existe plus, il n'y a rien à recharger. le code 204 = "No Content" : la réponse n'a pas de
# corps, c'est la convention REST pour un DELETE réussi. le return met fin à la fonction
# (None, donc pas de corps).
@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(UserModel, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="user not found")
    db.delete(u)
    db.commit()
    return
