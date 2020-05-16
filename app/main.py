from fastapi import FastAPI, HTTPException, status
from mongoengine import Document, FloatField, IntField, StringField, connect, errors
from pydantic import BaseModel

# Fast API main app
app = FastAPI()

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


class TreeDB(Document):
    """
    Mongo tree schema
    """

    species = StringField(max_length=60)
    status = IntField()
    lat = FloatField()
    lon = FloatField()
    notes = StringField(max_length=300)


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
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "oid": str(tree.id),
                    "species": tree.species,
                    "status": tree.status,
                    "notes": tree.notes,
                },
                "geometry": {"type": "Point", "coordinates": [tree.lat, tree.lon]},
            }
        )

    return {
        "data": {
            "type": "FeatureCollection",
            "name": "trees",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:EPSG:3857"},
            },
            "features": features,
        }
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
