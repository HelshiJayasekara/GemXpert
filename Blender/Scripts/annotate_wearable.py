"""
Adds the background, title, numbered markers and parts legend to the wearable concept render.

    python3 Blender/Scripts/annotate_wearable.py      (needs Pillow: pip install pillow)

Reads  Blender/Exports/Renders/Wearable_Concept_raw.png and Wearable_Concept_anchors.json
       (written by build_wearable_concept.py)
Writes Blender/Exports/Renders/GemXpert_Motion_Ring_Concept.png
"""
import json
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RENDERS = os.path.join(ROOT, "Blender", "Exports", "Renders")
OUT = os.path.join(RENDERS, "GemXpert_Motion_Ring_Concept.png")

BG = (16, 14, 18)
GOLD = (214, 178, 106)
GOLD_BRIGHT = (236, 205, 140)
TEXT = (232, 226, 216)
MUTED = (150, 143, 135)

# (anchor key, marker offset in px, title, detail)
PARTS = [
    ("sensor", (34, -46), "MPU-9250 sensor (GY-9250 board)", "Measures how the ring turns"),
    ("ring", (40, 18), "3D-printed ring with a flat pad", "Holds the sensor on your finger"),
    ("cable", (-10, 48), "4-wire cable to the wrist", "Red 3.3 V · black GND · yellow SCL (GPIO 22) · green SDA (GPIO 21)"),
    ("esp32", (-70, -52), "ESP32 DevKit", "Reads the sensor, sends the rotation over Bluetooth"),
    ("tp4056", (-60, -58), "TP4056 USB-C charger (protected)", "Charges the battery"),
    ("regulator", (56, -50), "3.3 V regulator", "Steady power for the ESP32 from the battery"),
    ("battery", (40, 70), "3.7 V LiPo, 500-1000 mAh", "Sits under the boards (about 3-4 hours)"),
    ("button", (54, -6), "Recentre button", "Sets the current ring position as straight ahead"),
    ("switch", (64, 34), "On/off slide switch", "Battery power"),
    ("strap", (-58, 30), "Velcro wrist strap", "Carries the pod on your wrist"),
    ("lid", (-60, 40), "Smoked lid (shown open)", "Closes over the electronics"),
]


def font(names, size, index=0):
    for path in names:
        try:
            return ImageFont.truetype(path, size, index=index)
        except OSError:
            continue
    return ImageFont.load_default()


SANS = ["/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf"]
SANS_BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"]
SERIF = ["/System/Library/Fonts/Supplemental/Didot.ttc", "/System/Library/Fonts/Supplemental/Georgia.ttf", "DejaVuSerif.ttf"]


def main():
    raw = Image.open(os.path.join(RENDERS, "Wearable_Concept_raw.png")).convert("RGBA")
    with open(os.path.join(RENDERS, "Wearable_Concept_anchors.json")) as fh:
        anchors = json.load(fh)["anchors"]

    W, H = 2100, 1240
    ox, oy = 0, 150                      # where the render sits on the canvas
    canvas = Image.new("RGBA", (W, H), BG + (255,))
    # soft warm glow behind the device
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((180, 260, 1300, 1150), fill=(70, 52, 30, 90))
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160)))
    canvas.alpha_composite(raw, (ox, oy))
    d = ImageDraw.Draw(canvas)

    f_title = font(SERIF, 54)
    f_sub = font(SANS, 24)
    f_num = font(SANS_BOLD, 20)
    f_item = font(SANS_BOLD, 22)
    f_detail = font(SANS, 18)
    f_foot = font(SANS, 17)

    d.text((60, 46), "GEMXPERT  MOTION RING", font=f_title, fill=GOLD_BRIGHT)
    d.text((62, 112), "Concept: ESP32 + MPU-9250 wearable. Turn the ring and the 3D ring turns in the GemXpert page.",
           font=f_sub, fill=MUTED)
    d.line((60, 146, W - 60, 146), fill=(70, 60, 48), width=1)

    # numbered markers with short leaders
    for i, (key, (dx, dy), _, _) in enumerate(PARTS, 1):
        ax, ay = anchors[key]
        ax, ay = ax + ox, ay + oy
        mx, my = ax + dx, ay + dy
        d.line((ax, ay, mx, my), fill=GOLD, width=2)
        d.ellipse((ax - 4, ay - 4, ax + 4, ay + 4), fill=GOLD)
        r = 17
        d.ellipse((mx - r, my - r, mx + r, my + r), fill=(28, 24, 22), outline=GOLD, width=2)
        d.text((mx, my + 1), str(i), font=f_num, fill=GOLD_BRIGHT, anchor="mm")

    # legend panel
    px, py = 1480, 196
    wrapped = [wrap(detail, f_detail, W - 90 - (px + 46)) for _, _, _, detail in PARTS]
    bottom = py + 34 + sum(64 + 21 * (len(l) - 1) for l in wrapped)
    d.rounded_rectangle((px - 30, py - 30, W - 50, bottom + 6), radius=18,
                        fill=(24, 21, 24), outline=(84, 70, 50), width=1)
    d.text((px, py - 8), "PARTS", font=f_item, fill=GOLD)
    y = py + 34
    for i, (_, _, title, detail) in enumerate(PARTS, 1):
        d.ellipse((px, y, px + 30, y + 30), outline=GOLD, width=2)
        d.text((px + 15, y + 16), str(i), font=f_num, fill=GOLD_BRIGHT, anchor="mm")
        d.text((px + 46, y - 1), title, font=f_item, fill=TEXT)
        lines = wrapped[i - 1]
        for j, line in enumerate(lines):
            d.text((px + 46, y + 27 + 21 * j), line, font=f_detail, fill=MUTED)
        y += 64 + 21 * (len(lines) - 1)

    d.text((60, H - 46), "Concept render built to the planned component list; module sizes follow the real boards. "
           "Not a photo of a built device. The ESP32 and battery sit on the wrist because a DevKit is too big for a ring.",
           font=f_foot, fill=MUTED)
    canvas.convert("RGB").save(OUT, optimize=True)
    print("wrote", OUT, canvas.size)


def wrap(text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if fnt.getlength(trial) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


if __name__ == "__main__":
    main()
