# FollowSpy NPS Dashboard

A static Net Promoter Score dashboard built from FollowSpy's Zonka survey
export ("Followspy NPS – Zonka"). Published via GitHub Pages.

## What's here

- `index.html` — the published dashboard (static HTML/CSS/JS, no external
  dependencies, no build step required to view it)
- `template.html` — the page template with a `__NPS_DATA_JSON__` placeholder
- `build.py` — regenerates `nps_data.json` and `index.html` from a survey CSV
- `survey_data.csv` — the survey export, stripped of personal data (no
  emails, names, phone numbers, or IP addresses — only response id, date,
  score, country, and free-text reason)
- `nps_data.json` — the aggregated data actually embedded in `index.html`

## Refreshing with new data

1. Export a fresh response sheet from Zonka/Google Sheets as CSV.
2. Keep only these columns (or edit `build.py`'s `keep` list to match your
   export): `Response Id`, `Date & Time`, `NPS`,
   `What is the primary reason for your score?`,
   `On a scale of 0 to 10, how likely are you to recommend Followspy?`,
   `Contact Country`
3. Save it over `survey_data.csv`.
4. Run:

   ```bash
   pip install pandas
   python3 build.py
   ```

5. Commit and push `index.html` and `nps_data.json`. GitHub Pages redeploys
   automatically.

## Methodology

- **NPS** = %Promoters (score 9–10) − %Detractors (score 0–6), among
  responses that completed the 0–10 recommendation question.
- Trend is aggregated **weekly** (not monthly) since this survey's data
  window is short — weekly gives a more readable trend line. Adjust the
  `.dt.to_period('W')` call in `build.py` back to `'M'` if the data window
  grows long enough that monthly makes more sense.
- Responses that didn't answer the score question still count toward total
  response volume and completion rate, but not toward NPS itself.
