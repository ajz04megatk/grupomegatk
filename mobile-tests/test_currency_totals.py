"""Run without an Odoo server: python3 -m unittest discover -s mobile-tests."""
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / 'lenka_financiero/models/mobile_totals.py'
spec = importlib.util.spec_from_file_location('mobile_totals', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
summary = module.summarize_by_currency


class CurrencyTotalsTest(unittest.TestCase):
    def test_mixed_currencies_never_have_a_combined_balance(self):
        result = summary([
            {'currency': 'HNL', 'balance': 25000},
            {'currency': 'USD', 'balance': 1000},
            {'currency': 'HNL', 'balance': 5000},
        ], ('balance',))
        self.assertIsNone(result['balance'])
        self.assertIsNone(result['currency'])
        self.assertEqual(result['by_currency'], [
            {'currency': 'HNL', 'count': 2, 'balance': 30000},
            {'currency': 'USD', 'count': 1, 'balance': 1000},
        ])

    def test_single_currency_is_labeled(self):
        result = summary([{'currency': 'USD', 'balance': 75}], ('balance',))
        self.assertEqual((result['currency'], result['balance']), ('USD', 75))

    def test_empty_portfolio_does_not_invent_currency(self):
        result = summary([], ('balance',))
        self.assertEqual(result['by_currency'], [])
        self.assertEqual(result['count'], 0)
        self.assertIsNone(result['balance'])

    def test_interest_is_not_added_to_principal(self):
        result = summary([{'currency': 'HNL', 'principal': 100, 'interest': 10}],
                         ('principal', 'interest'))
        self.assertEqual(result['principal'], 100)
        self.assertEqual(result['interest'], 10)

    def test_decimal_totals(self):
        result = summary([{'currency': 'USD', 'balance': n} for n in (0.1, 0.2)],
                         ('balance',))
        self.assertEqual(result['balance'], 0.3)


if __name__ == '__main__':
    unittest.main()
