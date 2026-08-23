from pathlib import Path
import re

INDEX = Path(__file__).resolve().parent / "index.html"

CSS = r'''

/* recipe completion checks + day controls */
.recipe-done-wrap{flex:0 0 auto;display:inline-flex;align-items:center;margin-left:2px;cursor:pointer;user-select:none}
.recipe-done-cb{width:19px;height:19px;margin:0;accent-color:#6f8f68;cursor:pointer}
.row.recipe-done .dishname{text-decoration:line-through;opacity:.46}
.row.recipe-done .title-icons{opacity:.48}
.recipe-reset-wrap{display:flex;justify-content:flex-end;margin:-2px 0 8px}
.recipe-reset{border:1px solid #ddd4c7;background:#f7f3ed;color:#6a6258;border-radius:999px;padding:6px 11px;font-size:11px;font-weight:700;min-height:30px;cursor:pointer}
.day-head-row{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 10px}
.day-head-row h3{margin:0!important}
.oneop-label{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;color:#6a6258;white-space:nowrap;cursor:pointer;user-select:none}
.oneop-cb{width:17px;height:17px;margin:0;accent-color:#b57b62;cursor:pointer}
.daycard.oneop-day{border-color:#e7cabc;background:#fffaf7}
.menu-override{width:100%;margin:0 0 8px;padding:7px 9px;border:1px solid #e1ddd5;border-radius:9px;background:#faf9f6;color:#3f3b36;font:inherit;font-size:12px;line-height:1.4;outline:none}
.menu-override:focus{border-color:#bcb2a5;background:#fff}
.menu-override::placeholder{color:#a19a90}
.menu-override:not(:placeholder-shown){background:#fff8df;border-color:#e3d196}
@media(max-width:390px){.recipe-done-cb{width:20px;height:20px}.oneop-cb{width:18px;height:18px}.menu-override{font-size:13px}}
'''

JS = r'''
<script>
/* レシピの作成済みチェック + 曜日ごとのワンオペ・変更メニュー。ブラウザ内に保存する */
document.addEventListener('DOMContentLoaded', () => {
  const recipePrefix = 'mealplan:recipe-done:';
  const oneopPrefix = 'mealplan:oneop:';
  const overridePrefix = 'mealplan:menu-override:';

  document.querySelectorAll('.week').forEach(weekEl => {
    const week = weekEl.dataset.week;
    const firstCard = weekEl.querySelector('.daycard');
    if (firstCard && !weekEl.querySelector('.recipe-reset-wrap')) {
      const resetWrap = document.createElement('div');
      resetWrap.className = 'recipe-reset-wrap';
      const reset = document.createElement('button');
      reset.type = 'button';
      reset.className = 'recipe-reset';
      reset.textContent = '作ったチェックをリセット';
      resetWrap.appendChild(reset);
      firstCard.before(resetWrap);

      reset.addEventListener('click', () => {
        weekEl.querySelectorAll('.recipe-done-cb').forEach(cb => {
          cb.checked = false;
          cb.closest('.row')?.classList.remove('recipe-done');
          localStorage.removeItem(recipePrefix + cb.dataset.recipeKey);
        });
      });
    }

    weekEl.querySelectorAll('.daycard').forEach(card => {
      const h3 = card.querySelector(':scope > h3');
      if (!h3) return;
      const day = h3.textContent.trim();
      const dayKey = `w${week}:${day}`;

      if (!card.querySelector('.day-head-row')) {
        const head = document.createElement('div');
        head.className = 'day-head-row';
        h3.before(head);
        head.appendChild(h3);

        const oneopLabel = document.createElement('label');
        oneopLabel.className = 'oneop-label';
        const oneop = document.createElement('input');
        oneop.type = 'checkbox';
        oneop.className = 'oneop-cb';
        oneop.checked = localStorage.getItem(oneopPrefix + dayKey) === '1';
        const oneopText = document.createElement('span');
        oneopText.textContent = 'ワンオペ';
        oneopLabel.append(oneop, oneopText);
        head.appendChild(oneopLabel);
        card.classList.toggle('oneop-day', oneop.checked);

        oneop.addEventListener('change', () => {
          card.classList.toggle('oneop-day', oneop.checked);
          if (oneop.checked) localStorage.setItem(oneopPrefix + dayKey, '1');
          else localStorage.removeItem(oneopPrefix + dayKey);
        });
      }

      if (!card.querySelector('.menu-override')) {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'menu-override';
        input.placeholder = '別メニューにする時のメモ';
        input.setAttribute('aria-label', `${day}の変更メニュー`);
        input.value = localStorage.getItem(overridePrefix + dayKey) || '';
        const head = card.querySelector('.day-head-row');
        head?.after(input);
        input.addEventListener('input', () => {
          const v = input.value.trim();
          if (v) localStorage.setItem(overridePrefix + dayKey, input.value);
          else localStorage.removeItem(overridePrefix + dayKey);
        });
      }
    });

    weekEl.querySelectorAll('.daycard .row').forEach(row => {
      if (row.querySelector('.recipe-done-cb')) return;
      const titleRow = row.querySelector('.dish-title-row');
      const dishLink = row.querySelector('.dishname a');
      const dishName = row.querySelector('.dishname');
      if (!titleRow || !dishName) return;

      const stableRecipeId = dishLink?.href || dishName.textContent.trim();
      const recipeKey = `w${week}:${stableRecipeId}`;

      const label = document.createElement('label');
      label.className = 'recipe-done-wrap';
      label.title = '作った';
      label.setAttribute('aria-label', '作った');

      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.className = 'recipe-done-cb';
      cb.dataset.recipeKey = recipeKey;
      cb.checked = localStorage.getItem(recipePrefix + recipeKey) === '1';

      label.appendChild(cb);
      titleRow.appendChild(label);
      row.classList.toggle('recipe-done', cb.checked);

      cb.addEventListener('change', () => {
        row.classList.toggle('recipe-done', cb.checked);
        if (cb.checked) localStorage.setItem(recipePrefix + recipeKey, '1');
        else localStorage.removeItem(recipePrefix + recipeKey);
      });
    });
  });
});
</script>
'''


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")

    # Replace the whole feature blocks so future syncs always get the latest UI.
    html = re.sub(
        r'\n/\* recipe completion checks(?: \+ day controls)? \*/.*?(?=\n</style>)',
        CSS.rstrip(),
        html,
        count=1,
        flags=re.S,
    )
    if "/* recipe completion checks + day controls */" not in html:
        html = html.replace("\n</style>", CSS + "\n</style>", 1)

    html = re.sub(
        r'\n<script>\n/\* (?:その週に作ったレシピのチェック。|レシピの作成済みチェック \+ 曜日ごとのワンオペ・変更メニュー。).*?</script>\n',
        "\n" + JS + "\n",
        html,
        count=1,
        flags=re.S,
    )
    if "mealplan:oneop:" not in html:
        html = html.replace("\n</body>", "\n" + JS + "\n</body>", 1)

    INDEX.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
