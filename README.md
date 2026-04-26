# Journal Tracker

A small public tracker for Scopus and Web of Science journals. The site is plain
static HTML/CSS/JS, so GitHub Pages can publish it without a build step.

## Add a Journal

Run the helper from the repository root:

```sh
python3 scripts/add_journal.py \
  --title "Journal of Example Studies" \
  --publisher "Example Publisher" \
  --issn "1234-5678" \
  --eissn "2345-6789" \
  --free \
  --scopus \
  --web-of-science \
  --quartile "Q2" \
  --subject "Computer Science" \
  --url "https://example.org/journal"
```

Use `--free` for journals with no publication fee. For paid journals, use:

```sh
python3 scripts/add_journal.py \
  --title "Paid Journal Example" \
  --price 1200 \
  --currency USD
```

Then commit and tag a release:

```sh
git add data/journals.json
git commit -m "Add Journal of Example Studies"
git tag v2026.04.26
git push origin main --tags
```

When a tag matching `v*` is pushed, GitHub Actions publishes the site to GitHub
Pages.

## Optional Interactive Mode

```sh
python3 scripts/add_journal.py --interactive
```

## Local Preview

Run a tiny local web server:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Data

Journal records are stored in [data/journals.json](data/journals.json). Each
record has:

- `title`
- `publisher`
- `issn`
- `eissn`
- `price.type`
- `price.value`
- `price.currency`
- `indexes.scopus`
- `indexes.web_of_science`
- `quartile`
- `subjects`
- `url`
- `notes`
- `updated_at`
