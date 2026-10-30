"""Clean filtered comments; keep normalized text of length 5 through 76.

Input: crawling/data/comments_filtered.json (LLM filtering result).
Output: crawling/data/comments_clean.json.
IQR statistics are recorded for reference, not used as length limits.
"""
import json
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'
MIN_LENGTH = 5
MAX_LENGTH = 76


def load_json(file_path):
    with open(file_path, encoding='utf-8') as file:
        return json.load(file)


def save_json(data, file_path):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(f'[Saved] {file_path}')


def to_dataframe(comments):
    # Do not turn missing values, numbers or objects into comment strings.
    texts = [text.strip() for text in comments
             if isinstance(text, str) and text.strip()]
    return pd.DataFrame({'comment': pd.Series(texts, dtype='str')})


def normalize_comment(text):
    # Remove full keycap emoji sequences, including their base digit.
    text = re.sub(r'[0-9#*]\ufe0f?\u20e3', '', text)
    # Remove common ASCII emoticons before stripping punctuation.
    text = re.sub(r'[:;=8][-^"\']?[)(/DPp]+|<3|\^+[_ .-]*\^+|[Tt??][-_.][Tt??]', '', text)
    # Retain Hangul syllables, Latin letters, digits and whitespace.
    # This removes emoji, symbols, isolated jamo (e.g. laughter), ZWJ and selectors.
    text = re.sub(r'[^\uac00-\ud7a3a-zA-Z0-9\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def remove_special_chars(df):
    df = df.copy()
    df['clean'] = df['comment'].map(normalize_comment).astype('str')
    return df


def remove_meaningless(df):
    # Keep meaningful English text; discard empty, numeric and placeholder text.
    normalized = df['clean'].str.casefold()
    meaningless = (
        normalized.isin(['', 'none', 'null', 'nan', 'lol', 'lmao', 'rofl'])
        | df['clean'].str.fullmatch(r'[0-9\s]+', na=False)
    )
    return df.loc[~meaningless].copy()


def get_iqr_thresholds(df):
    lengths = df['clean'].str.len()
    if lengths.empty:
        return None
    q1 = float(lengths.quantile(0.25))
    q3 = float(lengths.quantile(0.75))
    iqr = q3 - q1
    return {'q1': q1, 'q3': q3, 'iqr': iqr,
            'lower': q1 - 1.5 * iqr, 'upper': q3 + 1.5 * iqr}


def remove_length_outliers(df):
    # Apply the fixed requirement, including small input sets.
    df = df.copy()
    df['length'] = df['clean'].str.len()
    return df.loc[df['length'].between(MIN_LENGTH, MAX_LENGTH)].copy()


def prepare_comments(comments):
    df = to_dataframe(comments)
    df = remove_special_chars(df)
    df = remove_meaningless(df)
    thresholds = get_iqr_thresholds(df)
    df = remove_length_outliers(df)
    return df['clean'].tolist(), thresholds


def clean_comments(comments):
    """Reusable entry point for Django or a pipeline; no file or API access."""
    cleaned, _ = prepare_comments(comments)
    return cleaned


if __name__ == '__main__':
    input_path = DATA_DIR / 'comments_filtered.json'
    if not input_path.exists():
        raise SystemExit('Run filter.py first: comments_filtered.json was not found.')

    filtered = load_json(input_path)
    comments = filtered['comments']
    cleaned, thresholds = prepare_comments(comments)

    print(f'[Clean] {len(comments)} -> {len(cleaned)}')
    for index, comment in enumerate(cleaned, 1):
        print(f'{index:02d}. {comment}')

    save_json({
        'company': filtered['company'],
        'stock_code': filtered.get('stock_code'),
        'collected_at': filtered['collected_at'],
        'criteria': filtered.get('criteria'),
        'count': len(cleaned),
        'comments': cleaned,
        'length_limits': {'min': MIN_LENGTH, 'max': MAX_LENGTH},
        'iqr_thresholds': filtered.get('iqr_thresholds', thresholds),
        'raw_comments': filtered.get('raw_comments', []),
        'prepared_comments': filtered.get('prepared_comments', comments),
        'removed': filtered.get('removed', []),
        'timings_seconds': filtered.get('timings_seconds', {}),
    }, DATA_DIR / 'comments_clean.json')
