from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from mongoengine import connect, Document, StringField, FloatField, errors


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

    def to_dict(self):
        return {
            "species": self.species,
            "lat": self.lat,
            "lon": self.lon,
            "notes": self.notes,
        }

    @staticmethod
    def from_mongo(mongo_tree):
        return Tree(
            species=mongo_tree.species,
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
    lat = FloatField()
    lon = FloatField()
    notes = StringField(max_length=300)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/trees/")
def trees_geojson():
    """
    List tree objects in JSON format
    """
    features = []
    for tree in TreeDB.objects:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "oid": str(tree.id),
                    "species": tree.species,
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
def list_trees():
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


@app.post("/tree/remove/{oid}/")
def remove_tree(oid: str):
    """
    Remove trees from DB
    """
    try:
        tree = TreeDB.objects.get(id=oid)
        tree.delete()

    except errors.ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object ID"
        )

    except errors.ValidationError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object ID not found"
        )

    return {"detail": f"Object '{tree.id}' was removed"}
