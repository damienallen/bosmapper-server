import os
from datetime import datetime
from secrets import token_urlsafe

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from mongoengine import connect, errors

from models import (
    EmptyTree,
    GeoJson,
    ImportSpeciesJson,
    ImportUsersJson,
    Species,
    SpeciesDB,
    Tree,
    TreeDB,
    User,
    UsersDB,
)

# Fast API main app
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

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
# TODO: renameDB
connect("trees", host="mongodb://bosmapper_mongo")


# Users & auth
@app.post("/api/users/import/")
def import_users(users_json: ImportUsersJson, request: Request):
    """
    Import users from json
    """

    if not request.headers.get("Master") == os.environ.get("MASTER_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    UsersDB.objects.all().delete()
    for passcode in users_json.passcodes:
        new_user = UsersDB(
            passcode=passcode, token=token_urlsafe(20), token_generated=datetime.now(),
        )
        new_user.save()

    return {"detail": f"Imported {len(users_json.passcodes)} items from passcode list"}


def get_user(token: str):
    try:
        db_user = UsersDB.objects.get(token=token)
        return User(**db_user.to_mongo())

    except UsersDB.DoesNotExist:
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = get_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/api/token/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = UsersDB.objects.get(passcode=form_data.password)

    except UsersDB.DoesNotExist:
        raise HTTPException(status_code=400, detail="Incorrect credentials")

    return {
        "access_token": user.token,
        "token_type": "bearer",
        "token_generated": user.token_generated,
    }


@app.get("/api/users/me/")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# Main app


@app.get("/api/")
def hello():
    return {"Hello": "voedselbos"}


@app.get("/api/trees/")
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
                "notes": tree.notes,
                "tags": tree.tags,
                "dead": tree.dead,
            },
            "geometry": {"type": "Point", "coordinates": [tree.lon, tree.lat]},
        }

        try:
            species = SpeciesDB.objects.get(species=tree.species)
            feature["properties"]["name_la"] = species.name_la
            feature["properties"]["name_nl"] = species.name_nl
            feature["properties"]["name_en"] = species.name_en
        except SpeciesDB.DoesNotExist:
            pass

        features.append(feature)

    return {
        "type": "FeatureCollection",
        "name": "trees",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG:3857"}},
        "features": features,
    }


@app.get("/api/trees/json/")
def trees_json():
    """
    List tree objects in JSON format
    """
    trees = []
    for tree in TreeDB.objects:
        trees.append(Tree.from_mongo(tree))
    return trees


@app.get("/api/trees/clear/")
def remove_all(request: Request):
    """
    Remove all trees
    """
    # Check for master token
    if not request.headers.get("Master") == os.environ.get("MASTER_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    TreeDB.objects.all().delete()
    return {"detail": "All trees removed from collection"}


@app.post("/api/trees/import/")
def import_geojson(geojson: GeoJson, request: Request):
    """
    Import trees from GeoJSON
    """
    if not request.headers.get("Master") == os.environ.get("MASTER_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    TreeDB.objects.all().delete()

    for feature in geojson.features:
        tree = Tree(
            species=feature["properties"].get("species", "onbekend"),
            lon=feature["geometry"]["coordinates"][0],
            lat=feature["geometry"]["coordinates"][1],
            oid=feature["properties"].get("oid"),
            notes=feature["properties"].get("notes"),
            tags=feature["properties"].get("tags", []),
            dead=feature["properties"].get("dead", False),
        )

        new_tree = TreeDB(**tree.to_dict())
        new_tree.save()

    return {"detail": f"Imported {len(geojson.features)} features"}


@app.get("/api/tree/{oid}/")
def get_tree(oid: str):
    """
    Retrieve tree from DB
    """
    try:
        selected_tree = TreeDB.objects.get(id=oid)
        return Tree.from_mongo(selected_tree)
    except TreeDB.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object ID not found"
        )


@app.post("/api/tree/add/")
def add_tree(
    tree: Tree,
    current_user: User = Depends(get_current_active_user),
    status_code=status.HTTP_201_CREATED,
):
    """
    Add trees to DB
    """
    new_tree = TreeDB(**tree.to_dict())
    new_tree.save()
    return {"detail": "New object added", "id": str(new_tree.id)}


@app.post("/api/tree/update/{oid}/")
def update_tree(
    tree: EmptyTree, oid: str, current_user: User = Depends(get_current_active_user)
):
    """
    Update tree DB entry
    """
    print(tree)
    try:
        selected_tree = TreeDB.objects.get(id=oid)

        selected_tree.species = tree.species if tree.species else selected_tree.species
        selected_tree.lat = tree.lat if tree.lat else selected_tree.lat
        selected_tree.lon = tree.lon if tree.lon else selected_tree.lon

        selected_tree.tags = tree.tags if hasattr(tree, "tags") else selected_tree.tags
        selected_tree.dead = tree.dead if hasattr(tree, "dead") else selected_tree.dead

        if tree.notes == "":
            selected_tree.notes = None
        elif tree.notes:
            selected_tree.notes = tree.notes

        selected_tree.save()

        return {"detail": "Object updated", "id": oid}

    except errors.ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object ID"
        )

    except TreeDB.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object ID not found"
        )


@app.post("/api/tree/remove/{oid}/")
def remove_tree(oid: str, current_user: User = Depends(get_current_active_user)):
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


@app.get("/api/species/")
def species_json():
    """
    List species objects in JSON format
    """
    species_list = []
    for species in SpeciesDB.objects:
        species_list.append(Species(**species.to_mongo()))
    return species_list


@app.post("/api/species/import/")
def import_species(species_json: ImportSpeciesJson, request: Request):
    """
    Import trees from GeoJSON
    """
    if not request.headers.get("Master") == os.environ.get("MASTER_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    SpeciesDB.objects.all().delete()

    for item in species_json.species:
        new_species = SpeciesDB(**item)
        new_species.save()

    return {"detail": f"Imported {len(species_json.species)} species"}


@app.post("/api/update_db/")
def update_db(request: Request):
    """
    Update MongoDB
    """
    if not request.headers.get("Master") == os.environ.get("MASTER_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Remove unused field
    TreeDB.objects.all().update(unset__status=1)

    return {"detail": "Done."}
