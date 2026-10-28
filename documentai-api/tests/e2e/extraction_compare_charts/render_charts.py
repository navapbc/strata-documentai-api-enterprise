import pathlib

import vl_convert as vlc  # type: ignore[import-not-found]

for f in pathlib.Path(".").glob("*_chart.vl.json"):
    png = vlc.vegalite_to_png(f.read_text(), scale=2)
    out = f.with_suffix("").with_suffix(".png")
    out.write_bytes(png)
    print(f"rendered {f.name} -> {out.name}")
