#!/usr/bin/env python3
"""Zeichnet docs/bilder/dachfenster-geometrie.svg.

Die Skizze erklärt die Größen, die man für die Blueprints braucht:
Ausrichtung A_f und Sonnenazimut A_s (Draufsicht), Neigung β, Sonnenhöhe h und
Einfallswinkel θ (Schnitt), die Umrechnung PV-Leistung → Einstrahlung → Helligkeit
und die Startwerte der Beschattung aus docs/ENTWURF.md (Abschnitt 4.3).

Aufruf (nur Standardbibliothek, keine weitere Abhängigkeit):
    uv run python scripts/skizze_dachfenster.py
    uv run python scripts/skizze_dachfenster.py --ziel /tmp/test.svg

Alle Zahlen sind Beispielwerte, keine Werte aus einem echten Haus. Ändern sich
Formeln oder Startwerte in docs/ENTWURF.md, hier nachziehen, STAND anpassen und
die SVG-Datei neu erzeugen.
"""

from __future__ import annotations

import argparse
from math import atan2, cos, degrees, radians, sin
from pathlib import Path
from xml.sax.saxutils import escape

STAND = "27.11.2026"
WURZEL = Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "docs" / "bilder" / "dachfenster-geometrie.svg"

SCHRIFT = "Arial, 'Helvetica Neue', Helvetica, 'Liberation Sans', sans-serif"
MONO = "Consolas, 'DejaVu Sans Mono', 'Liberation Mono', monospace"

# Zeichenbreiten in 1/1000 em, gemessen an Liberation Sans (gleiche Maße wie Arial).
# Nur für die Breite der Kästchen in der Fußleiste; fehlende Zeichen zählen 0,56 em.
_BREITE_NORMAL = {
    " ": 278, "%": 889, "(": 333, ")": 333, "-": 333, ".": 278, "/": 278, ":": 278,
    "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556, "6": 556, "7": 556,
    "8": 556, "9": 556, "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611,
    "G": 778, "H": 722, "I": 278, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778,
    "P": 667, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944, "Z": 611,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556, "h": 556,
    "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556, "o": 556, "p": 556,
    "r": 333, "s": 500, "t": 278, "u": 556, "v": 500, "w": 722, "x": 500, "z": 500,
    "ä": 556, "ö": 556, "ü": 556, "ß": 611, "°": 400, "·": 333,
}
_BREITE_FETT = {
    " ": 278, "%": 889, "/": 278, ".": 278, "0": 556, "1": 556, "2": 556, "3": 556,
    "4": 556, "5": 556, "6": 556, "7": 556, "8": 556, "9": 556, "C": 722, "E": 667,
    "a": 556, "b": 611, "c": 556, "d": 611, "e": 556, "f": 333, "g": 611, "h": 611,
    "i": 278, "l": 278, "m": 889, "n": 611, "o": 611, "p": 611, "r": 389, "s": 556,
    "t": 333, "u": 611, "x": 556, "ä": 556, "ö": 611, "ü": 611, "°": 400,
}


def textbreite(text: str, groesse: float, fett: bool = False) -> float:
    tabelle = _BREITE_FETT if fett else _BREITE_NORMAL
    return sum(tabelle.get(z, 560) for z in text) * groesse / 1000


teile: list[str] = []


def f(z: float) -> str:
    return f"{z:.1f}".rstrip("0").rstrip(".")


def text(x, y, s, groesse=12.0, fett=False, farbe="#37474F", anker="start", halo=False, familie=None):
    attr = [f'x="{f(x)}"', f'y="{f(y)}"', f'font-family="{familie or SCHRIFT}"',
            f'font-size="{f(groesse)}"']
    if fett:
        attr.append('font-weight="bold"')
    attr += [f'fill="{farbe}"', f'text-anchor="{anker}"', 'dominant-baseline="central"']
    if halo:
        attr.append('stroke="#FFFFFF" stroke-width="4" stroke-linejoin="round" paint-order="stroke"')
    teile.append(f"<text {' '.join(attr)}>{escape(s)}</text>")


