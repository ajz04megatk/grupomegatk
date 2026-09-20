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
        cls.operation.write({'contract_signed': True, 'state': 'contracted'})
        cls.env['lenka.funding.line'].create({
            'operation_id': cls.operation.id,
            'source_type': 'own',
            'reference': 'Fondeo contable de prueba',
            'amount': 10000.0,
            'cost_rate': 0.0,
            'cost_period': 'annual',
        })

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
        self.operation.state = 'active'
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


    def _configure_accounting(self):
        journal = self.env['account.journal'].search([
            ('company_id', '=', self.company.id),
            ('type', '=', 'general'),
            ('default_account_id', '!=', False),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].search([
                ('company_id', '=', self.company.id),
                ('default_account_id', '!=', False),
            ], limit=1)
        accounts = self.env['account.account'].search([
            ('company_ids', 'in', self.company.id),
        ], limit=5)
        if len(accounts) < 5:
            self.skipTest('La base de prueba no contiene suficientes cuentas contables.')
        self.company.write({
            'lenka_disbursement_journal_id': journal.id,
            'lenka_collection_journal_id': journal.id,
            'lenka_portfolio_account_id': accounts[0].id,
            'lenka_interest_income_account_id': accounts[1].id,
            'lenka_late_fee_income_account_id': accounts[2].id,
            'lenka_unapplied_account_id': accounts[3].id,
            'lenka_card_fee_expense_account_id': accounts[4].id,
        })
        return journal

    def test_disbursement_account_move_stays_draft(self):
        self._configure_accounting()
        disbursement = self.env['lenka.disbursement'].create({
            'operation_id': self.operation.id,
            'amount': 10000.0,
            'destination_type': 'client',
            'destination_partner_id': self.partner.id,
        })
        disbursement.action_post()
        disbursement.action_create_account_move()
        self.assertTrue(disbursement.move_id)
        self.assertEqual(disbursement.move_id.state, 'draft')

    def test_collection_account_move_stays_draft(self):
        self._configure_accounting()
        self.operation.state = 'active'
        first = self.operation.schedule_line_ids.sorted('sequence')[0]
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'payment_date': first.date,
            'amount': 500.0,
            'payment_method': 'transfer',
        })
        payment.action_post()
        payment.action_create_account_move()
        self.assertTrue(payment.move_id)
        self.assertEqual(payment.move_id.state, 'draft')

    def test_account_move_creation_is_idempotent(self):
        self._configure_accounting()
        self.operation.state = 'active'
        first = self.operation.schedule_line_ids.sorted('sequence')[0]
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'payment_date': first.date,
            'amount': 500.0,
            'payment_method': 'transfer',
        })
        payment.action_post()
        payment.action_create_account_move()
        first_move = payment.move_id
        payment.action_create_account_move()
        self.assertEqual(payment.move_id, first_move)


    def test_card_fee_is_booked_separately(self):
        self._configure_accounting()
        self.operation.state = 'active'
        first = self.operation.schedule_line_ids.sorted('sequence')[0]
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'payment_date': first.date,
            'amount': 1000.0,
            'payment_method': 'card',
            'card_fee_rate': 3.5,
        })
        payment.action_post()
        self.assertAlmostEqual(payment.card_fee_amount, 35.0, places=2)
        self.assertAlmostEqual(payment.net_bank_amount, 965.0, places=2)
        payment.action_create_account_move()
        move = payment.move_id
        fee_lines = move.line_ids.filtered(
            lambda line: line.account_id == self.company.lenka_card_fee_expense_account_id
        )
        self.assertEqual(len(fee_lines), 1)
        self.assertAlmostEqual(fee_lines.debit, 35.0, places=2)
        self.assertAlmostEqual(sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit')), places=2)

    def test_card_fee_account_is_required_for_card_collection(self):
        self._configure_accounting()
        self.company.lenka_card_fee_expense_account_id = False
        self.operation.state = 'active'
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'amount': 1000.0,
            'payment_method': 'card',
            'card_fee_rate': 3.5,
        })
        payment.action_post()
        with self.assertRaises(ValidationError):
            payment.action_create_account_move()
