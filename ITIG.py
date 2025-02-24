# ITIG - Info Token Image Generator

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

def format_number(number):
    if number >= 1_000_000_000_000:
        return f"{number / 1_000_000_000_000:.2f}T"
    elif number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.2f}K"
    else:
        return str(number)

def generate_image(mcap, price, volume, supply, change, font_path="fonts/WorkSans-Black.ttf", font_size=36.17):
    positions = {
    "MCAP": (410, 400),  # X, Y for MCAP
    "PRICE": (790, 400),  # X, Y for PRICE
    "VOLUME": (430, 555),  # X, Y for VOLUME
    "SUPPLY": (810, 555),  # X, Y for SUPPLY
    "CHANGE": (620, 728),  # X, Y for CHANGE
    }
    
    img = Image.open("pattern.png")
    draw = ImageDraw.Draw(img)

    font = ImageFont.truetype(font_path, font_size)

    texts = {
        "MCAP": format_number(mcap) + "$",
        "PRICE": format_number(price) + "$",
        "VOLUME": format_number(volume) + "$",
        "SUPPLY": format_number(supply),
        "CHANGE": str(change) + "%",
    }

    for label, text in texts.items():
        bbox = draw.textbbox((0, 0), f"{label}: {text}", font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = positions[label][0] - text_width // 2
        y = positions[label][1] - text_height // 2

        draw.text((x, y), f"{text}", font=font, fill="black")

    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return img_byte_arr
