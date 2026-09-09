"""生成多模态测试图片（验证码、文字提取、元素识别、几何图等，全部原创）"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "images"
OUT.mkdir(parents=True, exist_ok=True)

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_EN = "C:/Windows/Fonts/arialbd.ttf"
FONT_MONO = "C:/Windows/Fonts/consola.ttf"


def make_captcha(text: str, filename: str) -> None:
    w, h = 220, 90
    img = Image.new("RGB", (w, h), (245, 246, 250))
    draw = ImageDraw.Draw(img)
    random.seed(text)
    # 噪点
    for _ in range(260):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        c = random.randint(90, 200)
        draw.point((x, y), fill=(c, c, c))
    # 干扰线
    for _ in range(6):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line((x1, y1, x2, y2), fill=(120, 120, 130), width=2)
    # 文字（带随机偏移/旋转）
    font = ImageFont.truetype(FONT_EN, 46)
    x = 18
    for ch in text:
        c = random.randint(20, 90)
        img2 = Image.new("RGBA", (60, 70), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(img2)
        d2.text((0, 0), ch, font=font, fill=(c, c, c))
        img2 = img2.rotate(random.randint(-12, 12), expand=False)
        img.paste(img2, (x, random.randint(8, 22)), img2)
        x += 46
    img.save(OUT / filename)
    print("saved", filename)


def make_text_image(text: str, filename: str, bg=(255, 255, 255), fg=(20, 20, 20), font_path=FONT_CN, size=64) -> None:
    font = ImageFont.truetype(font_path, size)
    tmp = Image.new("RGB", (10, 10))
    td = ImageDraw.Draw(tmp)
    bbox = td.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0] + 60, bbox[3] - bbox[1] + 60
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    draw.text((30 - bbox[0], 30 - bbox[1]), text, font=font, fill=fg)
    img.save(OUT / filename)
    print("saved", filename)


def make_element_tile(symbol: str, number: int, name: str, color: tuple, filename: str) -> None:
    img = Image.new("RGB", (320, 360), (250, 250, 245))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((20, 20, 300, 340), radius=24, fill=color, outline=(80, 80, 80), width=3)
    draw.text((40, 36), str(number), font=ImageFont.truetype(FONT_EN, 34), fill=(40, 40, 40))
    draw.text((48, 110), symbol, font=ImageFont.truetype(FONT_EN, 96), fill=(30, 30, 30))
    draw.text((44, 260), name, font=ImageFont.truetype(FONT_CN, 40), fill=(60, 60, 60))
    img.save(OUT / filename)
    print("saved", filename)


def make_triangle(filename: str) -> None:
    img = Image.new("RGB", (420, 340), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    a, b, c = (40, 280), (40, 80), (340, 80)  # 直角在 B
    draw.polygon([a, b, c], outline=(30, 30, 30), width=4)
    draw.text((16, 180), "4", font=ImageFont.truetype(FONT_EN, 30), fill=(200, 30, 30))
    draw.text((185, 92), "3", font=ImageFont.truetype(FONT_EN, 30), fill=(200, 30, 30))
    draw.text((185, 200), "5", font=ImageFont.truetype(FONT_EN, 30), fill=(30, 90, 200))
    draw.rectangle((b[0] - 8, b[1] - 8, b[0] + 8, b[1] + 8), outline=(30, 30, 30), width=2)
    img.save(OUT / filename)
    print("saved", filename)


if __name__ == "__main__":
    make_captcha("7K3P", "captcha1.png")
    make_captcha("M9XQ", "captcha2.png")
    make_text_image("人工智能改变世界", "text_cn.png")
    make_text_image("WELCOME TO BEIJING", "text_en.png", bg=(24, 62, 128), fg=(255, 255, 255), font_path=FONT_EN, size=58)
    make_element_tile("Au", 79, "金 Gold", (255, 215, 0), "element_gold.png")
    make_triangle("triangle_345.png")
