from odoo.tests.common import TransactionCase


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
        self.assertAlmostEqual(first.payment, 10046.208547, places=4)
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
