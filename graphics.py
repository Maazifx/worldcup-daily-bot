from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

WIDTH = 1080
HEIGHT = 1350

def create_graphic(image_path, headline):

image = Image.open(image_path)

image = image.convert("RGB")

image = image.resize(
    (WIDTH, HEIGHT)
)

draw = ImageDraw.Draw(image)

overlay_height = 420

draw.rectangle(
    (
        0,
        HEIGHT - overlay_height,
        WIDTH,
        HEIGHT
    ),
    fill=(0, 0, 0)
)

draw.rectangle(
    (
        0,
        HEIGHT - overlay_height,
        WIDTH,
        HEIGHT - overlay_height + 110
    ),
    fill=(220, 0, 0)
)

try:

    headline_font = ImageFont.truetype(
        "DejaVuSans-Bold.ttf",
        58
    )

    small_font = ImageFont.truetype(
        "DejaVuSans-Bold.ttf",
        38
    )

except Exception:

    headline_font = ImageFont.load_default()
    small_font = ImageFont.load_default()

draw.text(
    (40, HEIGHT - 390),
    "BREAKING",
    fill="white",
    font=small_font
)

words = headline.split()

lines = []
current = ""

for word in words:

    test = current + " " + word

    if len(test) < 28:
        current = test
    else:
        lines.append(current)
        current = word

lines.append(current)

y = HEIGHT - 250

for line in lines[:3]:

    draw.text(
        (40, y),
        line.strip(),
        fill="white",
        font=headline_font
    )

    y += 70

draw.text(
    (40, HEIGHT - 70),
    "@wcupdates2026",
    fill=(255, 215, 0),
    font=small_font
)

output = "final_news.jpg"

image.save(
    output,
    quality=95
)

return output
