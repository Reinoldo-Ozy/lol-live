import io

from PIL import Image, ImageDraw, ImageFont

import render

BG = render.BG
INK = render.INK
MUT = render.MUT
DIM = render.DIM
BLUE = render.BLUE
RED = render.RED
ACC = render.ACC

F_REG, F_BOLD, F_MONO = render.F_REG, render.F_BOLD, render.F_MONO
font = render.font
fit = render.fit
icon_of = render.champion_icon

W = 400


def _sides(team):
    return render.by_role(team, 100), render.by_role(team, 200)


def _canvas(h):
    img = Image.new("RGB", (W, h), BG)
    return img, ImageDraw.Draw(img)


def _buf(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b


def _icon(img, cid, x, y, size, color):
    ic = icon_of(cid)
    if ic:
        ic = ic.resize((size, size), Image.LANCZOS)
        img.paste(ic, (x, y), ic)
    else:
        ImageDraw.Draw(img).rectangle([x, y, x + size, y + size], outline=color)


def style_1(team, avg=None):
    rows, d = None, None
    h = 8 + 16 + 35 * 5 + 6 + 16 + 35 * 5 + 8
    img, d = _canvas(h)
    fc, fn, fe, ft = font(F_BOLD, 14), font(F_REG, 11), font(F_MONO, 10), font(F_BOLD, 9)
    y = 8
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((8, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += 16
        for p in render.by_role(team, tid):
            _icon(img, p["championId"], 8, y + 4, 26, col)
            d.rectangle([8, y + 4, 10, y + 30], fill=col)
            tx = 42
            d.text((tx, y + 2), fit(d, p["champ"], fc, W - tx - 100), font=fc, fill=INK)
            d.text((W - 8, y + 4), p["elo"], font=fe, fill=DIM, anchor="ra")
            d.text((tx, y + 19), fit(d, p["player"], fn, W - tx - 8), font=fn, fill=MUT)
            y += 35
        y += 6
    return img


def style_2(team, avg=None):
    h = 8 + 14 + 30 * 5 + 4 + 14 + 30 * 5 + 8
    img, d = _canvas(h)
    fc, fn, fe, ft = font(F_BOLD, 12), font(F_REG, 10), font(F_MONO, 9), font(F_BOLD, 8)
    y = 8
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((8, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += 14
        for p in render.by_role(team, tid):
            _icon(img, p["championId"], 8, y + 3, 22, col)
            tx = 36
            nick = p["player"]
            segs = [(p["champ"], fc, INK), (" · ", fn, DIM), (nick, fn, MUT),
                    (" · ", fn, DIM), (p["elo"], fe, DIM)]
            avail = W - tx - 8
            total = sum(d.textlength(t, font=f) for t, f, _ in segs)
            while total > avail and len(nick) > 3:
                nick = nick[:-1]
                segs[2] = (nick + "…", fn, MUT)
                total = sum(d.textlength(t, font=f) for t, f, _ in segs)
            x = tx
            for t, f, c in segs:
                d.text((x, y + 6), t, font=f, fill=c)
                x += d.textlength(t, font=f)
            y += 30
        y += 4
    return img


def style_3(team, avg=None):
    a, b = _sides(team)
    h = 8 + 16 + 44 * 5 + 8
    img, d = _canvas(h)
    fc, fn, fe, ft = font(F_BOLD, 10), font(F_REG, 8), font(F_MONO, 8), font(F_BOLD, 8)
    for ci, (rows, col, name) in enumerate(((a, BLUE, "AZUL"), (b, RED, "VERMELHO"))):
        x0 = 6 + ci * 197
        d.text((x0, 6), name, font=ft, fill=col)
        y = 20
        for p in rows:
            _icon(img, p["championId"], x0, y + 2, 18, col)
            d.text((x0 + 22, y), fit(d, p["champ"], fc, 168), font=fc, fill=INK)
            d.text((x0 + 22, y + 13), fit(d, p["player"], fn, 168), font=fn, fill=MUT)
            d.text((x0 + 22, y + 24), p["elo"], font=fe, fill=DIM)
            y += 44
    return img


def style_4(team, avg=None):
    h = 8 + 16 + 96 * 2 + 10
    img, d = _canvas(h)
    fc, fn, fe, ft = font(F_BOLD, 9), font(F_REG, 7), font(F_MONO, 7), font(F_BOLD, 8)
    for ti, tid in enumerate((100, 200)):
        col = BLUE if tid == 100 else RED
        d.text((8, 8 + ti * 104), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        for i, p in enumerate(render.by_role(team, tid)):
            cx = 8 + i * 77
            yy = 22 + ti * 104
            _icon(img, p["championId"], cx, yy, 44, col)
            d.text((cx, yy + 46), fit(d, p["champ"], fc, 72), font=fc, fill=INK)
            d.text((cx, yy + 58), fit(d, p["player"], fn, 72), font=fn, fill=MUT)
            d.text((cx, yy + 70), p["elo"], font=fe, fill=DIM)
    return img


def style_5(team, avg=None):
    h = 8 + 16 + 34 * 5 + 6 + 16 + 34 * 5 + 8
    img, d = _canvas(h)
    fe, fc, fn, ft = font(F_MONO, 9), font(F_BOLD, 13), font(F_REG, 10), font(F_BOLD, 9)
    y = 8
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((8, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += 16
        for p in render.by_role(team, tid):
            d.text((8, y + 9), p["elo"], font=fe, fill=DIM)
            _icon(img, p["championId"], 78, y + 3, 26, col)
            d.text((110, y + 5), fit(d, p["champ"], fc, 130), font=fc, fill=INK)
            d.text((110 + 132, y + 7), fit(d, p["player"], fn, 150), font=fn, fill=MUT)
            y += 34
        y += 6
    return img


def style_6(team, avg=None):
    order = {"TOP": 0, "JUNGLE": 1, "MIDDLE": 2, "BOTTOM": 3, "UTILITY": 4}
    rows = sorted(team, key=lambda p: order.get(p.get("role", ""), 9))
    h = 8 + 16 + 32 * 5 + 2 + 16 + 32 * 5 + 8
    img, d = _canvas(h)
    fr, fc, fn, fe, ft = font(F_BOLD, 7), font(F_BOLD, 12), font(F_REG, 10), font(F_MONO, 9), font(F_BOLD, 8)
    y = 8
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((8, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += 16
        for p in [x for x in rows if x["teamId"] == tid]:
            d.text((8, y + 8), (p.get("role") or "")[:3], font=fr, fill=col)
            _icon(img, p["championId"], 34, y + 3, 24, col)
            d.text((62, y + 4), fit(d, p["champ"], fc, 120), font=fc, fill=INK)
            d.text((62, y + 17), fit(d, p["player"], fn, 200), font=fn, fill=MUT)
            d.text((W - 8, y + 6), p["elo"], font=fe, fill=DIM, anchor="ra")
            y += 32
        y += 2
    return img


def style_7(team, avg=None):
    h = 8 + 16 + 34 * 5 + 6 + 16 + 34 * 5 + 8
    img, d = _canvas(h)
    fc, fn, fe, ft = font(F_BOLD, 13), font(F_REG, 10), font(F_MONO, 9), font(F_BOLD, 9)
    y = 8
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((8, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += 16
        for i, p in enumerate(render.by_role(team, tid)):
            if i % 2 == 0:
                d.rectangle([4, y, W - 4, y + 33], fill=(17, 18, 20))
            _icon(img, p["championId"], 8, y + 4, 24, col)
            d.text((38, y + 2), fit(d, p["champ"], fc, 150), font=fc, fill=INK)
            d.text((38, y + 17), fit(d, p["player"], fn, 200), font=fn, fill=MUT)
            d.text((W - 10, y + 8), p["elo"], font=fe, fill=col if "sem" not in p["elo"] else DIM, anchor="ra")
            y += 34
        y += 6
    return img


def style_8(team, avg=None):
    h = 8 + 14 + 28 * 10 + 8
    img, d = _canvas(h)
    fc, fn, ft = font(F_BOLD, 13), font(F_REG, 9), font(F_BOLD, 8)
    y = 8
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((8, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += 14
        for p in render.by_role(team, tid):
            _icon(img, p["championId"], 8, y + 2, 24, col)
            d.text((38, y + 5), fit(d, p["champ"], fc, 180), font=fc, fill=INK)
            d.text((W - 8, y + 8), fit(d, p["player"], fn, 150), font=fn, fill=MUT, anchor="ra")
            y += 28
    return img


def style_9(team, avg=None):
    h = 8 + 18 + 34 * 5 + 6 + 18 + 34 * 5 + 6
    img, d = _canvas(h)
    fc, fn, fe, ft = font(F_BOLD, 12), font(F_REG, 9), font(F_MONO, 9), font(F_BOLD, 9)
    y = 8
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.rectangle([4, y, W - 4, y + 15], fill=col)
        d.text((8, y + 3), ("AZUL" if tid == 100 else "VERMELHO"), font=ft, fill=(11, 12, 13))
        if avg:
            d.text((W - 8, y + 4), avg[tid], font=fe, fill=(11, 12, 13), anchor="ra")
        y += 18
        for p in render.by_role(team, tid):
            _icon(img, p["championId"], 8, y + 3, 26, col)
            d.text((42, y + 4), fit(d, p["champ"], fc, 150), font=fc, fill=INK)
            d.text((42, y + 19), fit(d, p["player"], fn, 200), font=fn, fill=MUT)
            d.text((W - 8, y + 10), p["elo"], font=fe, fill=DIM, anchor="ra")
            y += 34
        y += 6
    return img


def style_10(team, avg=None):
    a, b = _sides(team)
    h = 8 + 16 + 40 * 5 + 8
    img, d = _canvas(h)
    fc, fn, fe, ft = font(F_BOLD, 10), font(F_REG, 8), font(F_MONO, 8), font(F_BOLD, 8)
    for ci, (rows, col, name) in enumerate(((a, BLUE, "AZUL"), (b, RED, "VERMELHO"))):
        x0 = 6 + ci * 197
        d.rectangle([x0, 6, x0 + 190, 20], fill=col)
        d.text((x0 + 4, 8), name, font=ft, fill=(11, 12, 13))
        y = 24
        for p in rows:
            _icon(img, p["championId"], x0, y, 18, col)
            d.text((x0 + 22, y + 1), fit(d, p["champ"], fc, 90), font=fc, fill=INK)
            d.text((x0 + 22, y + 12), fit(d, p["player"], fn, 168), font=fn, fill=MUT)
            y += 40
    return img


STYLES = {
    1: ("linha dupla", style_1),
    2: ("linha unica", style_2),
    3: ("duas colunas", style_3),
    4: ("grade de cards", style_4),
    5: ("elo a esquerda", style_5),
    6: ("por posicao", style_6),
    7: ("linhas zebradas", style_7),
    8: ("minimalista", style_8),
    9: ("placar com media", style_9),
    10: ("colunas com faixa", style_10),
}


def build(style, team, avg=None):
    img = STYLES[style][1](team, avg)
    return _buf(img)


def style_6_hd(team, avg=None):
    S = 2
    W2 = W * S
    pad = 8 * S
    row = 32 * S
    h = (8 + 16 + 32 * 5 + 2 + 16 + 32 * 5 + 8) * S
    img = Image.new("RGB", (W2, h), BG)
    d = ImageDraw.Draw(img)
    fr = font(F_BOLD, 7 * S)
    fc = font(F_BOLD, 12 * S)
    fn = font(F_REG, 10 * S)
    fe = font(F_MONO, 9 * S)
    ft = font(F_BOLD, 8 * S)
    nick_col = (150, 155, 164)
    y = pad
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((pad, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += 16 * S
        for p in render.by_role(team, tid):
            d.text((pad, y + 8 * S), (p.get("role") or "")[:3], font=fr, fill=col)
            _icon(img, p["championId"], 34 * S, y + 3 * S, 24 * S, col)
            d.text((62 * S, y + 4 * S), fit(d, p["champ"], fc, 120 * S), font=fc, fill=INK)
            d.text((62 * S, y + 17 * S), fit(d, p["player"], fn, 200 * S), font=fn, fill=nick_col)
            d.text((W2 - pad, y + 6 * S), p["elo"], font=fe, fill=DIM, anchor="ra")
            y += row
        y += 2 * S
    return img


NOTO = "/usr/share/fonts/noto/"
TTF = "/usr/share/fonts/TTF/"


def style_6_final(team, S=3, fam="noto"):
    reg, bold, mono = ((NOTO + "NotoSans-Regular.ttf", NOTO + "NotoSans-Bold.ttf",
                        NOTO + "NotoSansMono-Regular.ttf") if fam == "noto"
                       else (TTF + "DejaVuSans.ttf", TTF + "DejaVuSans-Bold.ttf",
                             TTF + "DejaVuSansMono.ttf"))
    W2 = W * S
    pad = 6 * S
    label = 14 * S
    row = 35 * S
    icon = 28 * S
    h = pad + label + row * 5 + 4 * S + label + row * 5 + pad
    img = Image.new("RGB", (W2, h), BG)
    d = ImageDraw.Draw(img)
    fr = font(bold, 7 * S)
    fc = font(bold, 16 * S)
    fn = font(reg, 12 * S)
    fe = font(mono, 11 * S)
    ft = font(bold, 8 * S)
    nick_col = (170, 175, 184)
    tx = 60 * S
    y = pad
    for tid in (100, 200):
        col = BLUE if tid == 100 else RED
        d.text((pad, y), "AZUL" if tid == 100 else "VERMELHO", font=ft, fill=col)
        y += label
        for p in render.by_role(team, tid):
            watch = p.get("watched")
            if watch:
                d.rectangle([0, y - 2 * S, W2 - 1, y + row - 4 * S], fill=(23, 27, 12))
                d.rectangle([0, y - 2 * S, 3 * S, y + row - 4 * S], fill=ACC)
            d.text((pad, y + 11 * S), (p.get("role") or "")[:3], font=fr,
                   fill=ACC if watch else col)
            _icon(img, p["championId"], 26 * S, y + 3 * S, icon, ACC if watch else col)
            d.text((tx, y + 1 * S), fit(d, p["champ"], fc, 150 * S), font=fc,
                   fill=ACC if watch else INK)
            d.text((W2 - pad, y + 5 * S), p["elo"], font=fe,
                   fill=(190, 194, 202) if watch else (150, 154, 162), anchor="ra")
            d.text((tx, y + 19 * S), fit(d, p["player"], fn, 150 * S), font=fn,
                   fill=(225, 228, 233) if watch else nick_col)
            y += row
        y += 4 * S
    return img


def build_6(team, S=3):
    buf = io.BytesIO()
    style_6_final(team, S=S, fam="noto").save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_team_card(team, tid, avg=None):
    S = 3
    W2 = 550 * S
    pad = 10 * S
    row = 58 * S
    h = 40 * S + row * 5 + 10 * S
    img = Image.new("RGB", (W2, h), BG)
    d = ImageDraw.Draw(img)
    col = BLUE if tid == 100 else RED
    f_t = font(NOTO + "NotoSans-Bold.ttf", 12 * S)
    f_c = font(NOTO + "NotoSans-Bold.ttf", 18 * S)
    f_n = font(NOTO + "NotoSans-Regular.ttf", 13 * S)
    f_e = font(NOTO + "NotoSansMono-Regular.ttf", 12 * S)
    d.rectangle([0, 0, 4 * S, h], fill=col)
    d.text((pad, 10 * S), "AZUL" if tid == 100 else "VERMELHO", font=f_t, fill=col)
    if avg:
        d.text((W2 - pad, 10 * S), avg, font=f_e, fill=col, anchor="ra")
    y = 40 * S
    for p in render.by_role(team, tid):
        watch = p.get("watched")
        if watch:
            d.rectangle([0, y, W2, y + row - 6 * S], fill=(23, 27, 12))
            d.rectangle([0, y, 4 * S, y + row - 6 * S], fill=ACC)
        _icon(img, p["championId"], pad, y + 6 * S, 40 * S, ACC if watch else col)
        d.text((pad + 48 * S, y + 4 * S), fit(d, p["champ"], f_c, 300 * S), font=f_c,
               fill=ACC if watch else INK)
        d.text((pad + 48 * S, y + 28 * S), fit(d, p["player"], f_n, 330 * S), font=f_n,
               fill=(225, 228, 233) if watch else (170, 175, 184))
        d.text((W2 - pad, y + 10 * S), p["elo"], font=f_e,
               fill=(200, 204, 210) if watch else (155, 160, 168), anchor="ra")
        y += row
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_teams(team):
    elo = {}
    for tid in (100, 200):
        ps = render.by_role(team, tid)
        vals = [p.get("elo", "") for p in ps]
        elo[tid] = "média do time" if any(vals) else ""
    return build_team_card(team, 100), build_team_card(team, 200)
