"""Serialize fictional records through the actual service, without an Odoo ORM.

Only payload compatibility and relation filtering are exercised here.
"""
from datetime import date
import json
from pathlib import Path
import sys
from types import SimpleNamespace as Record
from test_service_domains import Service, QueryRecorder


class Records(list):
    def filtered(self, predicate):
        return Records(row for row in self if predicate(row))

    def sorted(self, field, reverse=False):
        return Records(sorted(self, key=lambda row: getattr(row, field), reverse=reverse))


def fixtures():
    deposits = Records()
    statements = Records()
    for ident, currency in ((1, 'HNL'), (2, 'USD')):
        deposits.append(Record(
            id=ident, name=f'Depósito ficticio {ident}', currency_id=Record(name=currency),
            investment_type='fixed', state='active', principal_amount=1000.0,
            outstanding_principal=900.0, accrued_interest=10.0, paid_interest=9.0,
            passive_rate=1.0, early_withdrawal_rate=0.5, rate_period='monthly',
            start_date=date(2026, 1, 1), maturity_date=date(2027, 1, 1),
            capitalization='monthly', notes='INTERNAL-NOT-FOR-MOBILE',
            interest_line_ids=Records([
                Record(period_date=date(2026, 2, 1), base_amount=1000, rate=1,
                       amount=10, tax_amount=1, net_amount=9, state='paid'),
                Record(period_date=date(2026, 3, 1), base_amount=900, rate=1,
                       amount=9, tax_amount=.9, net_amount=8.1, state='draft'),
            ]),
            withdrawal_ids=Records([
                Record(date=date(2026, 2, 1), principal_amount=100,
                       accrued_interest_amount=9, gross_interest_amount=10,
                       interest_tax_amount=1, effective_rate=.5, total_amount=109,
                       early_withdrawal=True, state='posted'),
                Record(date=date(2026, 3, 1), state='draft'),
            ]),
        ))
        statements.append(Record(
            id=ident, name=f'Estado ficticio {ident}', statement_type='investment',
            currency_id=Record(name=currency), state='generated',
            date_from=date(2026, 1, 1), date_to=date(2026, 2, 1),
            opening_balance=1000, closing_balance=900, period_capital=100,
            period_interest=9, period_late_fees=0, period_fees=0,
        ))

    class Environment(QueryRecorder):
        def __getitem__(self, model):
            class Search:
                def sudo(self):
                    return self

                def search(self, domain, **kwargs):
                    if model == 'lenka.investment':
                        ids = [clause[2] for clause in domain if clause[:2] == ('id', '=')]
                        return next(row for row in deposits if row.id == ids[0]) if ids else deposits
                    if model == 'lenka.statement':
                        return statements
                    return Records()
            return Search()

    service = Service()
    service.env = Environment()
    # Supply only Odoo's date serializer to the loaded service module.
    service.get_my_investments.__globals__['fields'] = Record(
        Date=Record(to_string=lambda value: value.isoformat() if value else False))
    return {
        'deposits': service.get_my_investments(),
        'details': [service.get_my_investment_detail(ident) for ident in (1, 2)],
        'statements': service.get_my_statements(),
    }


if __name__ == '__main__':
    payload = fixtures()
    text = json.dumps(payload, ensure_ascii=False)
    assert 'INTERNAL-NOT-FOR-MOBILE' not in text
    assert all(len(row['interest_history']) == len(row['withdrawals']) == 1
               for row in payload['details'])
    Path(sys.argv[1]).write_text(text, encoding='utf-8')
