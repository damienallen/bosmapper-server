from mongoengine import (
    Document,
    BooleanField,
    DateTimeField,
    FloatField,
    IntField,
    StringField,
)
from pydantic import BaseModel
from datetime import datetime

# Users & auth


class ImportUsersJson(BaseModel):
    passcodes: list


class User(BaseModel):
    passcode: str
    token: str
    token_generated: datetime
    disabled: bool = False


class UsersDB(Document):
    """
    Mongo user schema
    """

    passcode = StringField(max_length=30)
    token = StringField(max_length=30)
    token_generated = DateTimeField()
    disabled = BooleanField()


# Features


class EmptyTree(BaseModel):
    species: str = None
    lat: float = None
    lon: float = None
    notes: str = None
    oid: str = None
    status: int = None


class Tree(BaseModel):
    species: str
    lat: float
    lon: float
    notes: str = None
    oid: str = None

    # Status of tree health
    # 0 dead -> 1 bad -> 2 okay -> 3 good
    status: int = 3

    def to_dict(self):
        return {
            "species": self.species,
            "status": self.status,
            "lat": self.lat,
            "lon": self.lon,
            "notes": self.notes,
        }

    @staticmethod
    def from_mongo(mongo_tree):
        return Tree(
            species=mongo_tree.species,
            status=mongo_tree.status,
            lat=mongo_tree.lat,
            lon=mongo_tree.lon,
            notes=mongo_tree.notes,
            oid=str(mongo_tree.id),
        )


# TODO: proper types
class GeoJson(BaseModel):
    name: str
    features: list


class TreeDB(Document):
    """
    Mongo tree schema
    """

    species = StringField(max_length=60)
    status = IntField()
    lat = FloatField()
    lon = FloatField()
    notes = StringField(max_length=300)


class ImportSpeciesJson(BaseModel):
    species: list
    updated: str


class Species(BaseModel):
    species: str
    name_la: str
    name_nl: str = None
    name_en: str = None
    width: float = None
    height: float = None


class SpeciesDB(Document):
    """
    Mongo species schema
    """

    species = StringField(max_length=60)
    name_la = StringField(max_length=60)
    name_nl = StringField(max_length=60)
    name_en = StringField(max_length=60)
    width = FloatField(null=True)
    height = FloatField(null=True)
