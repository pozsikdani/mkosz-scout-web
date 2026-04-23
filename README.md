# mkosz-scout-web

Interaktív scout dashboard MKOSZ kosárlabda csapatokhoz. SvelteKit + Tailwind 4, statikus deploy GitHub Pages-re.

**Tervezett aldomain:** `scout.kozgazkosar.hu`

## M1 scope

- Landing — NB1 B Piros (`hun2a`) 14 csapatának rangsora
- Team overview — helyezés, W/L, dobott/kapott, PPG/OPPG/margin

Forrás: hivatalos MKOSZ tabella (`mkosz.hu/bajnoksag/{season}/{comp}`).

## Adatfrissítés

```bash
python3 scripts/scrape_standings.py                 # defaults: x2526, hun2a
python3 scripts/scrape_standings.py --comp hun2b    # override
```

Az eredmény `static/data/standings/{comp}.json`-ba kerül, commit-elve a repóba.

## Dev

```bash
npm install
npm run dev         # http://localhost:5173/
npm run build       # prerender → build/
```

## Tech stack

- SvelteKit 2 + `@sveltejs/adapter-static` + TypeScript
- Tailwind 4 (`@tailwindcss/vite`)
- Python scrape: `requests` + `beautifulsoup4`