def linie(punkte, farbe="#37474F", breite=1.4, strich=None, pfeil=None, kappe="butt"):
    d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in punkte)
    attr = (f'd="{d}" fill="none" stroke="{farbe}" stroke-width="{f(breite)}" '
            f'stroke-linecap="{kappe}" stroke-linejoin="round"')
    if strich:
        attr += f' stroke-dasharray="{strich}"'
    if pfeil:
        attr += f' marker-end="url(#{pfeil})"'
    teile.append(f"<path {attr}/>")


def rechteck(x, y, b, h, fuellung, rand="none", breite=1.0, rund=0.0):
    teile.append(f'<rect x="{f(x)}" y="{f(y)}" width="{f(b)}" height="{f(h)}" rx="{f(rund)}" '
                 f'fill="{fuellung}" stroke="{rand}" stroke-width="{f(breite)}"/>')


def bogen(mx, my, r, w1, w2, farbe="#5D4037", breite=1.5):
    """Kreisbogen um (mx, my) von w1 nach w2 in Grad (Bildschirm: 0 = rechts, 90 = unten)."""
    x1, y1 = mx + r * cos(radians(w1)), my + r * sin(radians(w1))
    x2, y2 = mx + r * cos(radians(w2)), my + r * sin(radians(w2))
    richtung = 1 if w2 > w1 else 0
    teile.append(f'<path d="M{f(x1)},{f(y1)} A{f(r)},{f(r)} 0 0 {richtung} {f(x2)},{f(y2)}" '
                 f'fill="none" stroke="{farbe}" stroke-width="{f(breite)}"/>')


def sonne(cx, cy):
    for i in range(8):
        w = radians(i * 45)
        linie([(cx + 17 * cos(w), cy + 17 * sin(w)), (cx + 24 * cos(w), cy + 24 * sin(w))],
              "#F9A825", 2.5, kappe="round")
    teile.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="13" fill="#FBC02D" stroke="#F9A825" stroke-width="1.5"/>')


def kompass(cx, cy):
    teile.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="38" fill="#FFFFFF" stroke="#8D6E63" stroke-width="1.5"/>')
    for i in range(8):
        w = radians(i * 45 - 90)
        linie([(cx + 29 * cos(w), cy + 29 * sin(w)), (cx + 38 * cos(w), cy + 38 * sin(w))], "#8D6E63", 1.2)
    teile.append(f'<path d="M{f(cx)},{f(cy - 28)} L{f(cx + 7)},{f(cy)} L{f(cx)},{f(cy + 6)} '
                 f'L{f(cx - 7)},{f(cy)} z" fill="#B71C1C"/>')
    teile.append(f'<path d="M{f(cx)},{f(cy + 28)} L{f(cx + 7)},{f(cy)} L{f(cx)},{f(cy - 6)} '
                 f'L{f(cx - 7)},{f(cy)} z" fill="#90A4AE"/>')
    text(cx, cy - 50, "N · 0°", fett=True, farbe="#3E2723", anker="middle")
    text(cx, cy + 51, "S · 180°", fett=True, farbe="#3E2723", anker="middle")
    text(cx + 46, cy, "O · 90°", fett=True, farbe="#3E2723")
    text(cx - 46, cy, "W · 270°", fett=True, farbe="#3E2723", anker="end")


def kasten(x, y, b, h, fuellung, rand, titel, untertitel, titelfarbe):
    rechteck(x, y, b, h, fuellung, rand, 2, 10)
    teile.append(f'<path d="M{x},{y + 10} a10,10 0 0 1 10,-10 h{b - 20} a10,10 0 0 1 10,10 '
                 f'v38 h-{b} z" fill="{rand}"/>')
    text(x + 14, y + 17, titel, 17, True, titelfarbe)
    text(x + 14, y + 36, untertitel, 12, False, titelfarbe)


