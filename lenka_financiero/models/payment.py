from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LenkaPayment(models.Model):
    _name = 'lenka.payment'
    _description = 'Cobro Lenka'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'payment_date desc, id desc'

    name = fields.Char(default='Nuevo', readonly=True, copy=False)
    operation_id = fields.Many2one('lenka.financial.operation', string='Operacion', required=True, tracking=True)
    partner_id = fields.Many2one(related='operation_id.partner_id', store=True, string='Cliente')
    currency_id = fields.Many2one(related='operation_id.currency_id', store=True)
    payment_date = fields.Date(string='Fecha de pago', required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='Monto recibido', required=True, tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Efectivo'), ('transfer', 'Transferencia'), ('check', 'Cheque'),
        ('card', 'Tarjeta'), ('other', 'Otro')
    ], string='Forma de pago', required=True, default='transfer')
    reference = fields.Char(string='Referencia')
    state = fields.Selection([('draft', 'Borrador'), ('posted', 'Aplicado'), ('cancelled', 'Anulado')], default='draft', tracking=True)
    late_fee_amount = fields.Monetary(string='Aplicado a mora', readonly=True)
    interest_amount = fields.Monetary(string='Aplicado a interes', readonly=True)
    capital_amount = fields.Monetary(string='Aplicado a capital', readonly=True)
    unapplied_amount = fields.Monetary(string='Saldo sin aplicar', readonly=True)
    allocation_line_ids = fields.One2many('lenka.payment.allocation', 'payment_id', string='Aplicacion', copy=False, readonly=True)
    notes = fields.Text(string='Observaciones')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('lenka.payment') or 'Nuevo'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('El monto recibido debe ser mayor que cero.'))

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if not rec.operation_id.schedule_line_ids:
                raise ValidationError(_('La operacion no tiene tabla de amortizacion.'))
            remaining = rec.amount
            allocations = []
            late_total = interest_total = capital_total = 0.0

            # Regla inicial configurable conceptualmente: mora -> interes -> capital.
            # Se aplica primero a las cuotas mas antiguas pendientes.
            for line in rec.operation_id.schedule_line_ids.sorted(key=lambda l: (l.date, l.sequence)):
                if remaining <= 0:
                    break
                due_late = max(line.late_fee_due - line.late_fee_paid, 0.0)
                due_interest = max(line.interest - line.interest_paid, 0.0)
                due_capital = max(line.capital - line.capital_paid, 0.0)
                if due_late <= 0 and due_interest <= 0 and due_capital <= 0:
                    continue

                pay_late = min(remaining, due_late)
                remaining -= pay_late
                pay_interest = min(remaining, due_interest)
                remaining -= pay_interest
                pay_capital = min(remaining, due_capital)
                remaining -= pay_capital

                line.write({
                    'late_fee_paid': line.late_fee_paid + pay_late,
                    'interest_paid': line.interest_paid + pay_interest,
                    'capital_paid': line.capital_paid + pay_capital,
                })
                late_total += pay_late
                interest_total += pay_interest
                capital_total += pay_capital
                allocations.append((0, 0, {
                    'schedule_line_id': line.id,
                    'late_fee_amount': pay_late,
                    'interest_amount': pay_interest,
                    'capital_amount': pay_capital,
                }))

            rec.write({
                'late_fee_amount': late_total,
                'interest_amount': interest_total,
                'capital_amount': capital_total,
                'unapplied_amount': remaining,
                'allocation_line_ids': allocations,
                'state': 'posted',
            })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state != 'posted':
                rec.state = 'cancelled'
                continue
            for alloc in rec.allocation_line_ids:
                line = alloc.schedule_line_id
                line.write({
                    'late_fee_paid': max(line.late_fee_paid - alloc.late_fee_amount, 0.0),
                    'interest_paid': max(line.interest_paid - alloc.interest_amount, 0.0),
                    'capital_paid': max(line.capital_paid - alloc.capital_amount, 0.0),
                })
            rec.state = 'cancelled'
        return True


class LenkaPaymentAllocation(models.Model):
    _name = 'lenka.payment.allocation'
    _description = 'Aplicacion de Cobro Lenka'

    payment_id = fields.Many2one('lenka.payment', required=True, ondelete='cascade')
    schedule_line_id = fields.Many2one('lenka.amortization.line', required=True, ondelete='restrict')
    currency_id = fields.Many2one(related='payment_id.currency_id')
    late_fee_amount = fields.Monetary(string='Mora')
    interest_amount = fields.Monetary(string='Interes')
    capital_amount = fields.Monetary(string='Capital')
