from math import pi
from operator import itemgetter
from pathlib import Path
import numpy as np
import cairo
import json
import pdfkit


current_dir = Path(__file__).resolve().parent

# Constants
DEFAULT_HEIGHT = 2
DEFAULT_RADIUS = 4
MARGIN_TOP = 20
MARGIN_BOTTOM = 10
MARGIN_LEFT = 10
MARGIN_RIGHT = 5
TEXT_MARGIN = 1

COMPASS_LAT = 6783555.3
COMPASS_LON = 493401.8

# TRANSLATION = [0, 0]
# ROTATION_ANGLE = 0

TRANSLATION = [0.45, 1.22]
ROTATION_ANGLE = -144.5 * pi / 180


def decimal_color(r, g, b):
    return [r / 255, g / 255, b / 255]


# Colors
TREE_FILL = decimal_color(77, 115, 67)
TREE_OUTLINE = decimal_color(54, 89, 62)

COLOR_WHITE = decimal_color(255, 255, 255)
COLOR_GREY_70 = decimal_color(179, 179, 179)
COLOR_GREY_80 = decimal_color(203, 203, 203)
COLOR_GREY_90 = decimal_color(230, 230, 230)
COLOR_BLACK = decimal_color(0, 0, 0)


def get_features(geojson_path):
    print(f"Parsing file {geojson_path}")

    with open(geojson_path, "r") as f:
        geojson_data = json.load(f)

    features = geojson_data.get("features")
    print(f"Loaded {len(features)} features")

    return features


