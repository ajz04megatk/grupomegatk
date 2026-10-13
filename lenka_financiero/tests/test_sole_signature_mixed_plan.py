from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestSoleSignatureMixedPlan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env['res.partner'].create({'name': 'Cliente pruebas sola firma'})
        cls.recipient = cls.env['res.partner'].create({'name': 'Luis Moran - prueba', 'email': 'lenka-test@example.invalid'})
        cls.env.company.lenka_sole_signature_notify_partner_id = cls.recipient
        users = cls.env['res.users'].with_context(no_reset_password=True)
        common = {'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)]}
        cls.operator = users.create(dict(common, name='Operador sola firma', login='lenka_sole_operator', groups_id=[(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('lenka_financiero.group_lenka_user').id])]))
        cls.manager = users.create(dict(common, name='Gerente sola firma', login='lenka_sole_manager', groups_id=[(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('lenka_financiero.group_lenka_manager').id])]))

    def _operation(self, **overrides):
        values = dict(partner_id=self.client.id, operation_type='loan', principal_amount=100000,
                      interest_rate=3, rate_period='monthly', term_months=18,
                      calculation_method='interest_then_level', interest_only_months=6,
                      first_payment_date='2027-01-31', security_mode='sole_signature',
                      approval_notes='Cliente de confianza autorizado por gerencia')
        values.update(overrides)
        return self.env['lenka.financial.operation'].create(values)

    def _application(self):
        op = self._operation()
        op.action_generate_schedule()
        op.action_convert_to_application()
        return op

    def test_six_interest_twelve_level_quote_conversion(self):
        op = self._operation()
        op.action_generate_schedule()
        lines = op.schedule_line_ids.sorted('sequence')
        self.assertEqual(len(lines), 18)
        self.assertEqual(lines[:6].mapped('capital'), [0.0] * 6)
        self.assertEqual(lines[:6].mapped('interest'), [3000.0] * 6)
        self.assertEqual(lines[6].opening_balance, 100000)
        expected = 100000 * .03 / (1 - 1.03 ** -12)
        for line in lines[6:-1]:
            self.assertAlmostEqual(line.payment, expected, delta=.02)
        self.assertAlmostEqual(sum(lines.mapped('capital')), 100000, places=2)
        self.assertEqual(lines[-1].closing_balance, 0)
        self.assertEqual(op.level_payment_months, 12)
        self.assertEqual(op.level_payment_start_date, fields.Date.to_date('2027-07-31'))
        op.action_convert_to_application()
        self.assertEqual(op.interest_only_months, 6)
        self.assertEqual(op.calculation_method, 'interest_then_level')

    def test_zero_rate_mixed_plan(self):
        op = self._operation(interest_rate=0)
        op.action_generate_schedule()
        lines = op.schedule_line_ids.sorted('sequence')
        self.assertEqual(lines[:6].mapped('payment'), [0.0] * 6)
        self.assertAlmostEqual(sum(lines.mapped('capital')), 100000, places=2)
        self.assertEqual(lines[-1].closing_balance, 0)

    def test_invalid_phase_lengths(self):
        for months in (-1, 0, 18, 19):
            with self.subTest(months=months), self.assertRaises(ValidationError), self.cr.savepoint():
                self._operation(interest_only_months=months)

    def test_operator_cannot_approve_via_button_or_direct_write(self):
        op = self._application().with_user(self.operator)
        for action in (op.action_approve, lambda: op.write({'state': 'approved'}), lambda: op.write({'state': 'active'})):
            with self.assertRaises((AccessError, ValidationError)), self.cr.savepoint():
                action()
        self.assertEqual(op.state, 'review')

    def test_manager_approval_audit_and_single_queued_mail(self):
        op = self._application().with_user(self.manager)
        op.action_approve()
        self.assertEqual(op.approved_by, self.manager)
        self.assertTrue(op.approval_date)
        mail = op.sole_signature_notification_id.sudo()
        self.assertEqual(mail.email_to, self.recipient.email)
        self.assertEqual(mail.state, 'outgoing')
        self.assertIn(op.name, mail.subject)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            op.action_approve()
        self.assertEqual(op.sole_signature_notification_id, mail)
        with self.assertRaises(AccessError), self.cr.savepoint():
            op.write({'state': 'approved', 'approved_by': self.operator.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            op.write({'interest_only_months': 3})

    def test_missing_recipient_and_reason_block_approval(self):
        op = self._application()
        self.env.company.lenka_sole_signature_notify_partner_id = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            op.with_user(self.manager).action_approve()
        self.env.company.lenka_sole_signature_notify_partner_id = self.recipient
        op.approval_notes = ''
        with self.assertRaises(ValidationError), self.cr.savepoint():
            op.with_user(self.manager).action_approve()
        self.assertEqual(op.state, 'review')

    def test_backed_operation_still_requires_backing(self):
        op = self._application()
        op.security_mode = 'backed'
        with self.assertRaises(ValidationError), self.cr.savepoint():
            op.with_user(self.manager).action_approve()

    def test_backing_cannot_be_removed_after_approval(self):
        op = self._application()
        op.security_mode = 'backed'
        guarantee = self.env['lenka.guarantee'].create({'operation_id': op.id, 'guarantee_type': 'labor', 'description': 'Garantia pruebas'})
        op.with_user(self.manager).action_approve()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            guarantee.unlink()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            op.security_mode = 'sole_signature'

    def test_import_cannot_create_approved_sole_signature(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._operation(state='approved', is_quote=False)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['lenka.financial.operation'].with_context(default_security_mode='sole_signature').create({
                'partner_id': self.client.id, 'principal_amount': 1000,
                'interest_rate': 3, 'term_months': 12, 'state': 'approved', 'is_quote': False,
            })
