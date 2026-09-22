from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLenkaRestructuring(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente Reestructuracion Lenka'})
        cls.guarantor = cls.env['res.partner'].create({'name': 'Aval Reestructuracion Lenka'})
        cls.operation = cls.env['lenka.financial.operation'].create({
            'partner_id': cls.partner.id,
            'guarantor_ids': [(6, 0, [cls.guarantor.id])],
            'operation_type': 'loan',
            'principal_amount': 100000.0,
            'interest_rate': 3.0,
            'rate_period': 'monthly',
            'term_months': 12,
            'calculation_method': 'level',
            'is_quote': False,
            'state': 'review',
        })
        cls.operation.action_generate_schedule()
        cls.operation.state = 'active'

    def test_restructuring_preserves_original_snapshot(self):
        restructuring = self.env['lenka.restructuring'].create({
            'operation_id': self.operation.id,
            'reason': 'Cliente solicita ampliar plazo',
            'proposed_interest_rate': 2.5,
            'proposed_term_months': 18,
        })
        self.assertAlmostEqual(restructuring.original_outstanding_capital, self.operation.outstanding_capital, places=2)
        self.assertAlmostEqual(restructuring.original_interest_rate, 3.0, places=2)
        self.assertEqual(restructuring.original_term_months, 12)

    def test_restructuring_requires_active_operation(self):
        operation = self.env['lenka.financial.operation'].create({
            'partner_id': self.partner.id,
            'operation_type': 'loan',
            'principal_amount': 50000.0,
            'interest_rate': 2.0,
            'rate_period': 'monthly',
            'term_months': 6,
            'calculation_method': 'level',
            'is_quote': False,
            'state': 'review',
        })
        with self.assertRaises(ValidationError):
            self.env['lenka.restructuring'].create({
                'operation_id': operation.id,
                'reason': 'No debe permitirse aun',
                'proposed_principal_amount': 50000.0,
                'proposed_interest_rate': 2.0,
                'proposed_term_months': 6,
            })

    def test_approved_restructuring_prepares_successor_without_mutating_original(self):
        original_rate = self.operation.interest_rate
        original_term = self.operation.term_months
        restructuring = self.env['lenka.restructuring'].create({
            'operation_id': self.operation.id,
            'reason': 'Extender plazo y reducir tasa',
            'proposed_principal_amount': self.operation.outstanding_capital,
            'proposed_interest_rate': 2.5,
            'proposed_rate_period': 'monthly',
            'proposed_term_months': 18,
            'proposed_calculation_method': 'level',
        })
        restructuring.action_submit()
        restructuring.action_approve()
        restructuring.action_prepare_successor()
        self.assertEqual(restructuring.state, 'prepared')
        self.assertTrue(restructuring.successor_operation_id)
        successor = restructuring.successor_operation_id
        self.assertEqual(successor.state, 'review')
        self.assertAlmostEqual(successor.interest_rate, 2.5, places=2)
        self.assertEqual(successor.term_months, 18)
        self.assertEqual(len(successor.schedule_line_ids), 18)
        self.assertAlmostEqual(self.operation.interest_rate, original_rate, places=2)
        self.assertEqual(self.operation.term_months, original_term)
        self.assertEqual(self.operation.state, 'active')

    def test_restructuring_blocked_when_unapplied_collection_exists(self):
        payment = self.env['lenka.payment'].create({
            'operation_id': self.operation.id,
            'payment_date': fields.Date.context_today(self.env.user),
            'amount': 110000.0,
            'payment_method': 'cash',
        })
        payment.action_post()
        self.assertGreater(payment.unapplied_amount, 0.0)
        restructuring = self.env['lenka.restructuring'].create({
            'operation_id': self.operation.id,
            'reason': 'Debe regularizar cobro',
            'proposed_principal_amount': 1000.0,
            'proposed_interest_rate': 2.0,
            'proposed_term_months': 18,
        })
        restructuring.action_submit()
        with self.assertRaises(ValidationError):
            restructuring.action_approve()


    def test_approved_restructuring_terms_are_locked(self):
        restructuring = self.env['lenka.restructuring'].create({
            'operation_id': self.operation.id,
            'reason': 'Propuesta que debe quedar congelada',
            'proposed_principal_amount': self.operation.outstanding_capital,
            'proposed_interest_rate': 2.5,
            'proposed_term_months': 18,
        })
        restructuring.action_submit()
        restructuring.action_approve()
        with self.assertRaises(ValidationError):
            restructuring.write({'proposed_interest_rate': 4.0})
        with self.assertRaises(ValidationError):
            restructuring.write({'proposed_term_months': 24})


    def test_original_cannot_close_until_successor_is_active(self):
        restructuring = self.env['lenka.restructuring'].create({
            'operation_id': self.operation.id,
            'reason': 'Sustitucion pendiente de activar',
            'proposed_principal_amount': self.operation.outstanding_capital,
            'proposed_interest_rate': 2.5,
            'proposed_term_months': 18,
        })
        restructuring.action_submit()
        restructuring.action_approve()
        restructuring.action_prepare_successor()
        self.assertEqual(restructuring.successor_operation_id.state, 'review')
        with self.assertRaises(ValidationError):
            restructuring.action_complete_restructuring()
        self.assertEqual(self.operation.state, 'active')
        self.assertFalse(restructuring.original_operation_closed)

    def test_complete_restructuring_closes_original_only_after_successor_active(self):
        guarantee = self.env['lenka.guarantee'].create({
            'operation_id': self.operation.id,
            'guarantee_type': 'equipment',
            'description': 'Garantia de operacion reestructurada',
            'state': 'active',
        })
        restructuring = self.env['lenka.restructuring'].create({
            'operation_id': self.operation.id,
            'reason': 'Sustitucion completa',
            'proposed_principal_amount': self.operation.outstanding_capital,
            'proposed_interest_rate': 2.5,
            'proposed_term_months': 18,
        })
        restructuring.action_submit()
        restructuring.action_approve()
        restructuring.action_prepare_successor()
        restructuring.successor_operation_id.state = 'active'
        restructuring.action_complete_restructuring()
        self.assertEqual(self.operation.state, 'done')
        self.assertTrue(restructuring.original_operation_closed)
        self.assertEqual(guarantee.state, 'release_pending')