def zeichnen() -> str:
    teile.clear()
    teile.append('<rect x="0" y="0" width="1680" height="860" fill="#ffffff"/>')
    text(30, 38, "Dachfenster: Ausrichtung, Neigung und Sonneneinfall", 26, True, "#1f2933")
    text(30, 66, f"Stand {STAND} · schematisch, Beispielwerte · Werte je Fläche in die Instanz des "
         "Blueprints eintragen · Kompass: 0 = Nord, 90 = Ost, 180 = Süd, 270 = West", 13, False, "#455A64")
    draufsicht()
    schnitt()
    helligkeit()
    startwerte()
    return zusammensetzen()


def draufsicht():
    """Kasten 1: Ausrichtung A_f, Sonnenazimut A_s und ihre Differenz Δ."""
    kasten(30, 110, 520, 600, "#FFFDE7", "#F9A825", "Ausrichtung der Dachfläche",
           "Draufsicht · Beispiel: Dachfläche nach Süden", "#3E2723")
    rechteck(80, 230, 250, 120, "#ECEFF1", "#90A4AE", 1.2)
    rechteck(80, 350, 250, 120, "#FFF9C4", "#F9A825", 1.5)
    linie([(80, 350), (330, 350)], "#78909C", 3)
    text(205, 290, "Nordseite", 12, True, "#90A4AE", "middle")
    text(338, 350, "First", 11.5, False, "#546E7A")
    text(86, 482, "Traufe", 11.5, False, "#546E7A")
    text(200, 369, "Dachfenster", 11.5, True, "#37474F", "middle", halo=True)
    rechteck(180, 383, 40, 40, "#90CAF9", "#42A5F5", 1.5, 2)
    for spalte in range(2):
        for zeile in range(2):
            x, y = 240 + spalte * 44, 378 + zeile * 32
            rechteck(x, y, 40, 28, "#455A64", "#263238", 1, 1)
            linie([(x + 20, y + 2), (x + 20, y + 26)], "#78909C", 0.8)
    text(282, 452, "PV, gleiche Fläche", 11.5, True, "#37474F", "middle", halo=True)
    # Ausrichtung: rechtwinklig zur Traufe nach draußen
    linie([(200, 403), (200, 585)], "#3E2723", 3, pfeil="pfeil-braun")
    text(212, 520, "A_f  Ausrichtung der Fläche", 12.5, True, "#3E2723", halo=True)
    text(212, 538, "= Blick nach draußen", 12.5, False, "#3E2723", halo=True)
    text(212, 556, "hier: Süden = 180°", 12.5, False, "#3E2723", halo=True)
    # Sonne im Südsüdwesten (Bildschirmwinkel 120° = 30° von Süd Richtung West)
    ws = radians(120)
    sx, sy = 200 + 190 * cos(ws), 403 + 190 * sin(ws)
    linie([(sx - 17 * cos(ws), sy - 17 * sin(ws)), (200, 403)], "#F9A825", 2, "5 4")
    sonne(sx, sy)
    text(44, sy + 42, "A_s  Sonnenazimut = 210°", 12, True, "#5D4037", halo=True)
    bogen(200, 403, 92, 90, 120)
    text(200 + 116 * cos(radians(105)), 403 + 116 * sin(radians(105)), "Δ = 30°", 11.5, True,
         "#5D4037", "middle", halo=True)
    kompass(448, 238)
    # Formel
    rechteck(350, 376, 190, 88, "#FFFFFF", "#F9A825", 1.2, 8)
    text(362, 394, "Δ = A_s − A_f", 12.5, True, "#3E2723", familie=MONO)
    text(362, 414, "Δ = 0°: Sonne genau von vorn", 11.5, False, "#5D4037")
    text(362, 432, "Δ = ±90°: Sonne von der Seite", 11.5, False, "#5D4037")
    text(362, 450, "A_s, A_f ab Nord im Uhrzeigersinn", 11, False, "#5D4037")
    text(44, 652, "A_f: rechtwinklig zur Traufe, Blick nach draußen.", 12)
    text(44, 670, "Am einfachsten aus SFML übernehmen (Panelgruppe der Fensterseite).", 12)
    text(44, 688, "A_s liefert Home Assistant laufend über sun.sun (Attribut azimuth).", 12)


