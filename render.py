import io
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ICONS = ROOT / "data" / "icons"
ICONS.mkdir(parents=True, exist_ok=True)

BG = (11, 12, 13)
INK = (233, 231, 226)
MUT = (124, 128, 136)
DIM = (74, 77, 84)
BLUE = (91, 140, 255)
RED = (255, 106, 90)
ACC = (216, 242, 74)

FONT_DIR = Path("/usr/share/fonts/TTF")
F_REG = FONT_DIR / "DejaVuSans.ttf"
F_BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"
F_MONO = FONT_DIR / "DejaVuSansMono.ttf"

ROLE_ORDER = {"TOP": 0, "JUNGLE": 1, "MIDDLE": 2, "BOTTOM": 3, "UTILITY": 4}


def by_role(team, team_id):
    return sorted([p for p in team if p["teamId"] == team_id],
                  key=lambda p: ROLE_ORDER.get(p.get("role", ""), 9))


_cdn = {}


def cdn():
    global _cdn
    if not _cdn:
        ver = requests.get("https://ddragon.leagueoflegends.com/api/versions.json",
                           timeout=15).json()[0]
        data = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json",
            timeout=30).json()["data"]
        _cdn = {"ver": ver,
                "by_id": {int(v["key"]): (v["name"], k) for k, v in data.items()}}
    return _cdn


def champion_icon(champion_id):
    name, ddragon_key = cdn()["by_id"].get(champion_id, ("?", "Aatrox"))
    f = ICONS / f"{ddragon_key}.png"
    if not f.exists():
        try:
            url = (f"https://ddragon.leagueoflegends.com/cdn/{cdn()['ver']}"
                   f"/img/champion/{ddragon_key}.png")
            r = requests.get(url, timeout=25)
            if r.status_code == 200:
                f.write_bytes(r.content)
        except Exception:
            pass
    if f.exists():
        return Image.open(f).convert("RGBA")
    return None


def font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except Exception:
        return ImageFont.load_default()


def fit(draw, text, fnt, width):
    if draw.textlength(text, font=fnt) <= width:
        return text
    while text and draw.textlength(text + "…", font=fnt) > width:
        text = text[:-1]
    return text + "…"


def rank_text(entry):
    if not entry:
        return "sem elo"
    return f"{entry['tier'].title()} {entry['rank']} · {entry['leaguePoints']} LP"


