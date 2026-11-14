from lxml import etree
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestSaleCommercialLock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(cls.env, login='quote_lock_manager', groups=(
            'sales_team.group_sale_manager,base.group_partner_manager,'
            'partner_commercial_lock.group_manage_commercial_assignment'))
        cls.seller = new_test_user(cls.env, login='quote_lock_seller', groups=(
            'sales_team.group_sale_salesman_all_leads,base.group_partner_manager,'
            'partner_commercial_lock.group_no_reassign_partner_commercial'))
        cls.other = new_test_user(cls.env, login='quote_lock_other', groups=(
            'sales_team.group_sale_salesman_all_leads,base.group_partner_manager'))
        cls.technician = new_test_user(cls.env, login='quote_lock_technician', groups=(
            'sales_team.group_sale_salesman_all_leads,base.group_partner_manager,'
            'grupos_accesos.edit_comercial_cotizacion,'
            'partner_commercial_lock.group_no_reassign_partner_commercial'))
        cls.legacy_admin = new_test_user(cls.env, login='quote_lock_generic_sales_admin', groups=(
            'sales_team.group_sale_manager,base.group_partner_manager,'
            'grupos_accesos.edit_comercial_cotizacion'))
        cls.customer = cls.env['res.partner'].create({'name': 'Synthetic protected customer', 'user_id': cls.other.id})
        cls.unassigned = cls.env['res.partner'].create({'name': 'Synthetic unassigned customer', 'user_id': False})
        cls.product = cls.env['product.product'].create({'name': 'Synthetic quote product', 'list_price': 100})

    def _order(self, line_owner=None):
        return self.env['sale.order'].with_user(self.manager).create({
            'partner_id': self.customer.id, 'user_id': self.other.id, 'x_responsable_id': self.other.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_uom_qty': 1,
                                           'price_unit': 100, 'x_user_id': (line_owner or self.other).id})],
        })

    def test_all_unapproved_users_are_locked_even_without_old_deny_group(self):
        order = self._order()
        for user in (self.seller, self.other, self.technician, self.legacy_admin):
            with self.subTest(user=user.login):
                self.assertTrue(order.with_user(user).commercial_assignment_locked)
                with self.assertRaises(AccessError):
                    order.with_user(user).write({'user_id': self.seller.id})
                with self.assertRaises(AccessError):
                    order.order_line.with_user(user).write({'x_user_id': self.seller.id})

    def test_header_alias_and_clearing_are_guarded_before_other_values_write(self):
        order = self._order()
        for payload in ({'user_id': self.seller.id}, {'x_responsable_id': self.seller.id},
                        {'user_id': False, 'x_responsable_id': False}, {'x_responsable_id': False}):
            with self.subTest(payload=payload), self.assertRaises(AccessError):
                order.with_user(self.seller).write(dict(payload, client_order_ref='must not persist'))
        self.assertFalse(order.client_order_ref)
        self.assertEqual(order.user_id, self.other)
        self.assertEqual(order.x_responsable_id, self.other)

    def test_inline_line_commands_and_direct_write_are_both_guarded(self):
        order = self._order()
        with self.assertRaises(AccessError):
            order.with_user(self.seller).write({'order_line': [Command.update(order.order_line.id, {'x_user_id': self.seller.id})]})
        with self.assertRaises(AccessError):
            order.order_line.with_user(self.seller).write({'x_user_id': False})
        self.assertEqual(order.order_line.x_user_id, self.other)

    def test_new_order_and_lines_follow_existing_customer_representative(self):
        order = self.env['sale.order'].with_user(self.seller).create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({'product_id': self.product.id, 'product_uom_qty': 1})],
        })
        self.assertEqual(order.user_id, self.other)
        self.assertEqual(order.x_responsable_id, self.other)
        self.assertEqual(order.order_line.x_user_id, self.other)
        self.assertEqual(self.customer.user_id, self.other)

    def test_new_order_cannot_override_existing_customer_owner(self):
        for field in ('user_id', 'x_responsable_id'):
            with self.subTest(field=field), self.assertRaises(AccessError):
                self.env['sale.order'].with_user(self.seller).create({'partner_id': self.customer.id, field: self.seller.id})

    def test_new_line_cannot_override_header_owner(self):
        order = self._order()
        for value in (self.seller.id, False):
            with self.subTest(value=value), self.assertRaises(AccessError):
                self.env['sale.order.line'].with_user(self.seller).create({
                    'order_id': order.id, 'product_id': self.product.id, 'x_user_id': value,
                })

    def test_copy_preserves_assignment_and_override_is_rejected(self):
        order = self._order()
        copied = order.with_user(self.seller).copy()
        self.assertEqual(copied.user_id, self.other)
        self.assertEqual(copied.x_responsable_id, self.other)
        self.assertEqual(copied.order_line.x_user_id, self.other)
        with self.assertRaises(AccessError):
            order.with_user(self.seller).copy({'user_id': self.seller.id, 'x_responsable_id': self.seller.id})

    def test_same_values_and_normal_product_edits_remain_allowed(self):
        order = self._order()
        order.with_user(self.seller).write({'user_id': self.other.id, 'client_order_ref': 'ordinary edit'})
        order.order_line.with_user(self.seller).write({'x_user_id': self.other.id, 'product_uom_qty': 2})
        self.assertEqual(order.client_order_ref, 'ordinary edit')
        self.assertEqual(order.order_line.product_uom_qty, 2)

    def test_split_assignment_cannot_be_replaced_or_reset_by_product_onchange(self):
        order = self._order(line_owner=self.seller)
        line = order.order_line
        with self.assertRaises(AccessError):
            line.with_user(self.other).unlink()
        virtual = self.env['sale.order.line'].with_user(self.other).new({
            'order_id': order.id, 'product_id': self.product.id, 'x_user_id': self.other.id,
        }, origin=line)
        virtual.product_id_change1()
        self.assertEqual(virtual.x_user_id, self.seller)

    def test_moving_existing_line_cannot_change_related_salesperson(self):
        order = self._order()
        target = self.env['sale.order'].with_user(self.manager).create({
            'partner_id': self.unassigned.id, 'user_id': self.seller.id, 'x_responsable_id': self.seller.id,
        })
        with self.assertRaises(AccessError):
            order.order_line.with_user(self.seller).write({'order_id': target.id})
        with self.assertRaises(AccessError):
            order.order_line.with_user(self.seller).write({'salesman_id': self.seller.id})

    def test_context_and_sudo_cannot_bypass_the_named_user_guard(self):
        order = self._order()
        for context in ({'skip_commercial_lock': True}, {'tracking_disable': True}, {'import_file': True}):
            with self.subTest(context=context), self.assertRaises(AccessError):
                order.order_line.with_user(self.seller).sudo().with_context(**context).write({'x_user_id': self.seller.id})

    def test_approved_managers_can_reassign_header_lines_and_contact(self):
        order = self._order()
        order.write({'x_responsable_id': self.seller.id})
        order.order_line.write({'x_user_id': self.seller.id})
        self.customer.with_user(self.manager).write({'user_id': self.seller.id})
        self.assertEqual(order.user_id, self.seller)
        self.assertEqual(order.order_line.x_user_id, self.seller)
        self.assertEqual(self.customer.user_id, self.seller)

    def test_header_and_line_show_readonly_indicator_for_sellers(self):
        order = self._order()
        self.assertTrue(order.with_user(self.legacy_admin).commercial_assignment_locked)
        self.assertFalse(order.commercial_assignment_locked)
        self.assertTrue(order.order_line.with_user(self.seller).commercial_assignment_locked)
        arch = self.env['sale.order'].with_user(self.seller).get_view(
            view_id=self.env.ref('sale.view_order_form').id, view_type='form')['arch']
        root = etree.fromstring(arch.encode())
        line_nodes = root.xpath("//field[@name='order_line']/list/field[@name='x_user_id']")
        self.assertTrue(line_nodes)
        self.assertTrue(all('commercial_assignment_locked' in node.get('readonly', '') for node in line_nodes))

    def test_invoice_preparation_keeps_line_owner_without_creating_invoice(self):
        order = self._order()
        self.assertEqual(order.order_line.with_user(self.seller)._prepare_invoice_line()['x_user_id'], self.other.id)

    def test_unassigned_customer_new_quote_does_not_claim_customer(self):
        order = self.env['sale.order'].with_user(self.seller).create({'partner_id': self.unassigned.id})
        self.assertEqual(order.user_id, self.seller)
        self.assertFalse(self.unassigned.user_id)

    def test_customer_change_does_not_reassign_existing_quote(self):
        order = self._order()
        virtual = self.env['sale.order'].with_user(self.seller).new({
            'partner_id': self.unassigned.id, 'user_id': self.seller.id, 'x_responsable_id': self.seller.id,
        }, origin=order)
        virtual._onchange_preserve_commercial_assignment()
        self.assertEqual(virtual.user_id, self.other)
        self.assertEqual(virtual.x_responsable_id, self.other)

    def test_explicit_nicaragua_exception_keeps_assignment_permissions(self):
        # No group is added. Test the same immutable UID+login exclusion using
        # a synthetic identity instead of allocating real production user IDs.
        order = self._order()
        before = self.legacy_admin.groups_id.ids
        with patch('odoo.addons.partner_commercial_lock.models.policy.EXEMPT_PRINCIPALS',
                   ((self.legacy_admin.id, self.legacy_admin.login),)):
            order.with_user(self.legacy_admin).write({'x_responsable_id': self.seller.id})
            order.order_line.with_user(self.legacy_admin).write({'x_user_id': self.seller.id})
            self.assertFalse(order.with_user(self.legacy_admin).commercial_assignment_locked)
        self.assertEqual(self.legacy_admin.groups_id.ids, before)
        self.assertEqual(order.user_id, self.seller)
        self.assertEqual(order.order_line.x_user_id, self.seller)
