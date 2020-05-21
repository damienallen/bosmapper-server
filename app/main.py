from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from mongoengine import Document, FloatField, IntField, StringField, connect, errors
from pydantic import BaseModel

# Fast API main app
app = FastAPI()

# Handle CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to mongo
connect("trees", host="mongodb://bosmapper_mongo")


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


class SpeciesJson(BaseModel):
    species: list
    updated: str


class Species(BaseModel):
    abbr: str
    species: str
    name_nl: str = None
    name_en: str = None
    width: float = None
    height: float = None


class SpeciesDB(Document):
    """
    Mongo species schema
    """

    abbr = StringField(max_length=60)
    species = StringField(max_length=60)
    name_nl = StringField(max_length=60)
    name_en = StringField(max_length=60)
    width = FloatField(null=True)
    height = FloatField(null=True)


@app.get("/")
def hello():
    return {"Hello": "voedselbos"}


@app.get("/trees/")
def trees_geojson():
    """
    List tree objects in GeoJSON format
    """
    features = []
    for tree in TreeDB.objects:
        feature = {
            "type": "Feature",
            "properties": {
                "oid": str(tree.id),
                "species": tree.species,
                "status": tree.status,
                "notes": tree.notes,
            },
            "geometry": {"type": "Point", "coordinates": [tree.lon, tree.lat]},
        }

        try:
            species = SpeciesDB.objects.get(abbr=tree.species)
            feature["properties"]["name_sci"] = species.species
            feature["properties"]["name_nl"] = species.name_nl
            feature["properties"]["name_en"] = species.name_en
        except SpeciesDB.DoesNotExist:
            pass

        features.append(feature)

    return {
        "type": "FeatureCollection",
        "name": "trees",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG:3857"},},
        "features": features,
    }


@app.get("/trees/json/")
def trees_json():
    """
    List tree objects in JSON format
    """
    trees = []
    for tree in TreeDB.objects:
        trees.append(Tree.from_mongo(tree))
    return trees


@app.get("/trees/clear/")
def remove_all():
    """
    Remove all trees
    """
    TreeDB.objects.all().delete()
    return {"detail": "All trees removed from collection"}


@app.post("/trees/import/")
def import_geojson(geojson: GeoJson):
    """
    Import trees from GeoJSON
    """
    for feature in geojson.features:
        tree = Tree(
            species=feature["properties"].get("species", "onbekend"),
            status=feature["properties"].get("status", 3),
            lon=feature["geometry"]["coordinates"][0],
            lat=feature["geometry"]["coordinates"][1],
            notes=feature["properties"].get("notes"),
            oid=feature["properties"].get("oid"),
        )

        new_tree = TreeDB(**tree.to_dict())
        new_tree.save()

    return {"detail": f"Imported {len(geojson.features)} features"}


@app.post("/tree/add/")
def add_tree(tree: Tree, status_code=status.HTTP_201_CREATED):
    """
    Add trees to DB
    """
    new_tree = TreeDB(**tree.to_dict())
    new_tree.save()
    return {"detail": "New object added", "id": str(new_tree.id)}


@app.post("/tree/update/{oid}/")
def update_tree(tree: Tree, oid: str):
    """
    Update tree DB entry
    """
    try:
        updated_tree = TreeDB.objects.get(id=oid)
        updated_tree.species = tree.species
        updated_tree.status = tree.status
        updated_tree.lat = tree.lat
        updated_tree.lon = tree.lon
        updated_tree.notes = tree.notes
        updated_tree.save()

        return {"detail": "Object updated", "id": oid}

    except errors.ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object ID"
        )

    except TreeDB.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object ID not found"
        )


@app.post("/tree/remove/{oid}/")
def remove_tree(oid: str):
    """
    Remove trees from DB
    """
    try:
        tree = TreeDB.objects.get(id=oid)
        tree.delete()

        return {"detail": "Object removed", "id": oid}

    except errors.ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object ID"
        )

    except TreeDB.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object ID not found"
        )


@app.get("/species/")
def species_json():
    """
    List species objects in JSON format
    """
    species_list = []
    for species in SpeciesDB.objects:
        species_list.append(Species(**species.to_mongo()))
    return species_list


@app.post("/species/import/")
def import_species(species_json: SpeciesJson):
    """
    Import trees from GeoJSON
    """
    SpeciesDB.objects.all().delete()

    for item in species_json.species:
        new_species = SpeciesDB(**item)
        new_species.save()

    return {"detail": f"Imported {len(species_json.species)} species"}
