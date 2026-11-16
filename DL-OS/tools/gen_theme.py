#!/usr/bin/env python3
"""Gera, a partir de themes/*.json: tema GTK3, cores do kitty e papel de parede SVG."""
import argparse, json, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent

GTK = """@import url("resource:///org/gtk/libgtk/theme/Adwaita{dark}.css");
@define-color theme_bg_color {bg};
@define-color theme_base_color {surface};
@define-color theme_fg_color {fg};
@define-color theme_text_color {fg};
@define-color theme_selected_bg_color {accent};
@define-color theme_selected_fg_color {bg};
@define-color accent_color {accent};
@define-color borders alpha({fg}, 0.12);
window, .background {{ background-color: {bg}; color: {fg}; }}
headerbar, .titlebar {{ background: {surface}; border-radius: 12px 12px 0 0; box-shadow: none; }}
button {{ border-radius: 10px; padding: 5px 12px; background: {surface}; border: 1px solid alpha({fg},.12); }}
button:hover {{ border-color: {accent}; }}
button.suggested-action, button:checked {{ background: {accent}; color: {bg}; }}
entry, textview, treeview {{ background: {surface}; border-radius: 10px; }}
selection, *:selected {{ background: {accent}; color: {bg}; }}
scrollbar slider {{ border-radius: 99px; min-width: 6px; background: alpha({fg},.3); }}
menu, .popup {{ border-radius: 12px; background: {surface}; }}
"""
KITTY = """background {bg}
foreground {fg}
cursor {accent}
selection_background {accent}
selection_foreground {bg}
color2 {ok}
color4 {accent}
color5 {accent2}
background_opacity 0.94
window_padding_width 10
font_family JetBrains Mono
font_size 11.5
"""
WALL = """<svg xmlns="http://www.w3.org/2000/svg" width="3840" height="2160" viewBox="0 0 3840 2160">
<defs><radialGradient id="a" cx="25%" cy="20%" r="60%"><stop offset="0" stop-color="{accent}" stop-opacity=".55"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
<radialGradient id="b" cx="80%" cy="85%" r="55%"><stop offset="0" stop-color="{accent2}" stop-opacity=".5"/><stop offset="1" stop-color="{accent2}" stop-opacity="0"/></radialGradient></defs>
<rect width="3840" height="2160" fill="{bg}"/><rect width="3840" height="2160" fill="url(#a)"/><rect width="3840" height="2160" fill="url(#b)"/></svg>
"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True)
    out = pathlib.Path(ap.parse_args().out)
    themes = [json.loads(p.read_text()) for p in sorted((ROOT / "themes").glob("*.json"))]
    for t in themes:
        d = {**t, "dark": "-dark" if t["mode"] == "dark" else ""}
        g = out / "themes" / f"DLOS-{t['id']}"
        (g / "gtk-3.0").mkdir(parents=True, exist_ok=True)
        (g / "index.theme").write_text(f"[Desktop Entry]\nType=X-GNOME-Metatheme\nName=DL OS {t['name']}\n\n[X-GNOME-Metatheme]\nGtkTheme=DLOS-{t['id']}\n")
        (g / "gtk-3.0" / "gtk.css").write_text(GTK.format(**d))
        (g / "kitty.conf").write_text(KITTY.format(**d))
        if t.get("wallpaper"):
            shutil.copy(ROOT / t["wallpaper"], g / "wallpaper.png")
            (g / "wallpaper.svg").write_text(WALL.format(**d))  # fallback
        else:
            (g / "wallpaper.svg").write_text(WALL.format(**d))
    (out / "themes.json").write_text(json.dumps(themes, indent=1))
    print(f"{len(themes)} temas gerados em {out}")

if __name__ == "__main__":
    main()