def schnitt():
    """Kasten 2: Neigung β, Sonnenhöhe h, Flächennormale und Einfallswinkel θ."""
    kasten(570, 110, 580, 600, "#ECEFF1", "#546E7A", "Schnitt durch die Dachfläche",
           "Neigung β, Sonnenhöhe h und Einfallswinkel θ", "#ffffff")
    beta, hoehe = 40.0, 20.0  # Beispiel: Sonne von vorn (Δ = 0) → θ = 90° − (h + β) = 30°
    ex, ey = 680.0, 600.0
    ux, uy = cos(radians(beta)), -sin(radians(beta))
    nx, ny = -sin(radians(beta)), -cos(radians(beta))  # Flächennormale, nach draußen
    sxr, syr = -cos(radians(hoehe)), -sin(radians(hoehe))  # Richtung zur Sonne

    def am_dach(t, laenge=380.0):
        return ex + t * laenge * ux, ey + t * laenge * uy

    rx, ry = am_dach(1.0)
    cx, cy = am_dach(0.51)
    linie([(ex, ey), (ex, 640)], "#546E7A", 3)
    linie([(ex, 640), (1135, 640)], "#546E7A", 3)
    text(1132, 624, "Raum", 12, True, "#90A4AE", "end")
    text(590, 560, "draußen", 12, True, "#90A4AE")
    linie([(ex - 28 * ux, ey - 28 * uy), (rx, ry)], "#B0BEC5", 16)
    linie([(ex - 28 * ux, ey - 28 * uy), (rx, ry)], "#78909C", 1)
    linie([am_dach(0.40), am_dach(0.62)], "#90CAF9", 9)
    linie([am_dach(0.40), am_dach(0.62)], "#42A5F5", 1)
    r1, r2 = am_dach(0.55), am_dach(0.62)
    linie([(r1[0] + 12 * nx, r1[1] + 12 * ny), (r2[0] + 12 * nx, r2[1] + 12 * ny)], "#FB8C00", 7)
    linie([(904, 377), (r2[0] + 14 * nx + 4, r2[1] + 14 * ny + 2)], "#E65100", 1)
    text(907, 377, "Solar-Rollladen (außen)", 11.5, False, "#E65100", halo=True)
    text(rx, ry - 16, "First", 11.5, False, "#546E7A", "middle")
    text(cx - 5, cy + 42, "Dachfenster", 11.5, True, "#37474F", "middle", halo=True)
    # Neigung β gegen die Waagerechte
    linie([(ex, ey), (ex + 110, ey)], "#546E7A", 1.2, "4 4")
    bogen(ex, ey, 66, 0, -beta)
    text(ex + 80, ey - 26, "β  Neigung = Dachneigung", 12, True, "#5D4037", halo=True)
    # Flächennormale
    nx_e, ny_e = cx + 165 * nx, cy + 165 * ny
    linie([(cx, cy), (nx_e, ny_e)], "#37474F", 1.6, pfeil="pfeil-grau")
    text(nx_e, ny_e - 32, "Flächennormale", 12, True, "#37474F", "middle", halo=True)
    text(nx_e, ny_e - 16, "senkrecht zur Scheibe", 11.5, False, "#546E7A", "middle", halo=True)
    # Sonnenstrahl, Sonnenhöhe h
    sonne_x, sonne_y = cx + 205 * sxr, cy + 205 * syr
    linie([(sonne_x - 18 * sxr, sonne_y - 18 * syr), (cx - 4 * sxr, cy - 4 * syr)], "#F9A825", 2.2,
          pfeil="pfeil-gelb")
    linie([(cx, cy), (cx - 260 * sxr, cy - 260 * syr)], "#F9A825", 1.5, "5 4")
    sonne(sonne_x, sonne_y)
    text(668, 396, "Sonnenstrahl", 11.5, False, "#E65100", halo=True)
    linie([(cx, cy), (cx - 140, cy)], "#546E7A", 1.2, "4 4")
    w_sonne = degrees(atan2(syr, sxr)) % 360
    bogen(cx, cy, 115, 180, w_sonne)
    text(cx - 146, cy - 12, "h  Sonnenhöhe", 12, True, "#5D4037", "end", halo=True)
    # Einfallswinkel θ zwischen Flächennormale und Richtung zur Sonne
    w_normale = degrees(atan2(ny, nx)) % 360
    bogen(cx, cy, 62, w_normale, w_sonne, "#B71C1C", 2)
    wm = radians((w_normale + w_sonne) / 2)
    text(cx + 84 * cos(wm), cy + 84 * sin(wm), "θ", 15, True, "#B71C1C", "middle", halo=True)
    # Formel
    rechteck(832, 172, 304, 122, "#FFFFFF", "#90A4AE", 1.2, 8)
    text(846, 192, "cos θ = sin h · cos β", 12, True, "#263238", familie=MONO)
    text(846 + 43, 212, "+ cos h · sin β · cos Δ", 12, True, "#263238", familie=MONO)
    text(846, 236, "θ Einfallswinkel: Sonnenstrahl ↔ Flächennormale", 11.5, False, "#37474F")
    text(846, 258, "Sonne trifft die Scheibe:", 12, False, "#37474F")
    text(846, 276, "h > 0 und cos θ > 0", 12.5, True, "#B71C1C")
    text(584, 664, "θ = 0°: senkrecht auf die Scheibe · 90°: streifend · über 90°: Sonne hinter der Fläche",
         11.5)
    text(584, 682, "Beispiel im Bild: β = 40°, Sonne von vorn (Δ = 0°) mit h = 20° → θ = 30°", 11.5)
    text(584, 700, "β z. B. aus SFML · h liefert Home Assistant über sun.sun (Attribut elevation)", 11.5)


