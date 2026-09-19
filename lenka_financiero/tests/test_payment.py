from odoo import fields
from odoo.tests.common import TransactionCase


class TestLenkaPayment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Cobros Lenka'})

    def _operation(self, first_payment_date=None):
        operation = self.env['lenka.financial.operation'].create({
            'partner_id': self.partner.id,
            'operation_type': 'loan',
            'principal_amount': 100000.0,
            'interest_rate': 3.0,
            'rate_period': 'monthly',
            'term_months': 12,
            'calculation_method': 'level',
            'first_payment_date': first_payment_date or fields.Date.context_today(self.env.user),
        })
        operation.action_generate_schedule()
        return operation

    def test_payment_priority_late_fee_interest_capital(self):
        operation = self._operation()
        first = operation.schedule_line_ids.sorted('sequence')[0]
        first.late_fee_due = 500.0

        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': first.date,
            'amount': 4000.0,
            'payment_method': 'cash',
        })
        payment.action_post()

        self.assertAlmostEqual(payment.late_fee_amount, 500.0, places=2)
        self.assertAlmostEqual(payment.interest_amount, 3000.0, places=2)
        self.assertAlmostEqual(payment.capital_amount, 500.0, places=2)
        self.assertAlmostEqual(payment.extra_capital_amount, 0.0, places=2)

    def test_card_fee_reduces_amount_applied_to_debt(self):
        operation = self._operation()
        first = operation.schedule_line_ids.sorted('sequence')[0]

        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': first.date,
            'amount': 100.0,
            'payment_method': 'card',
            'card_fee_rate': 3.5,
        })

        self.assertAlmostEqual(payment.card_fee_amount, 3.50, places=2)
        self.assertAlmostEqual(payment.net_bank_amount, 96.50, places=2)

        payment.action_post()
        self.assertAlmostEqual(
            payment.late_fee_amount + payment.interest_amount + payment.capital_amount + payment.unapplied_amount,
            96.50,
            places=2,
        )

    def test_overpayment_after_due_amount_goes_to_extra_capital(self):
        operation = self._operation()
        first = operation.schedule_line_ids.sorted('sequence')[0]
        due = first.capital + first.interest

        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': first.date,
            'amount': due + 5000.0,
            'payment_method': 'transfer',
        })
        payment.action_post()

        self.assertAlmostEqual(payment.interest_amount, first.interest, places=2)
        self.assertAlmostEqual(first.capital_paid, first.capital, places=2)
        self.assertAlmostEqual(payment.extra_capital_amount, 5000.0, places=2)
        self.assertAlmostEqual(payment.unapplied_amount, 0.0, places=2)

    def test_future_interest_is_not_paid_in_advance(self):
        today = fields.Date.context_today(self.env.user)
        operation = self._operation(first_payment_date=fields.Date.add(today, months=1))

        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': today,
            'amount': 10000.0,
            'payment_method': 'transfer',
        })
        payment.action_post()

        self.assertAlmostEqual(payment.interest_amount, 0.0, places=2)
        self.assertAlmostEqual(payment.capital_amount, 10000.0, places=2)
        self.assertAlmostEqual(payment.extra_capital_amount, 10000.0, places=2)

    def test_partial_payment_only_applies_available_amount(self):
        operation = self._operation()
        first = operation.schedule_line_ids.sorted('sequence')[0]

        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': first.date,
            'amount': 1000.0,
            'payment_method': 'cash',
        })
        payment.action_post()

        self.assertAlmostEqual(payment.interest_amount, 1000.0, places=2)
        self.assertAlmostEqual(payment.capital_amount, 0.0, places=2)
        self.assertEqual(first.payment_state, 'partial')


    def test_cancel_posted_payment_restores_schedule_balances(self):
        operation = self._operation()
        first = operation.schedule_line_ids.sorted('sequence')[0]
        original_due = first.amount_due

        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': first.date,
            'amount': 2500.0,
            'payment_method': 'cash',
        })
        payment.action_post()
        self.assertGreater(first.amount_paid, 0.0)

        payment.action_cancel()
        self.assertEqual(payment.state, 'cancelled')
        self.assertAlmostEqual(first.capital_paid, 0.0, places=2)
        self.assertAlmostEqual(first.interest_paid, 0.0, places=2)
        self.assertAlmostEqual(first.late_fee_paid, 0.0, places=2)
        self.assertAlmostEqual(first.amount_due, original_due, places=2)

    def test_payment_without_schedule_is_rejected(self):
        operation = self.env['lenka.financial.operation'].create({
            'partner_id': self.partner.id,
            'operation_type': 'loan',
            'principal_amount': 10000.0,
            'interest_rate': 3.0,
            'rate_period': 'monthly',
            'term_months': 12,
            'calculation_method': 'level',
        })
        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'amount': 1000.0,
            'payment_method': 'cash',
        })
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            payment.action_post()

    def test_payment_above_total_capital_leaves_unapplied_balance(self):
        operation = self._operation()
        first = operation.schedule_line_ids.sorted('sequence')[0]
        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': first.date,
            'amount': 200000.0,
            'payment_method': 'transfer',
        })
        payment.action_post()

        self.assertAlmostEqual(operation.outstanding_capital, 0.0, places=2)
        self.assertGreater(payment.unapplied_amount, 0.0)
        self.assertLessEqual(payment.capital_amount, operation.financed_amount + 0.01)

    def test_card_fee_rate_can_be_configured_globally(self):
        parameter = self.env['ir.config_parameter'].sudo()
        old_value = parameter.get_param('lenka_financiero.card_fee_rate')
        try:
            parameter.set_param('lenka_financiero.card_fee_rate', '4.25')
            operation = self._operation()
            payment = self.env['lenka.payment'].create({
                'operation_id': operation.id,
                'amount': 1000.0,
                'payment_method': 'card',
            })
            self.assertAlmostEqual(payment.card_fee_rate, 4.25, places=2)
            self.assertAlmostEqual(payment.card_fee_amount, 42.50, places=2)
            self.assertAlmostEqual(payment.net_bank_amount, 957.50, places=2)
        finally:
            if old_value is None:
                parameter.set_param('lenka_financiero.card_fee_rate', '3.5')
            else:
                parameter.set_param('lenka_financiero.card_fee_rate', old_value)

    def test_multiple_due_installments_are_paid_oldest_first(self):
        today = fields.Date.context_today(self.env.user)
        operation = self._operation(first_payment_date=fields.Date.add(today, months=-2))
        lines = operation.schedule_line_ids.sorted('sequence')
        first = lines[0]
        second = lines[1]
        first.late_fee_due = 100.0
        second.late_fee_due = 200.0

        amount = first.amount_due + 50.0
        payment = self.env['lenka.payment'].create({
            'operation_id': operation.id,
            'payment_date': today,
            'amount': amount,
            'payment_method': 'cash',
        })
        payment.action_post()

        self.assertAlmostEqual(first.late_fee_paid, 100.0, places=2)
        self.assertAlmostEqual(second.late_fee_paid, 200.0, places=2)
        self.assertAlmostEqual(first.interest_paid, first.interest, places=2)
        self.assertGreaterEqual(first.capital_paid, 0.0)
