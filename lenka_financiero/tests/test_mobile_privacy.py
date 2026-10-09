from odoo import fields
from odoo.exceptions import AccessError
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
