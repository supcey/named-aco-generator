# aco-tool

Create, read and batch-edit **Adobe `.aco` swatch files with color names**, using plain text.

Most CSS-to-swatch converters only write the color values, so every swatch ends up unnamed
and naming thousands of colors by hand is out of the question. `aco-tool` writes the named
(v2) section of the format, so names from a CSV or CSS file arrive intact in Photoshop and
Illustrator.

- No dependencies, just Python 3.8+ and one file
- Handles thousands of colors in a second
- Unicode names (Turkish, Japanese, emoji, etc.) work
- Round-trip: `.aco` → CSV → edit names in bulk → `.aco`

## Quick start

```bash
git clone https://github.com/YOUR-USERNAME/aco-tool.git
cd aco-tool
python aco_tool.py csv2aco examples/colors.csv swatches.aco
```

In Photoshop, open **Window → Swatches**, click the panel menu (☰) and choose
**Import Swatches…** (older versions: **Load Swatches…**), then select `swatches.aco`.

## Commands

| Command | What it does |
|---|---|
| `python aco_tool.py csv2aco colors.csv out.aco` | Build a named `.aco` from a CSV |
| `python aco_tool.py aco2csv in.aco colors.csv` | Export an existing `.aco` to CSV |
| `python aco_tool.py css2aco style.css out.aco` | Build a named `.aco` from CSS |

### CSV format

```csv
name,hex
Ocean Blue,#1A73E8
Cherry,#D2042D
#FF5733
```

- The header row is optional.
- `#` is optional and 3-digit codes (`#fff`) are accepted.
- Delimiter (`,` `;` or tab) is detected automatically, so CSVs saved by Excel in
  any locale work.
- A row with only a hex code uses the hex code as the name.
- Save as **UTF-8** if your names contain non-ASCII characters.

### CSS input

Names are derived from the CSS itself:

| CSS | Swatch name |
|---|---|
| `--brand-blue: #1a73e8;` | `brand-blue` |
| `.btn-primary { color: #fff; }` | `btn-primary` |
| a bare `#ff5733` | `#FF5733` |

## Bulk-renaming workflow

1. Export: `python aco_tool.py aco2csv old.aco colors.csv`
2. Edit the `name` column in Excel, Google Sheets or with a script.
3. Rebuild: `python aco_tool.py csv2aco colors.csv new.aco`

## Format notes

An `.aco` file holds two blocks: version 1 (colors only) followed by version 2
(colors plus UTF-16 names). `aco-tool` writes both, so legacy and current Adobe apps
can read the file.

- Reads RGB, CMYK and grayscale swatches. HSB and Lab swatches are skipped.
- Output is always RGB.
- Spec reference: Adobe Photoshop File Formats Specification, "Color Swatch file (.aco)".

## Contributing

Issues and pull requests are welcome. Ideas: HSB/Lab support, automatic color naming,
a `--sort` option, tests.

## License

[MIT](LICENSE)
