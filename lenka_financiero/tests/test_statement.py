from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLenkaStatement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Estado Lenka'})
        cls.other_partner = cls.env['res.partner'].create({'name': 'Cliente Incorrecto Lenka'})
        cls.operation = cls.env['lenka.financial.operation'].create({
            'partner_id': cls.partner.id,
            'operation_type': 'loan',
            'principal_amount': 10000.0,
            'interest_rate': 3.0,
            'rate_period': 'monthly',
            'term_months': 12,
            'calculation_method': 'level',
            'state': 'review',
        })
        cls.operation.action_generate_schedule()
        cls.operation.state = 'active'

    def test_operation_statement_balance_uses_capital_only(self):
        first = self.operation.schedule_line_ids.sorted('sequence')[0]
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'payment_date': first.date,
            'amount': first.amount_due,
            'payment_method': 'cash',
        })
        payment.action_post()
        statement = self.env['lenka.statement'].create({
            'statement_type': 'operation',
            'partner_id': self.partner.id,
            'operation_id': self.operation.id,
            'company_id': self.operation.company_id.id,
            'currency_id': self.operation.currency_id.id,
            'date_from': first.date,
            'date_to': first.date,
        })
        statement.action_generate()
        self.assertAlmostEqual(statement.opening_balance, 10000.0, places=2)
        self.assertAlmostEqual(
            statement.closing_balance,
            10000.0 - payment.capital_amount,
            places=2,
        )
        self.assertAlmostEqual(statement.period_interest, payment.interest_amount, places=2)

    def test_statement_rejects_wrong_partner(self):
        today = fields.Date.context_today(self.env.user)
        with self.assertRaises(ValidationError):
            self.env['lenka.statement'].create({
                'statement_type': 'operation',
                'partner_id': self.other_partner.id,
                'operation_id': self.operation.id,
                'company_id': self.operation.company_id.id,
                'currency_id': self.operation.currency_id.id,
                'date_from': today - timedelta(days=30),
                'date_to': today,
            })

    def test_statement_rejects_inverted_dates(self):
        today = fields.Date.context_today(self.env.user)
        with self.assertRaises(ValidationError):
            self.env['lenka.statement'].create({
                'statement_type': 'operation',
                'partner_id': self.partner.id,
                'operation_id': self.operation.id,
                'company_id': self.operation.company_id.id,
                'currency_id': self.operation.currency_id.id,
                'date_from': today,
                'date_to': today - timedelta(days=1),
            })