def extract_features(feature_list):

    # TODO: calculate these from bounds
    lon_list = [feature["geometry"]["coordinates"][0] for feature in feature_list]
    lat_list = [feature["geometry"]["coordinates"][1] for feature in feature_list]

    min_lon = min(lon_list) - MARGIN_LEFT
    max_lon = max(lon_list) + MARGIN_RIGHT

    min_lat = min(lat_list) - MARGIN_BOTTOM
    max_lat = max(lat_list) + MARGIN_TOP

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

        height = (
            feature["properties"]["height"]
            if feature["properties"]["height"]
            else DEFAULT_HEIGHT
        )
        adjusted_height = height * scale_factor

        trees.append(
            {
                "species": feature["properties"]["species"],
                "x": (feature["geometry"]["coordinates"][1] - min_lat) * scale_factor,
                "y": (feature["geometry"]["coordinates"][0] - min_lon) * scale_factor,
                "radius": adjusted_radius,
                "height": adjusted_height,
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
    return (trees, species_list, scale_factor, min_lon, min_lat)


def draw_background_outline(ctx, scale_factor, trees):
    ctx.save()
    ctx.set_line_width(scale_factor / 5)

    for tree in trees:
        if not tree["species"] == "Onbekend":
            ctx.arc(tree["x"], tree["y"], tree["radius"], 0, pi * 2)
            ctx.set_source_rgb(*TREE_OUTLINE)
            ctx.stroke()

    ctx.restore()


def draw_overlay(ctx, scale_factor, trees):

    for tree in trees:
        ctx.save()
        ctx.set_line_width(scale_factor / 10)
        ctx.set_dash([scale_factor / 3])
        ctx.arc(tree["x"], tree["y"], tree["radius"], 0, pi * 2)
        ctx.set_source_rgb(*TREE_OUTLINE)
        ctx.stroke()
        ctx.restore()

        ctx.save()
        dot_radius = max(tree["radius"] / 14, 0.001)
        ctx.arc(tree["x"], tree["y"], dot_radius, 0, pi * 2)
        ctx.set_source_rgba(*COLOR_BLACK, 0.6)
        ctx.fill()
        ctx.restore()


def fade_white(color, percent):
    color = np.array(color)
    white = np.array([1, 1, 1])
    vector = white - color
    return color + vector * percent


def draw_fills(ctx, scale_factor, trees, species_list):
    min_radius = min([species["radius"] for species in species_list])
    max_radius = max([species["radius"] for species in species_list]) + 0.01
    percent = (trees[0]["radius"] - min_radius) / (max_radius - min_radius)

    fill_color = fade_white(TREE_FILL, percent)

    ctx.save()

    for tree in trees:
        if not tree["species"] == "Onbekend":
            ctx.arc(tree["x"], tree["y"], tree["radius"] - scale_factor / 20, 0, pi * 2)
            ctx.set_source_rgba(*fill_color, 0.75)
            ctx.fill()

    ctx.restore()


def draw_text(ctx, scale_factor, trees, species_list):

    for tree in trees:

        ctx.save()

        min_radius = -25 * scale_factor
        max_radius = 15 * scale_factor
        fill_percent = min((tree["radius"] - min_radius) / (max_radius - min_radius), 1)
        fill_color = fade_white(COLOR_BLACK, 1 - fill_percent)
        ctx.set_source_rgb(*fill_color)

        min_height = -25 * scale_factor
        max_height = 15 * scale_factor
        size_percent = min((tree["height"] - min_height) / (max_height - min_height), 1)
        ctx.set_font_size(1 * scale_factor * size_percent)

        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)

        fascent, fdescent, fheight, fxadvance, fyadvance = ctx.font_extents()
        x_off, y_off, tw, th = ctx.text_extents(tree["species"])[:4]
        nx = -tw / 2.0
        ny = fheight / 2

        ctx.translate(tree["x"], tree["y"])
        ctx.rotate(-ROTATION_ANGLE)
        ctx.translate(nx, ny)
        ctx.move_to(0, TEXT_MARGIN * scale_factor)
        ctx.show_text(tree["species"])

        ctx.restore()


feature_styles = {
    "boundary": {"stroke_color": COLOR_GREY_70, "stroke_width": 0.5},
    "bed": {"fill_color": COLOR_GREY_90},
    "bee_hives": {"fill_color": COLOR_GREY_70},
    "concrete": {"fill_color": COLOR_WHITE},
    "paved": {"fill_color": COLOR_WHITE},
    "greenhouse": {"fill_color": COLOR_GREY_70},
    "misc": {"fill_color": COLOR_GREY_80},
    "tree_ring": {"fill_color": COLOR_GREY_80},
    "wall": {"fill_color": COLOR_GREY_80},
    "vegetation": {"fill_color": COLOR_GREY_90},
    "vegetation_no_wall": {"fill_color": COLOR_GREY_90},
}


def draw_base_features(ctx, base_features, scale_factor, min_lon, min_lat):
    # TODO: break this up, offset paths
    base_features.sort(key=lambda d: d["properties"]["z_index"])

    for feature in base_features:

        feature_type = feature["properties"]["type"]
        style = feature_styles.get(feature_type)

        if not style:
            print(f"Unknown feature type '{feature_type}', skipping...")
            continue

        ctx.save()

        for index, point in enumerate(feature["geometry"]["coordinates"][0]):
            x = (point[1] - min_lat) * scale_factor
            y = (point[0] - min_lon) * scale_factor

            if index == 0:
                ctx.move_to(x, y)
            else:
                ctx.line_to(x, y)

        ctx.close_path()

        fill_color = style.get("fill_color")
        stroke_color = style.get("stroke_color")
        stroke_width = style.get("stroke_width")

        if fill_color:
            ctx.set_source_rgb(*fill_color)
            if stroke_color and stroke_width:
                ctx.fill_preserve()
            else:
                ctx.fill()

        if stroke_color and stroke_width:
            ctx.set_line_width(scale_factor * stroke_width)
            ctx.set_source_rgb(*stroke_color)
            ctx.stroke()

        ctx.restore()


def draw_compass(ctx, scale_factor, min_lon, min_lat):

    ctx.save()

    # Center coordinates
    x = (COMPASS_LAT - min_lat) * scale_factor
    y = (COMPASS_LON - min_lon) * scale_factor

    # Draw arrow
    ctx.move_to(x - 2 * scale_factor, y)
    ctx.line_to(x + 2 * scale_factor, y)
    ctx.line_to(x + 1 * scale_factor, y - 0.5 * scale_factor)

    ctx.set_line_width(scale_factor * 0.15)
    ctx.set_source_rgb(*COLOR_BLACK)
    ctx.stroke()

    ctx.save()

    ctx.restore()

    # Draw N
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(2 * scale_factor)

    fascent, fdescent, fheight, fxadvance, fyadvance = ctx.font_extents()
    x_off, y_off, tw, th = ctx.text_extents("N")[:4]
    nx = -tw / 2.0
    ny = fheight / 2

    ctx.translate(x - 1 * scale_factor, y - 2.2 * scale_factor)
    ctx.rotate(-ROTATION_ANGLE)
    ctx.translate(nx, ny)
    ctx.move_to(0, 0)

    # ctx.move_to(x - 3 * scale_factor, y)
    ctx.show_text("N")

    ctx.restore()


def draw_scale(ctx, scale_factor, min_lon, min_lat):
    ctx.save()
    ctx.restore()


def generate_pdf(svg_path):
    print("Generating PDF version")
    template_dir = current_dir / "template"
    html_path = template_dir / "map.html"
    pdf_path = template_dir / "voedselbos.pdf"

    options = {
        "page-size": "A3",
        "margin-top": "10mm",
        "margin-right": "10mm",
        "margin-bottom": "10mm",
        "margin-left": "10mm",
    }

    pdfkit.from_file(str(html_path), str(pdf_path), options)


def main():
    svg_path = current_dir / "template" / "voedselbos.svg"
    feature_list = get_features(current_dir / "data" / "20200609.geojson")
    base_features = get_features(current_dir / "data" / "base.geojson")

    trees, species_list, scale_factor, min_lon, min_lat = extract_features(feature_list)

    with cairo.SVGSurface(svg_path, 840, 1200) as surface:
        ctx = cairo.Context(surface)
        ctx.scale(1200, 1200)

        # Set background
        ctx.save()
        ctx.set_source_rgb(*COLOR_WHITE)
        ctx.paint()
        ctx.restore()

        # Position canvas
        ctx.translate(*TRANSLATION)
        ctx.rotate(ROTATION_ANGLE)

        print("Drawing base map")
        draw_base_features(ctx, base_features, scale_factor, min_lon, min_lat)

        print(f"Drawing canopy of {len(species_list)} species")
        draw_background_outline(ctx, scale_factor, trees)
        for species in species_list:
            filtered_trees = [
                tree for tree in trees if tree["species"] == species["name"]
            ]
            draw_fills(ctx, scale_factor, filtered_trees, species_list)

        draw_overlay(ctx, scale_factor, trees)
        draw_text(ctx, scale_factor, trees, species_list)
        draw_compass(ctx, scale_factor, min_lon, min_lat)
        draw_scale(ctx, scale_factor, min_lon, min_lat)

    # generate_pdf(svg_path)


if __name__ == "__main__":
    main()
