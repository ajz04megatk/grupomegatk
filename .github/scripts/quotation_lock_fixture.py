"""Generate CI-only adapters for production assignment fields, outside the repo.

The real fields_megatk/grupos_accesos modules have HR, SAR, stock and ticket
dependencies. This synthetic fixture reproduces only their assignment fields,
alias synchronization, onchange and invoice-value propagation. It is never
installed on production and cannot replace staging compatibility validation.
"""
from pathlib import Path
import sys


def write(root, relative, content):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def main(root):
    write(root, 'fields_megatk/__init__.py', 'from . import models\n')
    write(root, 'fields_megatk/__manifest__.py', repr({
        'name': 'CI ONLY assignment compatibility fixture', 'version': '18.0.1.0.0',
        'depends': ['sale'], 'data': ['view.xml'], 'license': 'LGPL-3',
    }))
    write(root, 'fields_megatk/models.py', '''from odoo import api, fields, models

class SaleOrderFields(models.Model):
    _inherit = 'sale.order'
    x_responsable_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user)

    @api.onchange('x_responsable_id')
    def _onchange_x_responsable_id(self):
        if self.x_responsable_id:
            self.user_id = self.x_responsable_id

    @api.onchange('user_id')
    def _onchange_user_id_sync_responsable(self):
        if self.user_id:
            self.x_responsable_id = self.user_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('x_responsable_id') and not vals.get('user_id'):
                vals['user_id'] = vals['x_responsable_id']
            elif vals.get('user_id') and not vals.get('x_responsable_id'):
                vals['x_responsable_id'] = vals['user_id']
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get('x_responsable_id') and not vals.get('user_id'):
            vals['user_id'] = vals['x_responsable_id']
        elif vals.get('user_id') and not vals.get('x_responsable_id'):
            vals['x_responsable_id'] = vals['user_id']
        return super().write(vals)

class SaleOrderLineFields(models.Model):
    _inherit = 'sale.order.line'
    x_user_id = fields.Many2one('res.users', default=lambda self: self.env.user, string='Responsable')
    obj_padre = fields.Many2one('res.users', related='order_id.user_id', readonly=True)
    x_series = fields.Text()

    @api.onchange('product_id')
    def product_id_change1(self):
        self.x_user_id = self.obj_padre

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        values['x_user_id'] = self.x_user_id.id
        values['x_series'] = self.x_series
        return values
''')
    write(root, 'fields_megatk/view.xml', '''<odoo>
  <record id="sale_order_line_campo_megatk_view_inh" model="ir.ui.view">
    <field name="name">Synthetic production line assignment view</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//field[@name='order_line']/list/field[@name='product_template_id']" position="after">
        <field name="x_user_id"/>
      </xpath>
    </field>
  </record>
</odoo>''')
    write(root, 'grupos_accesos/__init__.py', 'from . import models\n')
    write(root, 'grupos_accesos/__manifest__.py', repr({
        'name': 'CI ONLY access compatibility fixture', 'version': '18.0.1.0.0',
        'depends': ['sale'], 'data': ['groups.xml'], 'license': 'LGPL-3',
    }))
    write(root, 'grupos_accesos/models.py', '''from odoo import fields, models

class DefaultVendor(models.Model):
    _inherit = 'res.partner'
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id)
''')
    write(root, 'grupos_accesos/groups.xml', '''<odoo>
  <record id="edit_comercial_cotizacion" model="res.groups">
    <field name="name">Editar Comercial en Cotizaciones</field>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
  </record>
  <record id="sale_order_edit_responsable" model="ir.ui.view">
    <field name="name">Synthetic production header permission view</field>
    <field name="model">sale.order</field>
    <field name="inherit_id" ref="sale.view_order_form"/>
    <field name="arch" type="xml">
      <xpath expr="//field[@name='user_id']" position="replace">
        <field name="user_id" readonly="1" groups="base.group_user,!grupos_accesos.edit_comercial_cotizacion"/>
        <field name="user_id" readonly="0" groups="grupos_accesos.edit_comercial_cotizacion"/>
      </xpath>
    </field>
  </record>
</odoo>''')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
