from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import textwrap

WIDTH = 1080
HEIGHT = 1080

BACKGROUND = (8, 18, 40)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)

def create_graphic(headline):

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        BACKGROUND
    )

    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype(
            "arial.ttf",
            90
        )

        headline_font = ImageFont.truetype(
            "arial.ttf",
            75
        )

    except:
        title_font = ImageFont.load_default()
        headline_font = ImageFont.load_default()

    draw.text(
        (60, 80),
        "FIFA WORLD CUP 2026",
        fill=WHITE,
        font=title_font
    )

    wrapped = textwrap.fill(
        headline.upper(),
        width=18
    )

    draw.text(
        (60, 320),
        wrapped,
        fill=WHITE,
        font=headline_font
    )

    draw.text(
        (60, 920),
        "@WORLDCUP2026UPDATES",
        fill=GOLD,
        font=headline_font
    )

    image.save("news_card.png")

    return "news_card.png"
