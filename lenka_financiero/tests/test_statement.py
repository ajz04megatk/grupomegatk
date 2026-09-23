from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLenkaStatement(TransactionCase):

    def _statement(self):
        return self.env['lenka.statement'].create({
            'statement_type': 'operation', 'partner_id': self.partner.id,
            'operation_id': self.operation.id, 'company_id': self.operation.company_id.id,
            'currency_id': self.operation.currency_id.id,
            'date_from': fields.Date.today(), 'date_to': fields.Date.add(fields.Date.today(), months=2),
        })

    def test_draft_identity_edits_are_revalidated(self):
        statement = self._statement()
        other_currency = self.env['res.currency'].with_context(active_test=False).search([('id', '!=', statement.currency_id.id)], limit=1)
        other_company = self.env['res.company'].create({'name': 'Empresa estado incorrecto'})
        for vals in [{'partner_id': self.other_partner.id}, {'currency_id': other_currency.id}, {'company_id': other_company.id}]:
            with self.subTest(vals=vals), self.assertRaises(ValidationError), self.cr.savepoint():
                statement.write(vals)

    def test_sent_statement_cannot_be_regenerated_or_rewritten(self):
        statement = self._statement()
        statement.action_generate()
        statement.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
        for vals in [{'date_to': fields.Date.today()}, {'closing_balance': 1.0}, {'state': 'draft'}]:
            with self.subTest(vals=vals), self.assertRaises(ValidationError):
                statement.write(vals)
        with self.assertRaises(ValidationError):
            statement.action_generate()
        with self.assertRaisesRegex(ValidationError, 'Solo pueden enviarse'):
            statement.action_send_email()

    def test_generated_statement_period_cannot_change(self):
        statement = self._statement()
        statement.action_generate()
        with self.assertRaises(ValidationError):
            statement.date_from = fields.Date.add(statement.date_from, days=1)

    def test_duplicate_statement_is_clean_draft(self):
        statement = self._statement()
        statement.action_generate()
        statement.write({'state': 'sent', 'sent_date': fields.Datetime.now()})
        copy = statement.copy()
        self.assertEqual(copy.state, 'draft')
        self.assertFalse(copy.sent_date)
        self.assertFalse(copy.line_ids)
        self.assertAlmostEqual(copy.opening_balance, 0.0, places=2)
        self.assertAlmostEqual(copy.closing_balance, 0.0, places=2)
        copy.action_generate()
        self.assertEqual(copy.closing_balance, statement.closing_balance)

    def test_cancelled_statement_cannot_be_generated_or_sent(self):
        statement = self._statement()
        statement.state = 'cancelled'
        with self.assertRaises(ValidationError):
            statement.action_generate()
        with self.assertRaisesRegex(ValidationError, 'Solo pueden enviarse'):
            statement.action_send_email()

    def test_onchange_source_fills_identity_and_currency(self):
        statement = self.env['lenka.statement'].new({'statement_type': 'operation', 'operation_id': self.operation.id})
        statement._onchange_source()
        self.assertEqual(statement.partner_id, self.partner)
        self.assertEqual(statement.company_id, self.operation.company_id)
        self.assertEqual(statement.currency_id, self.operation.currency_id)

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
