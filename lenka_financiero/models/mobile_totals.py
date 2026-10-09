"""Currency-safe mobile totals. No exchange or estimated available balance."""
from decimal import Decimal


def summarize_by_currency(rows, amount_fields):
    buckets = {}
    count = 0
    for row in rows:
        currency = row['currency']
        bucket = buckets.setdefault(currency, {
            'currency': currency, 'count': 0,
            **{field: Decimal('0') for field in amount_fields},
        })
        bucket['count'] += 1
        count += 1
        for field in amount_fields:
            bucket[field] += Decimal(str(row[field]))
    totals = [{**bucket, **{field: float(bucket[field]) for field in amount_fields}}
              for _, bucket in sorted(buckets.items())]
    # Legacy totals are meaningful only when exactly one currency is present.
    # Empty/mixed portfolios use null, never a misleading combined amount.
    return {
        'count': count,
        'currency': totals[0]['currency'] if len(totals) == 1 else None,
        'by_currency': totals,
        **{field: totals[0][field] if len(totals) == 1 else None
           for field in amount_fields},
    }
