from odoo import fields
from odoo.exceptions import AccessError, ValidationError
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
        users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.operator = users.create({
            'name': 'Operador reestructuracion', 'login': 'lenka_restructuring_operator',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('lenka_financiero.group_lenka_user').id])],
        })
        cls.manager = users.create({
            'name': 'Gerente reestructuracion', 'login': 'lenka_restructuring_manager',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('lenka_financiero.group_lenka_manager').id])],
        })

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

    def _request(self, user=None, **values):
        model = self.env['lenka.restructuring']
        if user:
            model = model.with_user(user)
        return model.create(dict({'operation_id': self.operation.id, 'reason': 'Prueba de control de reestructuracion'}, **values))

    def test_operator_cannot_approve_prepare_or_complete_via_direct_call(self):
        request = self._request(user=self.operator)
        request.action_submit()
        with self.assertRaises(AccessError):
            request.action_approve()
        request.with_user(self.manager).action_approve()
        with self.assertRaises(AccessError):
            request.action_prepare_successor()
        request.with_user(self.manager).action_prepare_successor()
        with self.assertRaises(AccessError):
            request.action_complete_restructuring()
        self.assertEqual(self.operation.state, 'active')
        self.assertFalse(request.original_operation_closed)

    def test_state_and_successor_cannot_be_injected(self):
        for values in ({'state': 'approved'}, {'successor_operation_id': self.operation.id}, {'original_operation_closed': True}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self._request(**values)
        request = self._request()
        for values in ({'state': 'approved'}, {'successor_operation_id': self.operation.id}, {'original_operation_closed': True}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                request.write(values)
        self.assertEqual(request.state, 'draft')

    def test_original_snapshot_is_captured_and_cannot_be_overwritten(self):
        request = self._request(original_outstanding_capital=1.0, original_interest_rate=99.0)
        self.assertAlmostEqual(request.original_outstanding_capital, self.operation.outstanding_capital)
        self.assertAlmostEqual(request.original_interest_rate, self.operation.interest_rate)
        for field in ('original_outstanding_capital', 'original_payoff_amount', 'original_interest_rate', 'original_term_months'):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                request.write({field: 1.0})
        other = self.operation.copy({'state': 'active'})
        with self.assertRaises(ValidationError):
            request.operation_id = other

    def test_prepared_request_copy_starts_as_unlinked_draft(self):
        request = self._request()
        request.action_submit()
        request.action_approve()
        request.action_prepare_successor()
        copied = request.copy()
        self.assertEqual(copied.state, 'draft')
        self.assertFalse(copied.successor_operation_id)
        self.assertFalse(copied.original_operation_closed)
        self.assertAlmostEqual(copied.original_outstanding_capital, self.operation.outstanding_capital)

    def test_prepared_request_cannot_be_reopened_deleted_or_detached(self):
        request = self._request()
        request.action_submit()
        request.action_approve()
        request.action_prepare_successor()
        for values in ({'state': 'draft'}, {'successor_operation_id': False}, {'request_date': '2020-01-01'}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                request.write(values)
        with self.assertRaises(ValidationError):
            request.unlink()
        with self.assertRaises(ValidationError):
            request.action_cancel()

    def test_prepare_and_complete_are_safe_to_repeat(self):
        request = self._request(user=self.manager)
        request.action_submit()
        request.action_approve()
        request.action_prepare_successor()
        successor = request.successor_operation_id
        request.action_prepare_successor()
        self.assertEqual(request.successor_operation_id, successor)
        successor.state = 'active'
        request.action_complete_restructuring()
        request.action_complete_restructuring()
        self.assertEqual(self.operation.state, 'done')
        self.assertTrue(request.original_operation_closed)

    def test_inactive_original_blocks_approval_and_successor_creation(self):
        request = self._request()
        request.action_submit()
        self.operation.state = 'done'
        with self.assertRaises(ValidationError):
            request.action_approve()
        self.operation.state = 'active'
        request.action_approve()
        self.operation.state = 'done'
        with self.assertRaises(ValidationError):
            request.action_prepare_successor()
        self.assertFalse(request.successor_operation_id)

    def test_manager_cannot_approve_mixed_company_batch(self):
        own = self._request()
        own.action_submit()
        company = self.env['res.company'].create({'name': 'Empresa ajena reestructuracion'})
        other_operation = self.operation.copy({'company_id': company.id, 'state': 'active'})
        other = self.env['lenka.restructuring'].create({'operation_id': other_operation.id, 'reason': 'Solicitud de otra empresa'})
        other.action_submit()
        with self.assertRaises(AccessError):
            (own | other).with_user(self.manager).with_context(allowed_company_ids=self.env.company.ids).action_approve()
        self.assertEqual(own.state, 'review')
        self.assertEqual(other.state, 'review')
