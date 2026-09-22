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
            'early_withdrawal_rate': 6.0,
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

    def test_early_withdrawal_recalculates_all_interest_at_contractual_early_rate(self):
        investment = self._investment(
            passive_rate=1.5,
            early_withdrawal_rate=1.0,
            rate_period='monthly',
        )
        investment.action_generate_monthly_interest()
        preferential_interest = sum(investment.interest_line_ids.mapped('amount'))

        withdrawal = self.env['lenka.investment.withdrawal'].create({
            'investment_id': investment.id,
            'principal_amount': 20000.0,
            'date': fields.Date.context_today(self.env.user),
        })
        self.assertTrue(withdrawal.early_withdrawal)
        withdrawal.action_post()

        recalculated_interest = withdrawal.accrued_interest_amount
        self.assertAlmostEqual(withdrawal.effective_rate, 1.0, places=4)
        self.assertLess(recalculated_interest, preferential_interest)
        self.assertAlmostEqual(
            withdrawal.total_amount,
            withdrawal.principal_amount + recalculated_interest,
            places=2,
        )

    def test_early_withdrawal_compounds_monthly_at_reduced_rate(self):
        investment = self._investment(
            passive_rate=1.5,
            early_withdrawal_rate=1.0,
            rate_period='monthly',
        )
        withdrawal = self.env['lenka.investment.withdrawal'].create({
            'investment_id': investment.id,
            'principal_amount': 20000.0,
            'date': fields.Date.context_today(self.env.user),
        })
        withdrawal.action_post()
        lines = investment.interest_line_ids.sorted('period_date')
        self.assertGreaterEqual(len(lines), 3)
        self.assertAlmostEqual(lines[0].amount, 1000.0, places=2)
        self.assertAlmostEqual(lines[1].base_amount, 101000.0, places=2)
        self.assertAlmostEqual(lines[1].amount, 1010.0, places=2)


    def test_early_rate_cannot_exceed_preferential_rate(self):
        investment = self.env['lenka.investment'].create({
            'partner_id': self.partner.id,
            'investment_type': 'fixed',
            'principal_amount': 100000.0,
            'passive_rate': 1.0,
            'early_withdrawal_rate': 1.5,
            'rate_period': 'monthly',
            'start_date': fields.Date.context_today(self.env.user),
            'term_months': 12,
            'capitalization': 'monthly',
        })
        with self.assertRaises(ValidationError):
            investment.action_activate()

    def test_withdrawal_before_investment_start_is_rejected(self):
        investment = self._investment(
            passive_rate=1.5,
            early_withdrawal_rate=1.0,
            rate_period='monthly',
        )
        withdrawal = self.env['lenka.investment.withdrawal'].create({
            'investment_id': investment.id,
            'principal_amount': 10000.0,
            'date': fields.Date.add(investment.start_date, days=-1),
        })
        with self.assertRaises(ValidationError):
            withdrawal.action_post()


    def test_fixed_investment_requires_early_withdrawal_rate(self):
        investment = self.env['lenka.investment'].create({
            'partner_id': self.partner.id,
            'investment_type': 'fixed',
            'principal_amount': 100000.0,
            'passive_rate': 1.5,
            'early_withdrawal_rate': 0.0,
            'rate_period': 'monthly',
            'start_date': fields.Date.context_today(self.env.user),
            'term_months': 12,
            'capitalization': 'monthly',
        })
        with self.assertRaises(ValidationError):
            investment.action_activate()


    def test_interest_tax_is_split_into_gross_tax_and_net(self):
        investment = self._investment()
        interest = self.env['lenka.investment.interest'].create({
            'investment_id': investment.id,
            'period_date': fields.Date.context_today(self.env.user),
            'base_amount': 100000.0,
            'rate': 1.0,
            'amount': 1000.0,
            'tax_rate': 10.0,
            'state': 'accrued',
        })
        self.assertAlmostEqual(interest.tax_amount, 100.0, places=2)
        self.assertAlmostEqual(interest.net_amount, 900.0, places=2)

    def test_interest_tax_rate_must_be_valid_percentage(self):
        investment = self._investment()
        with self.assertRaises(ValidationError):
            self.env['lenka.investment.interest'].create({
                'investment_id': investment.id,
                'period_date': fields.Date.context_today(self.env.user),
                'base_amount': 100000.0,
                'rate': 1.0,
                'amount': 1000.0,
                'tax_rate': 101.0,
                'state': 'accrued',
            })


    def test_maturity_withdrawal_uses_only_unpaid_net_interest(self):
        today = fields.Date.context_today(self.env.user)
        investment = self._investment(
            passive_rate=1.5,
            early_withdrawal_rate=1.0,
            rate_period='monthly',
            start_date=fields.Date.add(today, months=-3),
            maturity_date=today,
            term_months=3,
        )
        self.env['lenka.investment.interest'].create({
            'investment_id': investment.id,
            'period_date': fields.Date.add(today, months=-2),
            'base_amount': 100000.0,
            'rate': 1.5,
            'amount': 1500.0,
            'tax_rate': 10.0,
            'state': 'paid',
        })
        pending = self.env['lenka.investment.interest'].create({
            'investment_id': investment.id,
            'period_date': fields.Date.add(today, months=-1),
            'base_amount': 101500.0,
            'rate': 1.5,
            'amount': 1522.50,
            'tax_rate': 10.0,
            'state': 'accrued',
        })
        investment.action_generate_monthly_interest()
        expected_pending_net = sum(investment.interest_line_ids.filtered(lambda l: l.state == 'accrued').mapped('net_amount'))
        withdrawal = self.env['lenka.investment.withdrawal'].create({
            'investment_id': investment.id,
            'principal_amount': 100000.0,
            'date': today,
        })
        withdrawal.action_post()
        self.assertFalse(withdrawal.early_withdrawal)
        self.assertGreaterEqual(expected_pending_net, pending.net_amount)
        self.assertAlmostEqual(withdrawal.accrued_interest_amount, expected_pending_net, places=2)
        self.assertEqual(investment.state, 'closed')

    def test_partial_maturity_withdrawal_keeps_investment_open(self):
        today = fields.Date.context_today(self.env.user)
        investment = self._investment(
            start_date=fields.Date.add(today, months=-12),
            maturity_date=today,
            term_months=12,
        )
        withdrawal = self.env['lenka.investment.withdrawal'].create({
            'investment_id': investment.id,
            'principal_amount': 25000.0,
            'date': today,
        })
        withdrawal.action_post()
        self.assertAlmostEqual(investment.outstanding_principal, 75000.0, places=2)
        self.assertNotEqual(investment.state, 'closed')
