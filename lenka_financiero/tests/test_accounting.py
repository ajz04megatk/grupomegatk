from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestLenkaAccounting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Contable Lenka'})
        cls.operation = cls.env['lenka.financial.operation'].create({
            'partner_id': cls.partner.id,
            'operation_type': 'loan',
            'principal_amount': 10000.0,
            'interest_rate': 3.0,
            'rate_period': 'monthly',
            'term_months': 12,
            'calculation_method': 'level',
            'is_quote': False,
            'state': 'approved',
        })
        cls.operation.action_generate_schedule()

    def test_disbursement_requires_accounting_configuration(self):
        disbursement = self.env['lenka.disbursement'].create({
            'operation_id': self.operation.id,
            'amount': 10000.0,
            'destination_type': 'client',
            'destination_partner_id': self.partner.id,
        })
        disbursement.action_post()
        with self.assertRaises(ValidationError):
            disbursement.action_create_account_move()

    def test_payment_requires_accounting_configuration(self):
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'amount': 500.0,
            'payment_method': 'transfer',
        })
        payment.action_post()
        with self.assertRaises(ValidationError):
            payment.action_create_account_move()

    def test_existing_move_prevents_duplicate_creation(self):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': self.operation.date,
            'journal_id': self.env['account.journal'].search([
                ('company_id', '=', self.company.id),
                ('type', '=', 'general'),
            ], limit=1).id,
            'line_ids': [],
        })
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'amount': 500.0,
            'payment_method': 'transfer',
            'state': 'posted',
            'move_id': move.id,
        })
        before = payment.move_id
        payment.action_create_account_move()
        self.assertEqual(payment.move_id, before)
