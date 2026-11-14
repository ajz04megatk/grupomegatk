from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .policy import assignment_locked


def denied():
    raise AccessError(_(
        'No tiene permiso para cambiar o quitar el representante de la cotización '
        'o sus líneas. Solicite el cambio a Gerencia de Ventas, Facturación o Administración.'
    ))


def normalized_header(vals):
    """Mirror the real fields_megatk alias synchronization before checking it."""
    result = dict(vals)
    if result.get('x_responsable_id') and not result.get('user_id'):
        result['user_id'] = result['x_responsable_id']
    elif result.get('user_id') and not result.get('x_responsable_id'):
        result['x_responsable_id'] = result['user_id']
    return result


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    commercial_assignment_locked = fields.Boolean(
        compute='_compute_commercial_assignment_locked', compute_sudo=False,
    )

    @api.depends_context('uid')
    def _compute_commercial_assignment_locked(self):
        locked = assignment_locked(self.env)
        for order in self:
            order.commercial_assignment_locked = locked

    @api.model
    def _initial_representative(self, vals):
        partner_id = vals.get('partner_id') or self.env.context.get('default_partner_id')
        partner = self.env['res.partner'].browse(partner_id).exists() if partner_id else self.env['res.partner']
        return partner.commercial_partner_id.user_id.id or self.env.uid

    @api.onchange('partner_id')
    def _onchange_preserve_commercial_assignment(self):
        if assignment_locked(self.env):
            for order in self:
                owner = order._origin.user_id.id if order._origin.id else order._initial_representative({'partner_id': order.partner_id.id})
                order.user_id = owner
                order.x_responsable_id = owner

    @api.model_create_multi
    def create(self, vals_list):
        if not assignment_locked(self.env):
            return super().create(vals_list)
        prepared, owners = [], []
        for values in vals_list:
            values = normalized_header(values)
            owner = self._initial_representative(values)
            for key in ('user_id', 'x_responsable_id'):
                if key in values and (values[key] or False) != owner:
                    denied()
                values[key] = owner
            prepared.append(values)
            owners.append(owner)
        orders = super().create(prepared)
        for order, owner in zip(orders, owners):
            if order.user_id.id != owner or order.x_responsable_id.id != owner:
                denied()
        return orders

    def write(self, vals):
        if assignment_locked(self.env):
            effective = normalized_header(vals)
            for key in ('user_id', 'x_responsable_id'):
                if key in effective and any(order[key].id != (effective[key] or False) for order in self):
                    denied()
        return super().write(vals)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    commercial_assignment_locked = fields.Boolean(
        compute='_compute_commercial_assignment_locked', compute_sudo=False,
    )

    @api.depends_context('uid')
    def _compute_commercial_assignment_locked(self):
        locked = assignment_locked(self.env)
        for line in self:
            line.commercial_assignment_locked = locked

    @api.model_create_multi
    def create(self, vals_list):
        if not assignment_locked(self.env):
            return super().create(vals_list)
        prepared, owners = [], []
        for values in vals_list:
            values = dict(values)
            order_id = values.get('order_id') or self.env.context.get('default_order_id')
            order = self.env['sale.order'].browse(order_id).exists() if order_id else self.env['sale.order']
            owner = order.user_id.id or False
            if not order:
                denied()
            for key in ('x_user_id', 'salesman_id', 'obj_padre'):
                if key in values and (values[key] or False) != owner:
                    denied()
            values['x_user_id'] = owner
            prepared.append(values)
            owners.append(owner)
        lines = super().create(prepared)
        for line, owner in zip(lines, owners):
            if line.x_user_id.id != owner:
                denied()
        return lines

    def write(self, vals):
        if assignment_locked(self.env):
            for key in ('x_user_id', 'salesman_id', 'obj_padre'):
                if key in vals and any(line[key].id != (vals[key] or False) for line in self):
                    denied()
            if 'order_id' in vals and any(line.order_id.id != (vals['order_id'] or False) for line in self):
                denied()
        return super().write(vals)

    def unlink(self):
        # Replacing a manager-assigned split line must not silently reattribute it.
        if assignment_locked(self.env) and any(line.x_user_id != line.order_id.user_id for line in self):
            denied()
        return super().unlink()

    @api.onchange('product_id')
    def product_id_change1(self):
        result = super().product_id_change1()
        if assignment_locked(self.env):
            for line in self:
                line.x_user_id = line._origin.x_user_id if line._origin.id else line.order_id.user_id
        return result
