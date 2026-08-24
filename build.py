#!/usr/bin/env python3
"""
Build script for the FollowSpy NPS dashboard.

Regenerate index.html from survey_data.csv (a Zonka NPS export, PII-stripped)
whenever you have a fresher export:

    python3 build.py

It re-reads survey_data.csv, recomputes nps_data.json, and re-injects it
into template.html to produce index.html (the file GitHub Pages serves).
"""
import pandas as pd
import json
import re
from collections import Counter
from datetime import datetime, timezone

SCORE_COL = 'On a scale of 0 to 10, how likely are you to recommend Followspy?'
REASON_COL = 'What is the primary reason for your score?'
COUNTRY_COL = 'Contact Country'


def bucket(score):
    if score >= 9:
        return 'Promoter'
    if score >= 7:
        return 'Passive'
    return 'Detractor'


def build_data(csv_path='survey_data.csv'):
    df = pd.read_csv(csv_path)
    df[REASON_COL] = df[REASON_COL].fillna('-').astype(str)
    df[COUNTRY_COL] = df[COUNTRY_COL].fillna('-').astype(str)
    df['score'] = pd.to_numeric(df[SCORE_COL], errors='coerce')
    df['dt'] = pd.to_datetime(df['Date & Time'], errors='coerce')
    # Weekly buckets — this survey's data window is short (~2.5 months),
    # so weekly gives a more readable trend than monthly.
    df['period'] = df['dt'].dt.to_period('W').apply(lambda p: p.start_time.strftime('%Y-%m-%d'))

    valid = df.dropna(subset=['score']).copy()
    valid['segment'] = valid['score'].apply(bucket)

    total_responses = len(df)
    total_scored = len(valid)
    promoters = int((valid['segment'] == 'Promoter').sum())
    passives = int((valid['segment'] == 'Passive').sum())
    detractors = int((valid['segment'] == 'Detractor').sum())
    overall_nps = round((promoters - detractors) / total_scored * 100, 1) if total_scored else 0.0

    weekly = valid.groupby('period').agg(
        total=('score', 'count'),
        promoters=('segment', lambda x: int((x == 'Promoter').sum())),
        passives=('segment', lambda x: int((x == 'Passive').sum())),
        detractors=('segment', lambda x: int((x == 'Detractor').sum())),
    ).reset_index().rename(columns={'period': 'month'})
    weekly['nps'] = ((weekly['promoters'] - weekly['detractors']) / weekly['total'] * 100).round(1)
    weekly_records = weekly.to_dict('records')

    dist = valid['score'].value_counts().sort_index()
    dist_records = [{'score': int(k), 'count': int(v)} for k, v in dist.items()]

    volume_records = df.groupby('period').size().reset_index(name='count').rename(columns={'period': 'month'}).to_dict('records')

    valid['reason_clean'] = valid[REASON_COL].str.strip()
    valid_reasons = valid[
        (valid['reason_clean'] != '-')
        & (valid['reason_clean'].str.lower() != 'nan')
        & (valid['reason_clean'] != '')
    ]

    def top_comments(seg, n=15):
        sub = valid_reasons[valid_reasons['segment'] == seg].sort_values('dt', ascending=False)
        return [
            {'date': r['dt'].strftime('%b %d, %Y'), 'score': int(r['score']), 'text': r['reason_clean']}
            for _, r in sub.head(n).iterrows()
        ]

    stop = set('the a an and to for is it of in on my i im with too very that this so not no be '
               'are was were get more your you have has had can does do did'.split())
    words = Counter()
    for t in valid_reasons[valid_reasons['segment'] == 'Detractor']['reason_clean']:
        for w in re.findall(r"[a-zA-Z']+", t.lower()):
            if w not in stop and len(w) > 2:
                words[w] += 1

    country_series = df[df[COUNTRY_COL].str.strip() != '-'][COUNTRY_COL].str.strip().str.title()
    country_counts = country_series.value_counts().head(10)
    country_records = [{'country': k, 'count': int(v)} for k, v in country_counts.items()]

    return {
        'summary': {
            'total_responses': total_responses,
            'total_scored': total_scored,
            'completion_rate': round(total_scored / total_responses * 100, 1) if total_responses else 0.0,
            'promoters': promoters,
            'passives': passives,
            'detractors': detractors,
            'overall_nps': overall_nps,
            'date_range_start': df['dt'].min().strftime('%b %d, %Y'),
            'date_range_end': df['dt'].max().strftime('%b %d, %Y'),
            'countries_identified': int((df[COUNTRY_COL].str.strip() != '-').sum()),
        },
        'monthly': weekly_records,
        'distribution': dist_records,
        'volume': volume_records,
        'detractor_comments': top_comments('Detractor', 15),
        'promoter_comments': top_comments('Promoter', 15),
        'passive_comments': top_comments('Passive', 15),
        'top_detractor_words': [{'word': w, 'count': c} for w, c in words.most_common(15)],
        'top_countries': country_records,
        'period_label': 'week',
    }


def main():
    data = build_data()
    with open('nps_data.json', 'w') as f:
        json.dump(data, f, indent=2)

    with open('template.html', 'r') as f:
        template = f.read()

    generated = datetime.now(timezone.utc).strftime('%b %d, %Y')
    html = template.replace('__NPS_DATA_JSON__', json.dumps(data))
    html = html.replace('__DATE_START__', data['summary']['date_range_start'])
    html = html.replace('__DATE_END__', data['summary']['date_range_end'])
    html = html.replace('__GENERATED_DATE__', generated)
    html = html.replace('__SCORED__', str(data['summary']['total_scored']))
    html = html.replace('__TOTAL__', str(data['summary']['total_responses']))
    html = html.replace('__COUNTRIES_IDENTIFIED__', str(data['summary']['countries_identified']))

    with open('index.html', 'w') as f:
        f.write(html)

    print('Wrote index.html and nps_data.json')
    print(json.dumps(data['summary'], indent=2))


if __name__ == '__main__':
    main()
