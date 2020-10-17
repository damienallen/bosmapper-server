from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    FloatField,
    ListField,
    StringField,
)
from pydantic import BaseModel

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
    oid: str = None
    notes: str = None
    tags: list = []
    dead: bool = False


class Tree(BaseModel):
    species: str
    lat: float
    lon: float
    oid: str = None

    notes: str = None
    tags: list = None
    dead: bool = False

    def to_dict(self):
        return {
            "species": self.species,
            "lat": self.lat,
            "lon": self.lon,
            "notes": self.notes,
            "tags": self.tags,
            "dead": self.dead,
        }

    @staticmethod
    def from_mongo(mongo_tree):
        return Tree(
            species=mongo_tree.species,
            lat=mongo_tree.lat,
            lon=mongo_tree.lon,
            oid=str(mongo_tree.id),
            notes=mongo_tree.notes,
            tags=list(mongo_tree.tags),
            dead=mongo_tree.dead,
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
    lat = FloatField()
    lon = FloatField()

    notes = StringField(max_length=300)
    tags = ListField(StringField(max_length=30), default=list)
    dead = BooleanField(default=False)


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