def helligkeit():
    """Kasten 3: PV-Leistung → Einstrahlung G → Helligkeit E."""
    kasten(1170, 110, 480, 600, "#FFF4E6", "#E65100", "Helligkeit aus der PV",
           "Die PV liegt in derselben Ebene und misst, was auf die Scheibe fällt", "#ffffff")
    for y, titel, wert, betont in [
        (185, "PV-Leistung (DC) der Fensterseite", "P = 4 kW (Beispiel bei 10 kWp)", False),
        (300, "Einstrahlung auf die Fläche", "G = P / (kWp · PR) · 1000 = 500 W/m²", False),
        (415, "Helligkeit auf der Fläche", "E ≈ G · 110 = 55 000 lx", True),
    ]:
        rechteck(1200, y, 420, 60, "#FFFFFF", "#E65100", 1.4, 6)
        text(1214, y + 19, titel, 13, True, "#263238")
        text(1214, y + 41, wert, 13.5, betont, "#BF360C" if betont else "#37474F")
    for y, zeile1, zeile2 in [
        (247, "PR = 0,8 (Performance Ratio)", "Verluste durch Wechselrichter, Wärme, Leitungen"),
        (362, "110 lx pro W/m²", "Lichtausbeute des Sonnenlichts (grob 100–120)"),
    ]:
        linie([(1240, y + 2), (1240, y + 50)], "#E65100", 1.8, pfeil="pfeil-orange")
        text(1256, y + 17, zeile1, 12.5, True, "#BF360C")
        text(1256, y + 35, zeile2, 11.5, False, "#546E7A")
    text(1200, 500, "Einordnung", 12.5, True, "#263238")
    rechteck(1200, 520, 420, 20, "url(#luxskala)", "#90A4AE", 1, 3)

    def lux_x(lux: float) -> float:
        return 1200 + lux / 100000 * 420

    for lux, beschriftung in [(0, "0"), (20000, "20 000"), (40000, "40 000"), (100000, "100 000 lx")]:
        x = lux_x(lux)
        linie([(x, 540), (x, 547)], "#546E7A", 1.2)
        anker = "start" if lux == 0 else ("end" if lux == 100000 else "middle")
        text(x, 557, beschriftung, 11, False, "#455A64", anker)
    linie([(lux_x(40000), 514), (lux_x(40000), 546)], "#BF360C", 2)
    text(lux_x(10000), 575, "bedeckt", 11.5, False, "#546E7A", "middle")
    text(lux_x(40000), 575, "Schwelle", 11.5, True, "#BF360C", "middle")
    text(lux_x(72000), 575, "direkte Sonne", 11.5, False, "#546E7A", "middle")
    bx = lux_x(55000)
    teile.append(f'<path d="M{f(bx - 6)},511 L{f(bx + 6)},511 L{f(bx)},519 z" fill="#263238"/>')
    text(bx, 502, "Beispiel", 11, True, "#263238", "middle")
    text(1184, 616, "Nur Module derselben Ebene wie das Fenster,", 12)
    text(1184, 634, "DC-Leistung vor dem Wechselrichter, nicht die Einspeisung.", 12)
    text(1184, 652, "Zu niedrig bei Nulleinspeisung mit vollem Akku,", 12)
    text(1184, 670, "bei Schnee oder Teilverschattung der Module.", 12)
    text(1184, 688, "Die Umrechnung ist eine Schätzung (etwa ±15 %).", 12)


