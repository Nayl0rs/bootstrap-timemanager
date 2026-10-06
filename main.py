from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# classe des utilisateurs. est un "BaseModel" de pydantic ; cela permet plusieurs choses, 
# comme la validation des types (python ignore les types au runtime),
# la conversion du JSON reçu en objet (et inversement), etc..
class UserCreate(BaseModel):
    bananes: int
    name: str
    mail: str

# classe qui hérite de "UserCreate". le but est de mettre l'id dans cette classe et pas
# dans UserCreate pour éviter que le client puisse désigner l'id lorsqu'il crée un user.
# on désigne également "response_model=User" si l'on souhaite montrer l'id dans la réponse
class User(UserCreate):
    id: int

# l'app est une instance de la classe FastAPI
app = FastAPI()

# liste d'users (list[dict])
users = [
    {"id": 1,"bananes": 4, "name": "maxime", "mail":"foo@gmail.com"},
    {"id": 2, "bananes": 1, "name": "carl", "mail":"bar@gmail.com"}
]

# @app.get(...) = décorateur. le get fait référence à la méthode HTTP GET (opération). le "/users"
# représente le path (la partie de l'url après le domaine). la fonction en dessous est appelée
# automatiquement par FastAPI lorsqu'une requête GET arrive sur ce path. response_model permet de
# choisir les champs renvoyés au client ; ici, ça montre tous les champs de tous les utilisateurs,
# y compris l'id. si on voulait cacher l'id, on mettrait "UserCreate" à la place (car id est
# dans User qui hérite de UserCreate)
@app.get("/users", response_model=list[User])
async def get_users():
    return users

# ici, on boucle à travers tous les utilisateurs et on prend celui qui correspond au user_id
# présent dans l'input du client (dans l'URL, comme /users/4). on retourne simplement l'user,
# et si on ne trouve rien, on renvoie une erreur HTTP avec code 404 pour not found.
@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    for u in users:
        if u["id"] == user_id:
            return u
    raise HTTPException(status_code=404, detail="user not found")

# 200 -> 299 = success responses. en HTTP, le code 201 correspond à "Created". la fonction
# retourne l'user qui a été créé avec l'id (car User et non UserCreate).
# la 1ère ligne de la fonction prend le plus haut id parmi les users et ajoute 1 (si la liste
# est vide, le default de 0 est utilisé, donc le 1er id sera 1); le programme décide donc
# lui-même de l'id pour être certain qu'il soit unique.
# la 2e ligne AJOUTE l'id créé avec le reste de l'utilisateur créé par le client.
# item.model_dump() est une méthode de Pydantic qui convertit une instance de BaseModel
# en dictionnaire python. le ** qui vient avant "déballe" ce dictionnaire : ses paires
# clé/valeur sont copiées dans le nouveau dict sans avoir à les réécrire à la main. 
# enfin, on ajoute le nouvel utilisateur (ici item_dict, nom à changer) aux users et on le return.
@app.post("/users", status_code=201, response_model=User)
async def create_user(item: UserCreate):
    new_id: int = max((u["id"] for u in users), default=0) + 1
    item_dict = {"id" : new_id, **item.model_dump()}
    users.append(item_dict)
    return item_dict

# ici, pas grand chose de nouveau, mais on met à jour le dictionnaire avec le nouveau qui
# vient de l'input du client (dict.update, une méthode python et non FastAPI). cela remplace
# tous les champs modifiables de l'utilisateur par ceux du client ; l'id, lui, ne change pas
# (il vient de l'URL et n'est pas dans UserCreate). 
# si on voulait mettre à jour seulement UNE valeur, on utiliserait l'opération PATCH.
@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user: UserCreate):
    for u in users:
        if u["id"] == user_id:
            u.update(**user.model_dump())
            return u
    raise HTTPException(status_code=404, detail="user not found")

# ici, on supprime simplement l'utilisateur correspondant à l'id de l'input, avec list.remove(item)
# (users est une liste). le code 204 = "No Content" : la réponse n'a pas de corps, c'est la
# convention REST pour un DELETE réussi. le return arrête la fonction juste après la suppression,
# sinon on tomberait sur l'erreur 404.
@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int):
    for u in users:
        if u["id"] == user_id:
            users.remove(u)
            return
    raise HTTPException(status_code=404, detail="user not found")