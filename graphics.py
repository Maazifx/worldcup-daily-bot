from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

WIDTH = 1080
HEIGHT = 1350

def create_graphic(image_path, headline):

    image = Image.open(image_path)
    image = image.convert("RGB")
    image = image.resize((WIDTH, HEIGHT))

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (0, HEIGHT - 420, WIDTH, HEIGHT),
        fill=(0, 0, 0)
    )

    draw.rectangle(
        (0, HEIGHT - 420, WIDTH, HEIGHT - 320),
        fill=(220, 0, 0)
    )

    try:
        headline_font = ImageFont.truetype(
            "DejaVuSans-Bold.ttf",
            58
        )

        small_font = ImageFont.truetype(
            "DejaVuSans-Bold.ttf",
            40
        )

    except Exception:

        headline_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    draw.text(
        (40, HEIGHT - 400),
        "🚨 BREAKING",
        fill="white",
        font=small_font
    )

    words = headline.split()

    lines = []
    current = ""

    for word in words:

        candidate = current + " " + word

        if len(candidate) < 30:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)

    y = HEIGHT - 260

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
