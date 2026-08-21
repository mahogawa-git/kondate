from __future__ import annotations

import json
import re
from collections import defaultdict
from fractions import Fraction
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
DATA = ROOT / "recipes.json"

DAY_ORDER = ["週末昼", "週末夜", "月", "火", "水", "木", "金"]
CATEGORY_ORDER = ["メイン", "スープ", "副菜"]
CATEGORY_ICON = {"メイン": "🍽️", "スープ": "🥣", "副菜": "🥗"}
DAY_CLASS = {
    "週末昼": "d-sat",
    "週末夜": "d-sun",
    "月": "d-mon",
    "火": "d-tue",
    "水": "d-wed",
    "木": "d-thu",
    "金": "d-fri",
}
TOOL_LABEL = {
    "ホットクック": "🍲",
    "ホットクック予約✕": "🍲予約✕",
    "ホットクック予約○": "🍲予約◯",
    "ホットクック二段": "🍲二段",
    "ヘルシオ": "ヘルシオ",
    "レンジ": "レンジ",
}


def notion_url(url: str | None) -> str:
    if not url:
        return ""
    return re.sub(r"https://app\.notion\.com/(?!p/)([0-9a-fA-F]{32})(?=$|[/?#])", r"https://app.notion.com/p/\1", url)


def split_items(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in re.split(r"\s*(?:／|\r?\n)+\s*", value) if x.strip()]


