from __future__ import annotations

import json
import re
from collections import defaultdict
from fractions import Fraction
from html import escape
from pathlib import Path

P = Path('index.html')
DATA = Path('recipes.json')

PROTEIN_KEYS = (
    '鮭','サーモン','サバ','さば','鯖','ブリ','ぶり','白身魚','魚','しらす','ツナ',
    '豚','鶏','牛','合いびき','合挽','ひき肉','挽肉','ハム','ベーコン','餃子',
    '卵','豆腐','納豆','油揚げ',
)
PRODUCE_KEYS = (
    'トマト','ミニトマト','キャベツ','白菜','大根','小松菜','ほうれん草','水菜',
    'じゃがいも','さつまいも','玉ねぎ','たまねぎ','人参','にんじん','なす','ナス',
    'きゅうり','れんこん','ブロッコリー','きのこ','えのき','しめじ','しいたけ',
    '長ネギ','長ねぎ','ねぎ','ネギ','マッシュルーム','わかめ','ひじき','昆布',
)

SHOPPING_PRIORITY = [
    ('魚', ('鮭','サーモン','サバ','さば','鯖','ブリ','ぶり','白身魚','魚','しらす','ツナ')),
    ('肉', ('豚','鶏','牛','合いびき','合挽','ひき肉','挽肉','ハム','ベーコン','餃子')),
    ('卵・大豆', ('卵','豆腐','納豆','油揚げ')),
    ('とまと', ('トマト','とまと')),
    ('レタス・キャベツ', ('レタス','キャベツ')),
    ('大根', ('大根',)),
    ('葉物', ('白菜','小松菜','ほうれん草','水菜','チンゲン菜','青梗菜','ニラ','春菊')),
    ('いも', ('じゃがいも','さつまいも','里芋','長芋','山芋')),
    ('根菜', ('れんこん','ごぼう','かぶ')),
    ('たまねぎ', ('玉ねぎ','たまねぎ','長ネギ','長ねぎ','ねぎ','ネギ')),
    ('にんじん', ('人参','にんじん')),
    ('なす・ぴーまん・もやし', ('なす','ナス','ピーマン','パプリカ','もやし')),
    ('きのこ', ('きのこ','えのき','しめじ','しいたけ','椎茸','エリンギ','まいたけ','舞茸','マッシュルーム')),
    ('海藻', ('わかめ','ひじき','昆布')),
    ('豆', ('枝豆','いんげん','豆','ビーンズ')),
]


def split_items(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in re.split(r'\s*(?:／|\r?\n)+\s*', value) if x.strip()]


def split_name_qty(text: str) -> tuple[str, str]:
    text = text.strip()
    m = re.match(r'^(.*?)[ \t]+((?:\d+\s+\d+/\d|\d+/\d|\d+(?:\.\d+)?).*)$', text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return text, ''


def parse_number(value: str) -> Fraction | None:
    value = value.strip()
    try:
        if ' ' in value:
            whole, frac = value.split(None, 1)
            return Fraction(int(whole), 1) + Fraction(frac)
        if '/' in value:
            return Fraction(value)
        if '.' in value:
            return Fraction(value)
        return Fraction(int(value), 1)
    except (ValueError, ZeroDivisionError):
        return None


def parse_qty(qty: str):
    # Match fractions before plain integers so "1/2本" is one numeric value.
    m = re.match(r'^(\d+\s+\d+/\d|\d+/\d|\d+(?:\.\d+)?)([^（(\s]*)(.*)$', qty.strip())
    if not m:
        return None
    num = parse_number(m.group(1))
    if num is None:
        return None
    return num, m.group(2), m.group(3)


def fmt_number(v: Fraction) -> str:
    if v.denominator == 1:
        return str(v.numerator)
    whole = v.numerator // v.denominator
    rem = v - whole
    if whole:
        return f'{whole} {rem.numerator}/{rem.denominator}'
    return f'{v.numerator}/{v.denominator}'


def classify(name: str) -> str:
    if any(k in name for k in PROTEIN_KEYS):
        return '肉・魚・たんぱく'
    if any(k in name for k in PRODUCE_KEYS):
        return '野菜・海藻など'
    return '主食・その他'


def rank(text: str) -> int:
    for i, (_, keys) in enumerate(SHOPPING_PRIORITY):
        if any(k in text for k in keys):
            return i
    return 99


def aggregate(items: list[str]) -> list[str]:
    numeric = defaultdict(lambda: {'total': Fraction(0), 'count': 0, 'suffix': ''})
    passthrough: list[str] = []
    order: list[tuple[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()

    for raw in items:
        name, qty = split_name_qty(raw)
        parsed = parse_qty(qty)
        if not qty or parsed is None:
            passthrough.append(raw)
            continue
        num, unit, suffix = parsed
        # Different units are kept separate (e.g. 大根 5cm and 大根 1/3本).
        key = (name, unit)
        if key not in seen_keys:
            seen_keys.add(key)
            order.append(key)
        entry = numeric[key]
        entry['total'] += num
        entry['count'] += 1
        if entry['count'] == 1:
            entry['suffix'] = suffix
        else:
            entry['suffix'] = ''

    result: list[str] = []
    for key in order:
        name, unit = key
        e = numeric[key]
        suffix = e['suffix'] if e['count'] == 1 else ''
        result.append(f'{name} {fmt_number(e["total"])}{unit}{suffix}')

    for item in passthrough:
        if item not in result:
            result.append(item)
    return result


def items_for_week(recipes: list[dict], week: int) -> list[str]:
    flag = f'w{week}'
    items: list[str] = []
    for recipe in recipes:
        if recipe.get(flag) != '__YES__':
            continue
        items.extend(split_items(recipe.get('materials')))
    return items


def build_utility(section: str, recipes: list[dict]) -> str:
    wm = re.search(r'data-week="(\d+)"', section)
    if not wm:
        return section
    week = int(wm.group(1))
    first = week == 1
    items = aggregate(items_for_week(recipes, week))

    groups = defaultdict(list)
    for item in items:
        name, _ = split_name_qty(item)
        groups[classify(name)].append(item)
    for vals in groups.values():
        vals.sort(key=lambda x: (rank(x), x))

    title_id = ' id="shopping-start"' if first else ''
    out = [f'<section class="utility"><h3{title_id}>🛒 材料・買い物</h3><button class="shop-reset" data-week="{week}" type="button">チェック解除</button>']
    idx = 0
    for heading in ('肉・魚・たんぱく','野菜・海藻など','主食・その他'):
        if not groups.get(heading):
            continue
        out.append(f'<div class="shopgroup"><strong>{heading}</strong><div class="shop-checklist">')
        for item in groups[heading]:
            idx += 1
            key = f'w{week}:{item}'
            out.append(
                f'<label class="shop-row"><input class="shop-cb" data-store-key="{escape(key, quote=True)}" id="w{week}-shop-{idx}" type="checkbox"/><span class="shop-item-text">{escape(item)}</span></label>'
            )
        out.append('</div></div>')
    out.append('</section>')
    return ''.join(out)


def main():
    s = P.read_text(encoding='utf-8')
    recipes = json.loads(DATA.read_text(encoding='utf-8'))
    s = re.sub(
        r'<section class="utility">.*?</section>',
        lambda m: build_utility(m.group(0), recipes),
        s,
        flags=re.S,
    )
    P.write_text(s, encoding='utf-8')


if __name__ == '__main__':
    main()
