from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class LenkaRestructuring(models.Model):
    _name = 'lenka.restructuring'
    _description = 'Reestructuracion Financiera Lenka'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='Nuevo', readonly=True, copy=False, tracking=True)
    operation_id = fields.Many2one(
        'lenka.financial.operation', string='Operacion original',
        required=True, ondelete='restrict', tracking=True,
    )
    company_id = fields.Many2one(related='operation_id.company_id', store=True)
    currency_id = fields.Many2one(related='operation_id.currency_id', store=True)
    partner_id = fields.Many2one(related='operation_id.partner_id', store=True)
    request_date = fields.Date(default=fields.Date.context_today, required=True)
    reason = fields.Text(string='Motivo', required=True, tracking=True)

    original_outstanding_capital = fields.Monetary(
        string='Capital pendiente original', readonly=True, copy=False,
    )
    original_payoff_amount = fields.Monetary(
        string='Liquidacion original a la fecha', readonly=True, copy=False,
    )
    original_interest_rate = fields.Float(string='Tasa original (%)', readonly=True, copy=False)
    original_rate_period = fields.Selection(
        [('monthly', 'Mensual'), ('annual', 'Anual')],
        string='Periodo tasa original', readonly=True, copy=False,
    )
    original_term_months = fields.Integer(string='Plazo original', readonly=True, copy=False)

    proposed_principal_amount = fields.Monetary(string='Nuevo capital', required=True, tracking=True)
    proposed_interest_rate = fields.Float(string='Nueva tasa (%)', required=True, tracking=True)
    proposed_rate_period = fields.Selection(
        [('monthly', 'Mensual'), ('annual', 'Anual')],
        string='Periodo nueva tasa', required=True, default='monthly',
    )
    proposed_term_months = fields.Integer(string='Nuevo plazo (meses)', required=True, tracking=True)
    proposed_calculation_method = fields.Selection([
        ('level', 'Cuota nivelada'),
        ('balance', 'Interes sobre saldo / capital fijo'),
        ('interest_only', 'Solo intereses + capital al final'),
        ('balloon', 'Cuota bomba / extraordinarios'),
        ('custom', 'Plan personalizado'),
    ], string='Nuevo metodo', required=True, default='level')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('review', 'En revision'),
        ('approved', 'Aprobada'),
        ('prepared', 'Nueva operacion preparada'),
        ('cancelled', 'Cancelada'),
    ], default='draft', tracking=True, copy=False)

    successor_operation_id = fields.Many2one(
        'lenka.financial.operation', string='Nueva operacion',
        readonly=True, copy=False, ondelete='restrict',
    )
    original_operation_closed = fields.Boolean(string='Operacion original cerrada', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            if vals.get('state', 'draft') != 'draft' or vals.get('successor_operation_id') or vals.get('original_operation_closed'):
                raise ValidationError(_('Cree la solicitud en borrador y utilice las acciones de reestructuracion.'))
            vals['state'] = 'draft'
            vals['successor_operation_id'] = False
            vals['original_operation_closed'] = False
            operation = self.env['lenka.financial.operation'].browse(vals.get('operation_id')).exists()
            if not operation:
                raise ValidationError(_('Seleccione una operacion valida.'))
            if operation.state != 'active':
                raise ValidationError(_('Solo se puede reestructurar una operacion activa.'))
            vals.setdefault('name', self.env['ir.sequence'].next_by_code('lenka.restructuring') or 'Nuevo')
            vals['original_outstanding_capital'] = operation.outstanding_capital
            vals['original_payoff_amount'] = operation.get_payoff_amount()
            vals['original_interest_rate'] = operation.interest_rate
            vals['original_rate_period'] = operation.rate_period
            vals['original_term_months'] = operation.term_months
            vals.setdefault('proposed_principal_amount', operation.outstanding_capital)
            vals.setdefault('proposed_interest_rate', operation.interest_rate)
            vals.setdefault('proposed_rate_period', operation.rate_period)
            vals.setdefault('proposed_term_months', operation.term_months)
            vals.setdefault('proposed_calculation_method', operation.calculation_method)
            records |= super().create(vals)
        return records

    def write(self, vals):
        protected = {
            'original_outstanding_capital', 'original_payoff_amount',
            'original_interest_rate', 'original_rate_period', 'original_term_months',
            'successor_operation_id', 'original_operation_closed', 'state',
        }
        if protected.intersection(vals):
            raise ValidationError(_('El historial y el estado solo pueden cambiar mediante las acciones de reestructuracion.'))
        if 'operation_id' in vals and any(rec.operation_id.id != vals['operation_id'] for rec in self):
            raise ValidationError(_('La operacion original no puede sustituirse. Cree otra solicitud.'))
        proposal_fields = {
            'operation_id', 'proposed_principal_amount', 'proposed_interest_rate',
            'proposed_rate_period', 'proposed_term_months',
            'proposed_calculation_method', 'reason', 'request_date',
        }
        if proposal_fields.intersection(vals):
            locked = self.filtered(lambda r: r.state in ('approved', 'prepared', 'cancelled'))
            if locked:
                raise ValidationError(_('Una reestructuracion aprobada no puede modificarse. Cree una nueva solicitud para conservar la auditoria.'))
        return super().write(vals)

    def unlink(self):
        if any(rec.state != 'draft' or rec.successor_operation_id for rec in self):
            raise ValidationError(_('Solo puede eliminar solicitudes en borrador sin una operacion sucesora.'))
        return super().unlink()

    def _check_manager_action(self):
        self.check_access('write')
        if not self.env.su and not self.env.user.has_group('lenka_financiero.group_lenka_manager'):
            raise AccessError(_('Solo un gerente de Lenka puede aprobar o completar una reestructuracion.'))
        self.mapped('operation_id').check_access('write')

    @api.constrains('proposed_principal_amount', 'proposed_interest_rate', 'proposed_term_months')
    def _check_proposal(self):
        for rec in self:
            if rec.proposed_principal_amount <= 0:
                raise ValidationError(_('El nuevo capital debe ser mayor que cero.'))
            if rec.proposed_interest_rate < 0:
                raise ValidationError(_('La nueva tasa no puede ser negativa.'))
            if rec.proposed_term_months <= 0:
                raise ValidationError(_('El nuevo plazo debe ser mayor que cero.'))

    def action_submit(self):
        self.check_access('write')
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.operation_id.state != 'active':
                raise ValidationError(_('La operacion original debe continuar activa.'))
            super(LenkaRestructuring, rec).write({'state': 'review'})
        return True

    def action_approve(self):
        self._check_manager_action()
        for rec in self:
            if rec.state != 'review':
                raise ValidationError(_('La reestructuracion debe estar en revision antes de aprobarse.'))
            if rec.operation_id.state != 'active':
                raise ValidationError(_('La operacion original debe continuar activa.'))
            if rec.operation_id.payment_ids.filtered(lambda p: p.state == 'posted' and p.unapplied_amount > 0.01):
                raise ValidationError(_('Existen cobros con saldo sin aplicar. Regularicelos antes de aprobar la reestructuracion.'))
            super(LenkaRestructuring, rec).write({'state': 'approved'})
        return True

    def action_prepare_successor(self):
        self._check_manager_action()
        for rec in self:
            if rec.state == 'prepared' and rec.successor_operation_id:
                continue
            if rec.state != 'approved':
                raise ValidationError(_('Apruebe la reestructuracion antes de preparar la nueva operacion.'))
            if rec.successor_operation_id:
                continue
            if rec.operation_id.state != 'active':
                raise ValidationError(_('La operacion original debe continuar activa.'))
            successor = self.env['lenka.financial.operation'].create({
                'partner_id': rec.partner_id.id,
                'guarantor_ids': [(6, 0, rec.operation_id.guarantor_ids.ids)],
                'operation_type': rec.operation_id.operation_type,
                'product_id': rec.operation_id.product_id.id,
                'company_id': rec.company_id.id,
                'currency_id': rec.currency_id.id,
                'principal_amount': rec.proposed_principal_amount,
                'down_payment': 0.0,
                'interest_rate': rec.proposed_interest_rate,
                'rate_period': rec.proposed_rate_period,
                'term_months': rec.proposed_term_months,
                'calculation_method': rec.proposed_calculation_method,
                'is_quote': False,
                'state': 'review',
                'notes': _('Preparada desde reestructuracion %s de la operacion %s. La operacion original permanece intacta hasta completar contrato y cierre controlado.') % (rec.name, rec.operation_id.name),
            })
            if successor.calculation_method != 'custom':
                successor.action_generate_schedule()
            super(LenkaRestructuring, rec).write({
                'successor_operation_id': successor.id,
                'state': 'prepared',
            })
        return True

    def action_complete_restructuring(self):
        self._check_manager_action()
        for rec in self:
            if rec.original_operation_closed:
                continue
            if rec.state != 'prepared' or not rec.successor_operation_id:
                raise ValidationError(_('Primero prepare la nueva operacion de la reestructuracion.'))
            successor = rec.successor_operation_id
            if successor.state != 'active':
                raise ValidationError(_('La nueva operacion debe estar contratada, desembolsada y activa antes de cerrar la operacion original.'))
            original = rec.operation_id
            if original.state != 'active':
                raise ValidationError(_('La operacion original debe continuar activa hasta completar la sustitucion.'))
            if original.payment_ids.filtered(lambda p: p.state == 'posted' and p.unapplied_amount > 0.01):
                raise ValidationError(_('Existen cobros sin aplicar en la operacion original. Regularicelos antes de completar la reestructuracion.'))
            original.state = 'done'
            original.guarantee_ids.filtered(lambda g: g.state in ('accepted', 'active')).write({'state': 'release_pending'})
            super(LenkaRestructuring, rec).write({'original_operation_closed': True})
        return True

    def action_cancel(self):
        self.check_access('write')
        for rec in self:
            if rec.state == 'prepared':
                raise ValidationError(_('No se puede cancelar desde aqui una reestructuracion que ya preparo una nueva operacion. Revise primero la operacion sucesora.'))
            super(LenkaRestructuring, rec).write({'state': 'cancelled'})
        return True