def startwerte():
    """Fußleiste: Startwerte der Beschattung aus docs/ENTWURF.md 4.3."""
    rechteck(20, 730, 1640, 110, "#FAFAFA", "#CFD8DC", 1, 10)
    text(36, 752, "Startwerte der Beschattung (ENTWURF 4.3 · Blueprint und Rechenweg der Position "
         "folgen in Etappe 7)", 14, True, "#263238")
    x = 36.0
    for beschriftung, wert in [
        ("max. Einfallswinkel", "60°"),
        ("Helligkeits-Schwelle", "40 000 lx"),
        ("Temperatur-Freigabe", "23 °C"),
        ("Position", "folgt dem Sonnenstand"),
        ("Position offen", "100 %"),
        ("Verzögerung ein / aus", "10 / 30 min"),
    ]:
        b_text = textbreite(beschriftung, 11.5)
        breite = 10 + b_text + 9 + textbreite(wert, 13, fett=True) + 10
        rechteck(x, 770, breite, 30, "#FFE0B2", "#FB8C00", 1.2, 6)
        text(x + 10, 785, beschriftung, 11.5, False, "#37474F")
        text(x + 10 + b_text + 9, 785, wert, 13, True, "#102027")
        x += breite + 10
    text(36, 822, "Raumtemperatur ist nur Freigabe, kein Auslöser · einen von Hand weiter geschlossenen "
         "Rollladen nie hochfahren · wenige Fahrten pro Tag (Solar-Akku) · Position: 100 = offen, 0 = zu",
         12.5)


def zusammensetzen() -> str:
    pfeile = "".join(
        f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" '
        f'markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0,0.8 L10,5 L0,9.2 z" '
        f'fill="{farbe}"/></marker>'
        for name, farbe in [("pfeil-braun", "#3E2723"), ("pfeil-grau", "#37474F"),
                            ("pfeil-orange", "#E65100"), ("pfeil-gelb", "#F9A825")]
    )
    verlauf = ('<linearGradient id="luxskala" x1="0" y1="0" x2="1" y2="0">'
               '<stop offset="0" stop-color="#CFD8DC"/><stop offset="0.2" stop-color="#FFF9C4"/>'
               '<stop offset="0.4" stop-color="#FFE082"/><stop offset="1" stop-color="#F9A825"/>'
               '</linearGradient>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1680 860" width="1680" height="860" '
            f'font-family="{SCHRIFT}">\n<defs>{pfeile}{verlauf}</defs>\n' + "\n".join(teile) + "\n</svg>\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ziel", type=Path, default=ZIEL, help=f"Ausgabedatei (Standard: {ZIEL})")
    args = parser.parse_args(argv)
    args.ziel.parent.mkdir(parents=True, exist_ok=True)
    args.ziel.write_text(zeichnen(), encoding="utf-8")
    print("geschrieben:", args.ziel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