def build(game, team, header):
    cdn()
    cell_w, cell_h = 148, 170
    pad_x, top = 10, 74
    W = pad_x * 2 + cell_w * 5
    H = top + cell_h * 2 + 8
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_title = font(F_BOLD, 18)
    f_small = font(F_REG, 11)
    f_name = font(F_REG, 13)
    f_champ = font(F_BOLD, 18)
    f_elo = font(F_MONO, 12)
    f_team = font(F_BOLD, 10)

    d.text((pad_x, 12), header["title"], font=f_title, fill=INK)
    d.text((pad_x, 36), header["sub"], font=f_small, fill=MUT)
    d.line([(pad_x, 52), (W - pad_x, 52)], fill=(40, 42, 46), width=1)


    for ti, team_id in enumerate((100, 200)):
        y0 = top + ti * cell_h
        color = BLUE if team_id == 100 else RED
        label = "AZUL" if team_id == 100 else "VERMELHO"
        d.text((pad_x, y0 - 16), label, font=f_team, fill=color)
        players = [p for p in team if p["teamId"] == team_id]
        for i, p in enumerate(players):
            x = pad_x + i * cell_w
            cx = x + cell_w // 2
            icon = champion_icon(p["championId"])
            if icon:
                icon = icon.resize((74, 74), Image.LANCZOS)
                img.paste(icon, (cx - 37, y0 + 4), icon)
            else:
                d.rectangle([cx - 37, y0 + 4, cx + 37, y0 + 78], outline=color)
            d.text((cx, y0 + 88), fit(d, p["player"], f_name, cell_w - 8),
                   font=f_name, fill=MUT, anchor="ma")
            d.text((cx, y0 + 106), fit(d, p["champ"], f_champ, cell_w - 8),
                   font=f_champ, fill=INK, anchor="ma")
            d.text((cx, y0 + 128), p["elo"], font=f_elo, fill=DIM, anchor="ma")
            d.rectangle([cx - 12, y0 + 148, cx + 12, y0 + 150], fill=color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_vertical(game, team, header):
    cdn()
    W = 550
    pad = 10
    icon = 30
    row_h = 38
    H = 46 + 16 + row_h * 5 + 10 + 16 + row_h * 5 + 8
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_title = font(F_BOLD, 15)
    f_sub = font(F_REG, 10)
    f_team = font(F_BOLD, 9)
    f_champ = font(F_BOLD, 13)
    f_nick = font(F_REG, 11)
    f_elo = font(F_MONO, 10)

    d.text((pad, 8), header["title"], font=f_title, fill=INK)
    d.text((pad, 27), header["sub"], font=f_sub, fill=MUT)
    d.line([(pad, 43), (W - pad, 43)], fill=(40, 42, 46), width=1)

    y = 48
    for team_id in (100, 200):
        color = BLUE if team_id == 100 else RED
        d.text((pad, y), "AZUL" if team_id == 100 else "VERMELHO",
               font=f_team, fill=color)
        y += 16
        for p in by_role(team, team_id):
            ic = champion_icon(p["championId"])
            if ic:
                ic = ic.resize((icon, icon), Image.LANCZOS)
                img.paste(ic, (pad, y + 3), ic)
            else:
                d.rectangle([pad, y + 3, pad + icon, y + 3 + icon], outline=color)
            d.rectangle([pad, y + 3, pad + 3, y + 3 + icon], fill=color)
            tx = pad + icon + 10
            ty = y + (row_h - 14) // 2 - 2
            segs = [(p["champ"], f_champ, INK), (" · ", f_nick, DIM),
                    (p["player"], f_nick, MUT), (" · ", f_nick, DIM),
                    (p["elo"], f_elo, DIM)]
            total = sum(d.textlength(t, font=f) for t, f, _ in segs)
            if total > W - tx - pad:
                p = dict(p)
                while p["player"] and total > W - tx - pad:
                    p["player"] = p["player"][:-1]
                    segs[2] = (p["player"] + "…", f_nick, MUT)
                    total = sum(d.textlength(t, font=f) for t, f, _ in segs)
            x = tx
            for t, f, c in segs:
                d.text((x, ty), t, font=f, fill=c)
                x += d.textlength(t, font=f)
            y += row_h
        y += 10

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_compact(game, team, header):
    cdn()
    W = 400
    pad = 8
    icon = 26
    row_h = 35
    H = pad + 16 + row_h * 5 + 6 + 16 + row_h * 5 + pad
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_team = font(F_BOLD, 9)
    f_champ = font(F_BOLD, 14)
    f_nick = font(F_REG, 11)
    f_elo = font(F_MONO, 10)

    y = pad
    for team_id in (100, 200):
        color = BLUE if team_id == 100 else RED
        d.text((pad, y), "AZUL" if team_id == 100 else "VERMELHO", font=f_team, fill=color)
        y += 16
        for p in by_role(team, team_id):
            ic = champion_icon(p["championId"])
            if ic:
                ic = ic.resize((icon, icon), Image.LANCZOS)
                img.paste(ic, (pad, y + 4), ic)
            d.rectangle([pad, y + 4, pad + 2, y + 4 + icon], fill=color)
            tx = pad + icon + 8
            d.text((tx, y + 2), fit(d, p["champ"], f_champ, W - tx - pad - 90),
                   font=f_champ, fill=INK)
            d.text((W - pad, y + 4), p["elo"], font=f_elo, fill=DIM, anchor="ra")
            d.text((tx, y + 19), fit(d, p["player"], f_nick, W - tx - pad),
                   font=f_nick, fill=MUT)
            y += row_h
        y += 6

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