def parse_material(line: str) -> tuple[str, str]:
    line = line.strip()
    m = re.match(r"^(.*?)[ \t]+((?:\d|\d+\.\d|\d+/\d|\d+\s+\d+/\d).*)$", line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return line, ""


def parse_prep(line: str) -> tuple[str, str]:
    line = line.strip()
    if " " in line:
        ingredient, action = line.split(None, 1)
        return ingredient.strip(), action.strip()
    m = re.match(r"^(.+?)は(.+)$", line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return line, ""


def qty_for(ingredient: str, materials: str | None) -> str:
    targets = [ingredient]
    if ingredient == "鶏肉":
        targets += ["鶏もも肉", "鶏もも"]
    if ingredient == "豚肉":
        targets += ["豚バラ肉", "豚バラ", "豚こま肉"]
    for line in split_items(materials):
        name, qty = parse_material(line)
        if any(name == t or name.startswith(t) or t.startswith(name) for t in targets):
            return qty
    return ""


def tool_html(tool: str | None) -> str:
    if not tool or tool == "なし":
        return ""
    label = TOOL_LABEL.get(tool, tool)
    return f'<span class="tool" data-tool="{escape(tool)}">{escape(label)}</span>'


def row_html(r: dict, body_badges: set[str]) -> str:
    cat = r.get("category") or ""
    page = notion_url(r.get("page_url"))
    icons = [tool_html(r.get("tool"))]
    if page in body_badges or r.get("name") == "ミートソースパスタ":
        icons.append('<span aria-label="本文あり" class="mini-icon meta-badge" data-kind="body"></span>')
    if r.get("source_url"):
        icons.append(
            f'<a aria-label="元レシピ" class="source-btn" href="{escape(r["source_url"], quote=True)}" '
            'rel="noopener noreferrer" target="_blank">🔗</a>'
        )
    icon_html = "".join(x for x in icons if x)
    return (
        '<div class="row">'
        f'<div aria-label="{escape(cat)}" class="label label-icon-only" title="{escape(cat)}">{CATEGORY_ICON.get(cat, "🍽️")}</div>'
        '<div class="dish"><div class="dish-title-row">'
        f'<div class="dishname dish-title"><a href="{escape(page, quote=True)}" rel="noopener" target="_blank">{escape(r.get("name") or "")}</a></div>'
        f'<span class="title-icons">{icon_html}</span>'
        '</div></div></div>'
    )


def render_cards(rows: list[dict], body_badges: set[str]) -> str:
    out = []
    for day in DAY_ORDER:
        todays = [r for r in rows if r.get("day") == day]
        if not todays:
            continue
        todays.sort(key=lambda r: (CATEGORY_ORDER.index(r.get("category")) if r.get("category") in CATEGORY_ORDER else 99, r.get("name") or ""))
        out.append(f'<section class="daycard"><h3>{day}</h3>')
        out.extend(row_html(r, body_badges) for r in todays)
        out.append('</section>')
    return "".join(out)


def render_prep(rows: list[dict], first_week: bool) -> str:
    grouped: dict[str, dict[str, list[tuple[dict, str]]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        for item in split_items(r.get("prep")):
            ingredient, action = parse_prep(item)
            if not ingredient or not action:
                continue
            grouped[ingredient][action].append((r, qty_for(ingredient, r.get("materials"))))

    if not grouped:
        return ""

    title_id = ' id="prep-start"' if first_week else ""
    legend = ''.join(f'<span class="prep-day-chip {DAY_CLASS[d]}">{d}</span>' for d in DAY_ORDER)
    parts = [f'<section class="prep-summary"><h3{title_id}>🔪 7日分の下準備（食材ごと）</h3><div class="prep-weekday-legend">{legend}</div><div class="prep-ing-grid">']
    for ingredient in sorted(grouped):
        parts.append(f'<div class="prep-ing"><h4>{escape(ingredient)}</h4>')
        for action, refs in grouped[ingredient].items():
            parts.append(f'<div class="prep-action"><div class="prep-task">{escape(action)}</div><div class="prep-recipes">')
            refs.sort(key=lambda x: DAY_ORDER.index(x[0]["day"]))
            for r, qty in refs:
                day = r["day"]
                text = r["name"] + (f'（{qty}）' if qty else '')
                parts.append(
                    f'<a class="prep-day-link {DAY_CLASS[day]}" data-day="{day}" href="{escape(notion_url(r["page_url"]), quote=True)}" rel="noopener" target="_blank">{escape(text)}</a>'
                )
            parts.append('</div></div>')
        parts.append('</div>')
    parts.append('</div></section>')
    return ''.join(parts)


def category_for_item(name: str) -> str:
    fish = ("鮭", "サーモン", "サバ", "さば", "鯖", "ブリ", "ぶり", "白身魚", "しらす", "ツナ")
    meat = ("豚", "鶏", "牛", "合いびき", "合挽", "ひき肉", "挽肉", "ハム", "ベーコン", "餃子")
    produce = ("トマト", "ミニトマト", "キャベツ", "白菜", "大根", "小松菜", "ほうれん草", "水菜", "じゃがいも", "さつまいも", "玉ねぎ", "たまねぎ", "人参", "にんじん", "なす", "ナス", "きゅうり", "れんこん", "ブロッコリー", "きのこ", "えのき", "しめじ", "しいたけ", "長ネギ", "ねぎ", "マッシュルーム")
    if any(k in name for k in fish + meat):
        return "肉・魚"
    if any(k in name for k in produce):
        return "野菜・果物"
    return "その他"


def shopping_rank(text: str) -> int:
    priorities = [
        ("鮭", "サーモン", "サバ", "さば", "鯖", "ブリ", "ぶり", "白身魚", "魚", "しらす", "ツナ"),
        ("豚", "鶏", "牛", "合いびき", "合挽", "ひき肉", "挽肉", "ハム", "ベーコン", "肉"),
        ("トマト", "とまと"),
        ("レタス", "キャベツ"),
        ("大根",),
        ("白菜", "小松菜", "ほうれん草", "水菜", "チンゲン菜", "ニラ", "春菊"),
        ("じゃがいも", "さつまいも", "里芋", "長芋", "山芋"),
        ("れんこん", "ごぼう", "かぶ"),
        ("玉ねぎ", "たまねぎ", "長ネギ", "長ねぎ", "ねぎ", "ネギ"),
        ("人参", "にんじん"),
        ("なす", "ナス", "ピーマン", "パプリカ", "もやし"),
        ("きのこ", "えのき", "しめじ", "しいたけ", "椎茸", "エリンギ", "まいたけ", "舞茸", "マッシュルーム"),
        ("枝豆", "いんげん", "豆", "ビーンズ"),
    ]
    for i, keys in enumerate(priorities):
        if any(k in text for k in keys):
            return i
    return 99


def render_shopping(rows: list[dict], week: int, first_week: bool) -> str:
    items: list[str] = []
    for r in rows:
        items.extend(split_items(r.get("materials")))
    # Keep every recipe's exact shopping entry. This avoids unsafe quantity math
    # when units/fractions differ, while still de-duplicating exact repeats.
    seen = set()
    items = [x for x in items if not (x in seen or seen.add(x))]
    groups: dict[str, list[str]] = defaultdict(list)
    for item in items:
        name, _ = parse_material(item)
        groups[category_for_item(name)].append(item)
    for values in groups.values():
        values.sort(key=lambda x: (shopping_rank(x), x))

    title_id = ' id="shopping-start"' if first_week else ""
    parts = [f'<section class="utility"><h3{title_id}>🛒 材料・買い物</h3><button class="shop-reset" data-week="{week}" type="button">チェック解除</button>']
    idx = 0
    for group in ("肉・魚", "野菜・果物", "その他"):
        if not groups.get(group):
            continue
        parts.append(f'<div class="shopgroup"><strong>{group}</strong><div class="shop-checklist">')
        for item in groups[group]:
            idx += 1
            store_key = f'w{week}:{item}'
            parts.append(
                f'<label class="shop-row"><input class="shop-cb" data-store-key="{escape(store_key, quote=True)}" id="w{week}-shop-{idx}" type="checkbox"/><span class="shop-item-text">{escape(item)}</span></label>'
            )
        parts.append('</div></div>')
    parts.append('</section>')
    return ''.join(parts)


def render_week(all_rows: list[dict], week: int, body_badges: set[str]) -> str:
    flag = f'w{week}'
    rows = [r for r in all_rows if r.get(flag) == "__YES__" and r.get("day") and r.get("category")]
    first = week == 1
    active = " active" if first else ""
    return (
        f'<main class="week{active}" data-week="{week}" id="week{week}">\n'
        + render_cards(rows, body_badges)
        + '\n'
        + render_prep(rows, first)
        + '\n'
        + render_shopping(rows, week, first)
        + '\n</main>'
    )


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    rows = json.loads(DATA.read_text(encoding="utf-8"))

    body_badges = set()
    for m in re.finditer(r'<div class="dishname dish-title"><a href="([^"]+)".*?</a></div><span class="title-icons">(.*?)</span>', html, re.S):
        if 'data-kind="body"' in m.group(2):
            body_badges.add(notion_url(m.group(1)))

    weeks_html = "\n".join(render_week(rows, w, body_badges) for w in range(1, 5))
    pattern = re.compile(r'<main class="week(?: active)?" data-week="1" id="week1">.*?</main>\s*<main class="week(?: active)?" data-week="2" id="week2">.*?</main>\s*<main class="week(?: active)?" data-week="3" id="week3">.*?</main>\s*<main class="week(?: active)?" data-week="4" id="week4">.*?</main>', re.S)
    html2, n = pattern.subn(weeks_html, html, count=1)
    if n != 1:
        raise SystemExit(f"Could not replace four week blocks (matched {n})")
    INDEX.write_text(html2, encoding="utf-8")


if __name__ == "__main__":
    main()
