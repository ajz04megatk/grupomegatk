from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestLenkaInvestment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Inversionista Prueba Lenka'})

    def _investment(self, **extra):
        vals = {
            'partner_id': self.partner.id,
            'investment_type': 'fixed',
            'principal_amount': 100000.0,
            'passive_rate': 12.0,
            'rate_period': 'annual',
            'start_date': fields.Date.add(fields.Date.context_today(self.env.user), months=-3),
            'term_months': 12,
            'capitalization': 'monthly',
        }
        vals.update(extra)
        investment = self.env['lenka.investment'].create(vals)
        investment.action_activate()
        return investment

    def test_monthly_interest_12_percent_annual(self):
        investment = self._investment()
        investment.action_generate_monthly_interest()
        self.assertTrue(investment.interest_line_ids)
        first = investment.interest_line_ids.sorted('period_date')[0]
        self.assertAlmostEqual(first.amount, 1000.0, places=2)

    def test_monthly_capitalization_increases_interest_base(self):
        investment = self._investment()
        investment.action_generate_monthly_interest()
        lines = investment.interest_line_ids.sorted('period_date')
        if len(lines) >= 2:
            self.assertGreater(lines[1].base_amount, lines[0].base_amount)
            self.assertGreater(lines[1].amount, lines[0].amount)

    def test_withdrawal_cannot_exceed_outstanding_principal(self):
        investment = self._investment()
        withdrawal = self.env['lenka.investment.withdrawal'].create({
            'investment_id': investment.id,
            'principal_amount': 120000.0,
            'date': fields.Date.context_today(self.env.user),
        })
        with self.assertRaises(ValidationError):
            withdrawal.action_post()

    def test_early_withdrawal_penalty_reduces_interest_payment(self):
        investment = self._investment()
        withdrawal = self.env['lenka.investment.withdrawal'].create({
            'investment_id': investment.id,
            'principal_amount': 20000.0,
            'accrued_interest_amount': 1000.0,
            'penalty_rate': 25.0,
            'date': fields.Date.context_today(self.env.user),
        })
        self.assertTrue(withdrawal.early_withdrawal)
        self.assertAlmostEqual(withdrawal.penalty_amount, 250.0, places=2)
        self.assertAlmostEqual(withdrawal.total_amount, 20750.0, places=2)
