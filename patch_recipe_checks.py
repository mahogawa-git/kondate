from pathlib import Path
import re

INDEX = Path(__file__).resolve().parent / "index.html"

CSS = r'''

/* recipe completion checks */
.recipe-done-wrap{flex:0 0 auto;display:inline-flex;align-items:center;margin-left:2px;cursor:pointer;user-select:none}
.recipe-done-cb{width:19px;height:19px;margin:0;accent-color:#6f8f68;cursor:pointer}
.row.recipe-done .dishname{text-decoration:line-through;opacity:.46}
.row.recipe-done .title-icons{opacity:.48}
.recipe-reset-wrap{display:flex;justify-content:flex-end;margin:-2px 0 8px}
.recipe-reset{border:1px solid #ddd4c7;background:#f7f3ed;color:#6a6258;border-radius:999px;padding:6px 11px;font-size:11px;font-weight:700;min-height:30px;cursor:pointer}
@media(max-width:390px){.recipe-done-cb{width:20px;height:20px}}
'''

JS = r'''
<script>
/* その週に作ったレシピのチェック。レシピURL単位で保存するので曜日を入れ替えても維持される */
document.addEventListener('DOMContentLoaded', () => {
  const prefix = 'mealplan:recipe-done:';

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
          localStorage.removeItem(prefix + cb.dataset.recipeKey);
        });
      });
    }

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
      cb.checked = localStorage.getItem(prefix + recipeKey) === '1';

      label.appendChild(cb);
      titleRow.appendChild(label);
      row.classList.toggle('recipe-done', cb.checked);

      cb.addEventListener('change', () => {
        row.classList.toggle('recipe-done', cb.checked);
        if (cb.checked) localStorage.setItem(prefix + recipeKey, '1');
        else localStorage.removeItem(prefix + recipeKey);
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
        r'\n/\* recipe completion checks \*/.*?(?=\n</style>)',
        CSS.rstrip(),
        html,
        count=1,
        flags=re.S,
    )
    if "/* recipe completion checks */" not in html:
        html = html.replace("\n</style>", CSS + "\n</style>", 1)

    html = re.sub(
        r'\n<script>\n/\* その週に作ったレシピのチェック。.*?</script>\n',
        "\n" + JS + "\n",
        html,
        count=1,
        flags=re.S,
    )
    if "mealplan:recipe-done:" not in html:
        html = html.replace("\n</body>", "\n" + JS + "\n</body>", 1)

    INDEX.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
