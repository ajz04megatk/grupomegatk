from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestLenkaMobileService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'Otra empresa móvil'})
        cls.partner = cls.env['res.partner'].create({
            'name': 'Cliente móvil', 'email': 'lenka-mobile-test@example.invalid',
            'company_id': cls.company.id, 'lenka_mobile_enabled': True,
        })
        cls.other_partner = cls.env['res.partner'].create({'name': 'Otro cliente móvil'})
        cls.user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': cls.partner.name, 'login': cls.partner.email, 'partner_id': cls.partner.id,
            'company_id': cls.company.id, 'company_ids': [(6, 0, cls.company.ids)],
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id,
                                  cls.env.ref('lenka_financiero.group_lenka_mobile_client').id])],
        })
        cls.service = cls.env['lenka.mobile.service'].with_user(cls.user)

    def _operation(self, partner=None, company=None, state='approved'):
        return self.env['lenka.financial.operation'].create({
            'partner_id': (partner or self.partner).id,
            'company_id': (company or self.company).id,
            'operation_type': 'loan', 'principal_amount': 70000,
            'interest_rate': 2, 'rate_period': 'monthly', 'term_months': 12,
            'calculation_method': 'level', 'state': state,
        })

    def test_operation_list_and_detail_are_scoped(self):
        own = self._operation()
        foreign = self._operation(partner=self.other_partner)
        cross_company = self._operation(company=self.other_company)
        draft = self._operation(state='draft')
        self.assertEqual([item['id'] for item in self.service.get_my_operations()], own.ids)
        self.assertEqual(self.service.get_my_operation_detail(own.id)['id'], own.id)
        for operation in foreign | cross_company | draft:
            with self.assertRaises(AccessError):
                self.service.get_my_operation_detail(operation.id)

    def test_revoked_client_cannot_consult_any_resource(self):
        self.partner.lenka_mobile_enabled = False
        for method in ('get_my_dashboard', 'get_my_operations', 'get_my_investments', 'get_my_statements'):
            with self.assertRaises(AccessError):
                getattr(self.service, method)()

    def test_ordinary_client_cannot_grant_mobile_access(self):
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user).action_enable_lenka_mobile()

    def test_ordinary_client_cannot_revoke_other_access(self):
        with self.assertRaises(AccessError):
            self.partner.with_user(self.user).action_disable_lenka_mobile()

    def test_missing_mobile_group_denies_access(self):
        group = self.env.ref('lenka_financiero.group_lenka_mobile_client')
        self.user.write({'groups_id': [(3, group.id)]})
        with self.assertRaises(AccessError):
            self.service.get_my_dashboard()

    def test_company_context_cannot_expand_visibility(self):
        own = self._operation()
        self._operation(company=self.other_company)
        # Client-supplied context cannot expand the user's assigned companies.
        service = self.service.with_context(allowed_company_ids=(self.company | self.other_company).ids)
        self.assertEqual([item['id'] for item in service.get_my_operations()], own.ids)
