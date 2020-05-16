from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Tree(BaseModel):
    species: str
    lat: float
    lon: float
    notes: str = None


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/tree/add/")
def add_tree(tree: Tree):
    return tree
