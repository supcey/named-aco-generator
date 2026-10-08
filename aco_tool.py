#!/usr/bin/env python3
"""
aco-tool: create, read and batch-edit Adobe .aco swatch files, with color names.

Usage:
  python aco_tool.py aco2csv  input.aco   colors.csv   # .aco -> CSV (name,hex)
  python aco_tool.py csv2aco  colors.csv  output.aco   # CSV   -> named .aco
  python aco_tool.py css2aco  style.css   output.aco   # CSS   -> named .aco

CSV format (header row optional, delimiter , ; or tab is auto-detected):
  name,hex
  Ocean Blue,#1A73E8
  #FF5733            <- single column: the hex code is used as the name

Names taken from CSS:
  --brand-blue: #1a73e8;       -> name: brand-blue
  .btn-primary { color:#fff }  -> name: btn-primary
  Unnamed colors               -> name: hex code
"""
import csv
import re
import struct
import sys

__version__ = "1.0.0"


# ---------- ACO read / write ----------

def read_aco(path):
    """Return [(name, (r, g, b))]. Names come from the v2 block if present."""
    with open(path, "rb") as f:
        data = f.read()

    def read_block(pos, version):
        _, count = struct.unpack_from(">HH", data, pos)
        pos += 4
        out = []
        for _ in range(count):
            space, a, b, c, d = struct.unpack_from(">HHHHH", data, pos)
            pos += 10
            name = ""
            if version == 2:
                pos += 2  # reserved 0x0000
                (n,) = struct.unpack_from(">H", data, pos)
                pos += 2
                name = data[pos:pos + (n - 1) * 2].decode("utf-16-be")
                pos += n * 2
            out.append((space, a, b, c, d, name))
        return out, pos

    colors, pos = read_block(0, 1)
    if pos < len(data):  # v2 block follows: it carries the names
        colors, pos = read_block(pos, 2)

    result = []
    for space, a, b, c, d, name in colors:
        if space == 0:  # RGB (0-65535)
            rgb = (round(a / 257), round(b / 257), round(c / 257))
        elif space == 8:  # grayscale (0-10000)
            g = round(a / 10000 * 255)
            rgb = (g, g, g)
        elif space == 2:  # CMYK (stored inverted: 65535 = 0% ink)
            cc, m, y, k = [1 - v / 65535 for v in (a, b, c, d)]
            rgb = tuple(round(255 * (1 - x) * (1 - k)) for x in (cc, m, y))
        else:
            continue  # HSB, Lab, etc. are skipped
        result.append((name, rgb))
    return result


def write_aco(path, colors):
    """colors: [(name, (r, g, b))]. Writes a v1 block followed by a named v2 block."""
    n = len(colors)
    out = bytearray()
    out += struct.pack(">HH", 1, n)  # v1: colors only (legacy readers)
    for _, (r, g, b) in colors:
        out += struct.pack(">HHHHH", 0, r * 257, g * 257, b * 257, 0)
    out += struct.pack(">HH", 2, n)  # v2: colors + UTF-16 names
    for name, (r, g, b) in colors:
        out += struct.pack(">HHHHH", 0, r * 257, g * 257, b * 257, 0)
        out += struct.pack(">HH", 0, len(name) + 1)
        out += name.encode("utf-16-be") + b"\x00\x00"
    with open(path, "wb") as f:
        f.write(out)


# ---------- helpers ----------

def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) == 8:  # drop alpha
        h = h[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % rgb


# ---------- commands ----------

def aco2csv(src, dst):
    colors = read_aco(src)
    with open(dst, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["name", "hex"])
        for name, rgb in colors:
            w.writerow([name, rgb_to_hex(rgb)])
    print(f"{len(colors)} colors written -> {dst}")


def csv2aco(src, dst):
    colors = []
    with open(src, newline="", encoding="utf-8-sig") as f:
        lines = f.read().splitlines()
    first = lines[0] if lines else ""
    delim = max([",", ";", "\t"], key=first.count)
    for row in csv.reader(lines, delimiter=delim):
        row = [c.strip() for c in row if c.strip()]
        if not row:
            continue
        hexval = row[-1]
        if not re.fullmatch(r"#?[0-9a-fA-F]{3,8}", hexval):
            continue  # header or junk line
        name = row[0] if len(row) > 1 else rgb_to_hex(hex_to_rgb(hexval))
        colors.append((name, hex_to_rgb(hexval)))
    write_aco(dst, colors)
    print(f"{len(colors)} colors -> {dst}")


def css2aco(src, dst):
    with open(src, encoding="utf-8") as f:
        css = f.read()
    colors, seen = [], set()

    # 1) CSS custom properties
    for m in re.finditer(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b", css):
        colors.append((m.group(1), hex_to_rgb(m.group(2))))
        seen.add(m.group(2).lower())

    # 2) Rule blocks: .name { ... #hex ... }
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector, body = m.group(1).strip(), m.group(2)
        hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", body)
        if not hexes or body.strip().startswith("--"):
            continue
        base = re.sub(r"^[.#]", "", selector.split(",")[0].strip())
        for i, h in enumerate(hexes):
            if h.lower() in seen:
                continue
            colors.append((base if len(hexes) == 1 else f"{base}-{i + 1}",
                           hex_to_rgb(h)))
            seen.add(h.lower())

    # 3) Any remaining unnamed hex codes
    for h in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", css):
        if h.lower() not in seen:
            colors.append((rgb_to_hex(hex_to_rgb(h)), hex_to_rgb(h)))
            seen.add(h.lower())

    write_aco(dst, colors)
    print(f"{len(colors)} colors -> {dst}")


def main(argv):
    cmds = {"aco2csv": aco2csv, "csv2aco": csv2aco, "css2aco": css2aco}
    if len(argv) != 4 or argv[1] not in cmds:
        print(__doc__)
        return 1
    try:
        cmds[argv[1]](argv[2], argv[3])
    except FileNotFoundError as e:
        print(f"Error: file not found: {e.filename}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
