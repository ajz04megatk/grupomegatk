from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestMobilePrivacy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = cls.env['res.partner'].create({
            'name': 'Mobile client A', 'lenka_mobile_enabled': True,
        })
        cls.other = cls.env['res.partner'].create({'name': 'Mobile client B'})
        cls.user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Mobile client A', 'login': 'mobile-privacy-test@example.invalid',
            'partner_id': cls.client.id,
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id,
                cls.env.ref('lenka_financiero.group_lenka_mobile_client').id])],
        })

    def investment(self, partner, state='active'):
        return self.env['lenka.investment'].create({
            'partner_id': partner.id, 'investment_type': 'current',
            'principal_amount': 1000, 'passive_rate': 0,
            'start_date': fields.Date.today(), 'state': state,
        })

    def test_client_cannot_read_another_clients_deposit(self):
        own = self.investment(self.client)
        other = self.investment(self.other)
        service = self.env['lenka.mobile.service'].with_user(self.user)
        self.assertEqual([row['id'] for row in service.get_my_investments()], [own.id])
        with self.assertRaises(AccessError):
            service.get_my_investment_detail(other.id)

    def test_disabled_client_cannot_read_previous_deposit(self):
        own = self.investment(self.client)
        self.client.lenka_mobile_enabled = False
        with self.assertRaises(AccessError):
            self.env['lenka.mobile.service'].with_user(self.user).get_my_investment_detail(own.id)

    def test_draft_and_cancelled_deposits_are_not_accessible_by_id(self):
        service = self.env['lenka.mobile.service'].with_user(self.user)
        for state in ('draft', 'cancelled'):
            record = self.investment(self.client, state)
            with self.assertRaises(AccessError):
                service.get_my_investment_detail(record.id)

    def test_child_contact_does_not_inherit_parent_deposits(self):
        child = self.env['res.partner'].create({'name': 'Contact child', 'parent_id': self.client.id})
        record = self.investment(child)
        with self.assertRaises(AccessError):
            self.env['lenka.mobile.service'].with_user(self.user).get_my_investment_detail(record.id)

    def test_deposit_in_unauthorized_company_is_hidden(self):
        company = self.env['res.company'].create({'name': 'Private other company'})
        record = self.investment(self.client)
        record.company_id = company
        with self.assertRaises(AccessError):
            self.env['lenka.mobile.service'].with_user(self.user).get_my_investment_detail(record.id)

    def test_client_cannot_enable_own_mobile_access(self):
        partner = self.client.with_user(self.user)
        with self.assertRaises(AccessError):
            partner.action_enable_lenka_mobile()
        with self.assertRaises(AccessError):
            partner.write({'lenka_mobile_enabled': True})

    def test_unpublished_operations_are_hidden_even_by_id(self):
        service = self.env['lenka.mobile.service'].with_user(self.user)
        for state in ('draft', 'review', 'rejected', 'cancelled'):
            operation = self.env['lenka.financial.operation'].create({
                'partner_id': self.client.id, 'is_quote': False,
                'principal_amount': 1000, 'interest_rate': 0,
                'term_months': 12, 'state': state,
            })
            with self.assertRaises(AccessError):
                service.get_my_operation_detail(operation.id)
            self.assertNotIn(operation.id, [row['id'] for row in service.get_my_operations()])

    def test_quotes_are_hidden_even_when_approved(self):
        operation = self.env['lenka.financial.operation'].create({
            'partner_id': self.client.id, 'is_quote': True,
            'principal_amount': 1000, 'interest_rate': 0,
            'term_months': 12, 'state': 'approved',
        })
        with self.assertRaises(AccessError):
            self.env['lenka.mobile.service'].with_user(self.user).get_my_operation_detail(operation.id)

    def test_mobile_client_has_no_direct_financial_write_access(self):
        record = self.investment(self.client)
        with self.assertRaises(AccessError):
            record.with_user(self.user).write({'principal_amount': 2000})
        with self.assertRaises(AccessError):
            self.env['lenka.investment'].with_user(self.user).create({
                'partner_id': self.client.id, 'principal_amount': 1000,
                'passive_rate': 0, 'investment_type': 'current',
            })

    def test_new_mobile_user_is_limited_to_selected_company(self):
        company = self.env['res.company'].create({'name': 'Mobile onboarding company'})
        partner = self.env['res.partner'].create({
            'name': 'Fictional new client', 'email': 'new-mobile@example.invalid',
        })
        partner.sudo().with_company(company).action_enable_lenka_mobile()
        user = self.env['res.users'].sudo().search([('partner_id', '=', partner.id)])
        self.assertEqual(user.company_id, company)
        self.assertEqual(user.company_ids, company)
        self.assertTrue(user.has_group('base.group_portal'))
        self.assertFalse(user.has_group('lenka_financiero.group_lenka_user'))

    def test_enabling_existing_user_does_not_add_company(self):
        self.client.email = 'mobile-privacy-test@example.invalid'
        company = self.env['res.company'].create({'name': 'Not authorized for client'})
        before = self.user.company_ids
        with self.assertRaises(ValidationError):
            self.client.sudo().with_company(company).action_enable_lenka_mobile()
        self.assertEqual(self.user.company_ids, before)

    def test_archived_user_is_not_silently_replaced(self):
        self.client.email = 'mobile-privacy-test@example.invalid'
        self.user.active = False
        with self.assertRaises(ValidationError):
            self.client.sudo().action_enable_lenka_mobile()

    def test_login_owned_by_another_contact_is_not_reused(self):
        self.other.email = self.user.login
        with self.assertRaises(ValidationError):
            self.other.sudo().action_enable_lenka_mobile()
