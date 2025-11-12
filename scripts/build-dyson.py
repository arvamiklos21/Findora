name: ingest-dyson

on:
  workflow_dispatch:
  schedule:
    - cron: "10 10,19 * * *"   # 11:10 és 20:10 (HU) – 10:10 és 19:10 UTC

permissions:
  contents: write
  pull-requests: write

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout (full)
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: Install deps
        run: pip install requests

      - name: Build Dyson feed pages
        env:
          FEED_DYSON_URL: ${{ secrets.FEED_DYSON_URL }}
        run: |
          set -e
          if [ -z "$FEED_DYSON_URL" ]; then
            echo "::error title=Missing secret::FEED_DYSON_URL nincs beállítva (Settings → Secrets → Actions)."; exit 1
          fi
          mkdir -p docs/feeds/dyson
          python scripts/build_dyson.py
          echo "Sanity check (first item):"
          if command -v jq >/dev/null 2>&1; then
            jq -r '.items[0] | {title, img, url, price, discount}' docs/feeds/dyson/page-0001.json || true
          else
            head -c 600 docs/feeds/dyson/page-0001.json || true
          fi
          ls -la docs/feeds/dyson

      - name: Prepare clean branch
        run: |
          set -e
          git rebase --abort || true
          git merge --abort || true
          git reset --hard
          git clean -fd

          git fetch origin
          git checkout main
          git reset --hard origin/main

          BR="bot/update-dyson"
          git checkout -B "$BR"

      - name: Commit feed updates
        run: |
          set -e
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          git add docs/feeds/dyson
          git commit -m "dyson: update feed pages" || echo "No changes"
          git push --force-with-lease origin HEAD:bot/update-dyson

      - name: Create pull request
        uses: peter-evans/create-pull-request@v6
        with:
          branch: bot/update-dyson
          delete-branch: true
          title: "dyson: update feed pages"
          commit-message: "dyson: update feed pages"
          body: |
            Automated update of Dyson feed pages (JSON pagination).
          base: main
