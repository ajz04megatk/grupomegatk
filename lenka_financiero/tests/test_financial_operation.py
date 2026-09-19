from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestLenkaFinancialOperation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Prueba Lenka'})

    def _operation(self, method, rate=3.0, term=12):
        return self.env['lenka.financial.operation'].create({
            'partner_id': self.partner.id,
            'operation_type': 'loan',
            'principal_amount': 100000.0,
            'down_payment': 0.0,
            'interest_rate': rate,
            'rate_period': 'monthly',
            'term_months': term,
            'calculation_method': method,
        })

    def test_level_payment_3_percent_12_months(self):
        operation = self._operation('level')
        operation.action_generate_schedule()
        self.assertEqual(len(operation.schedule_line_ids), 12)
        first = operation.schedule_line_ids.sorted('sequence')[0]
        last = operation.schedule_line_ids.sorted('sequence')[-1]
        self.assertAlmostEqual(first.payment, 10046.21, places=2)
        self.assertAlmostEqual(first.interest, 3000.0, places=2)
        self.assertAlmostEqual(last.closing_balance, 0.0, places=2)
        self.assertAlmostEqual(sum(operation.schedule_line_ids.mapped('capital')), 100000.0, places=2)

    def test_balance_method_has_fixed_capital_and_decreasing_payment(self):
        operation = self._operation('balance')
        operation.action_generate_schedule()
        lines = operation.schedule_line_ids.sorted('sequence')
        self.assertAlmostEqual(lines[0].capital, 100000.0 / 12.0, places=2)
        self.assertAlmostEqual(lines[0].interest, 3000.0, places=2)
        self.assertGreater(lines[0].payment, lines[-1].payment)
        self.assertAlmostEqual(lines[-1].closing_balance, 0.0, places=2)

    def test_interest_only_pays_capital_at_end(self):
        operation = self._operation('interest_only')
        operation.action_generate_schedule()
        lines = operation.schedule_line_ids.sorted('sequence')
        self.assertEqual(len(lines), 12)
        self.assertAlmostEqual(lines[0].capital, 0.0, places=2)
        self.assertAlmostEqual(lines[0].interest, 3000.0, places=2)
        self.assertAlmostEqual(lines[-1].capital, 100000.0, places=2)
        self.assertAlmostEqual(lines[-1].payment, 103000.0, places=2)
        self.assertAlmostEqual(lines[-1].closing_balance, 0.0, places=2)

    def test_annual_rate_converts_to_monthly_nominal_rate(self):
        operation = self._operation('interest_only', rate=18.0, term=1)
        operation.rate_period = 'annual'
        operation.action_generate_schedule()
        line = operation.schedule_line_ids[0]
        self.assertAlmostEqual(line.interest, 1500.0, places=2)

    def test_financing_down_payment_reduces_financed_amount(self):
        operation = self.env['lenka.financial.operation'].create({
            'partner_id': self.partner.id,
            'operation_type': 'financing',
            'principal_amount': 100000.0,
            'down_payment': 20000.0,
            'interest_rate': 3.0,
            'rate_period': 'monthly',
            'term_months': 12,
            'calculation_method': 'level',
        })
        self.assertAlmostEqual(operation.financed_amount, 80000.0, places=2)
        operation.action_generate_schedule()
        self.assertAlmostEqual(sum(operation.schedule_line_ids.mapped('capital')), 80000.0, places=2)

    def test_balloon_extra_payment_reduces_future_interest(self):
        normal = self._operation('level')
        normal.action_generate_schedule()
        normal_lines = normal.schedule_line_ids.sorted('sequence')

        balloon = self._operation('balloon')
        balloon.write({
            'balloon_base_payment': normal_lines[0].payment,
            'extra_payment_line_ids': [(0, 0, {
                'installment_number': 6,
                'amount': 20000.0,
                'note': 'Cuota bomba mes 6',
            })],
        })
        balloon.action_generate_schedule()
        balloon_lines = balloon.schedule_line_ids.sorted('sequence')

        sixth = balloon_lines.filtered(lambda l: l.sequence == 6)
        seventh = balloon_lines.filtered(lambda l: l.sequence == 7)
        self.assertAlmostEqual(sixth.extra_charge, 20000.0, places=2)
        self.assertLess(seventh.interest, normal_lines[6].interest)
        self.assertAlmostEqual(balloon_lines[-1].closing_balance, 0.0, places=2)

    def test_balloon_payment_outside_term_is_rejected(self):
        operation = self._operation('balloon', term=12)
        operation.write({
            'extra_payment_line_ids': [(0, 0, {
                'installment_number': 13,
                'amount': 5000.0,
            })],
        })
        with self.assertRaises(ValidationError):
            operation.action_generate_schedule()
