from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Base est un "registry". chaque classe qui hérite de base est enregistrée  dans Base.metadata.
# ça permet à create_all de savoir quels tableaux créer, et comment alembic va savoir à quoi
# ressemble le schéma.
class Base(DeclarativeBase):
    pass

# Mapped[int] = colonne de int dans la DB. primary_key représente l'id ;
# la DB fait en sorte que la primary_key soit toujours unique, et jamais NULL.
# apparemment, écrire "name: Mapped[str]" est suffisant si
# il n'y a pas de paramètre particulier dans mapped_column().
# __tablename__ est juste le nom du tableau "users"
class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    bananes: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column()
    mail: Mapped[str] = mapped_column(unique=True)

