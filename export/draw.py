from math import pi
from operator import itemgetter
from pathlib import Path
import numpy as np
import cairo
import json


current_dir = Path(__file__).resolve().parent

# Constants
DEFAULT_HEIGHT = 2
DEFAULT_RADIUS = 4
MARGIN = 10

FILL_COLOR = [77 / 255, 115 / 255, 67 / 255]
OUTLINE_COLOR = [54 / 255, 89 / 255, 62 / 255]


def get_features():
    geojson_path = current_dir / "data" / "20200530.geojson"
    print(f"Parsing file {geojson_path}")

    with open(geojson_path, "r") as f:
        geojson_data = json.load(f)

    features = geojson_data.get("features")
    print(f"Loaded {len(features)} features")

    return features


def extract_features(feature_list):

    lon_list = [feature["geometry"]["coordinates"][0] for feature in feature_list]
    lat_list = [feature["geometry"]["coordinates"][1] for feature in feature_list]

    min_lon = min(lon_list) - MARGIN
    max_lon = max(lon_list) + MARGIN

    min_lat = min(lat_list) - MARGIN
    max_lat = max(lat_list) + MARGIN

    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat
    scale_factor = 1 / lon_range if lon_range > lat_range else 1 / lat_range

    trees = []
    species_list = []

    for feature in feature_list:
        crown_radius = (
            feature["properties"]["width"]
            if feature["properties"]["width"]
            else DEFAULT_RADIUS
        )
        adjusted_radius = crown_radius / 2 * scale_factor

        trees.append(
            {
                "species": feature["properties"]["species"],
                "x": (feature["geometry"]["coordinates"][1] - min_lat) * scale_factor,
                "y": (feature["geometry"]["coordinates"][0] - min_lon) * scale_factor,
                "radius": adjusted_radius,
            }
        )

        existing_species = [species["name"] for species in species_list]
        if not feature["properties"]["species"] in existing_species:
            height = (
                feature["properties"]["height"]
                if feature["properties"]["height"]
                else DEFAULT_HEIGHT
            )
            species_list.append(
                {
                    "name": feature["properties"]["species"],
                    "radius": adjusted_radius,
                    "height": height,
                }
            )

    species_list = sorted(species_list, key=itemgetter("height"))
    return (trees, species_list, scale_factor)


def draw_background_outline(context, scale_factor, trees):
    context.save()
    context.set_line_width(scale_factor / 5)

    for tree in trees:
        context.arc(tree["x"], tree["y"], tree["radius"], 0, pi * 2)
        context.set_source_rgba(OUTLINE_COLOR[0], OUTLINE_COLOR[1], OUTLINE_COLOR[2], 1)
        context.stroke()

    context.restore()


def draw_overlay(context, scale_factor, trees):

    for tree in trees:
        context.save()
        context.set_line_width(scale_factor / 10)
        context.set_dash([scale_factor / 3])
        context.arc(tree["x"], tree["y"], tree["radius"], 0, pi * 2)
        context.set_source_rgba(OUTLINE_COLOR[0], OUTLINE_COLOR[1], OUTLINE_COLOR[2], 1)
        context.stroke()
        context.restore()

        context.save()
        dot_radius = max(tree["radius"] / 14, 0.001)
        context.arc(tree["x"], tree["y"], dot_radius, 0, pi * 2)
        context.set_source_rgba(0, 0, 0, 0.6)
        context.fill()
        context.restore()


def fade_white(color, percent):
    color = np.array(color)
    white = np.array([1, 1, 1])
    vector = white - color
    return color + vector * percent


def draw_fills(context, scale_factor, trees, species_list):
    min_radius = min([species["radius"] for species in species_list])
    max_radius = max([species["radius"] for species in species_list]) + 0.01
    percent = (trees[0]["radius"] - min_radius) / (max_radius - min_radius)

    fill_color = fade_white(FILL_COLOR, percent)
    print(fill_color)

    context.save()

    for tree in trees:
        context.arc(tree["x"], tree["y"], tree["radius"] - scale_factor / 20, 0, pi * 2)
        context.set_source_rgba(fill_color[0], fill_color[1], fill_color[2], 1)
        context.fill()

    context.restore()


def main():
    feature_list = get_features()
    trees, species_list, scale_factor = extract_features(feature_list)

    svg_path = current_dir / "output" / "example.svg"
    with cairo.SVGSurface(svg_path, 1024, 1024) as surface:
        context = cairo.Context(surface)
        context.scale(1024, 1024)

        # Set background
        context.save()
        context.set_source_rgb(1, 1, 1)
        context.paint()
        context.restore()

        print(f"Drawing canopy of {len(species_list)} species")
        for species in species_list:
            filtered_trees = [
                tree for tree in trees if tree["species"] == species["name"]
            ]
            draw_background_outline(context, scale_factor, filtered_trees)
            draw_fills(context, scale_factor, filtered_trees, species_list)

        draw_overlay(context, scale_factor, trees)


if __name__ == "__main__":
    main()
