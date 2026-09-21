from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LenkaFinancialOperationLifecycle(models.Model):
    _inherit = 'lenka.financial.operation'

    approval_date = fields.Datetime(string='Fecha de aprobacion', readonly=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='Aprobado por', readonly=True, tracking=True)
    approval_notes = fields.Text(string='Condiciones / observaciones de aprobacion')
    contract_date = fields.Date(string='Fecha de contrato')
    contract_signed = fields.Boolean(string='Contrato firmado', tracking=True)
    contract_reference = fields.Char(string='Referencia de contrato')
    document_ids = fields.One2many('lenka.operation.document', 'operation_id', string='Expediente')
    disbursement_ids = fields.One2many('lenka.disbursement', 'operation_id', string='Desembolsos')
    disbursed_amount = fields.Monetary(string='Total desembolsado', compute='_compute_disbursed_amount')
    pending_disbursement = fields.Monetary(string='Pendiente de desembolsar', compute='_compute_disbursed_amount')

    @api.depends('disbursement_ids.state', 'disbursement_ids.amount', 'financed_amount')
    def _compute_disbursed_amount(self):
        for rec in self:
            posted = rec.disbursement_ids.filtered(lambda d: d.state == 'posted')
            rec.disbursed_amount = sum(posted.mapped('amount'))
            rec.pending_disbursement = max(rec.financed_amount - rec.disbursed_amount, 0.0)

    def _validate_for_approval(self):
        self.ensure_one()
        missing = []
        if not self.partner_id:
            missing.append(_('cliente'))
        if self.financed_amount <= 0:
            missing.append(_('monto financiado'))
        if self.interest_rate < 0:
            missing.append(_('tasa'))
        if self.term_months <= 0:
            missing.append(_('plazo'))
        if self.calculation_method != 'custom' and not self.schedule_line_ids:
            missing.append(_('tabla de amortizacion'))
        required_docs = self.document_ids.filtered(lambda d: d.required)
        missing_docs = required_docs.filtered(lambda d: d.state != 'received' or not d.attachment_id)
        if missing_docs:
            missing.append(_('documentos obligatorios'))
        if missing:
            raise ValidationError(_('No se puede aprobar. Falta: %s.') % ', '.join(missing))

    def action_approve(self):
        for rec in self:
            if rec.is_quote:
                raise ValidationError(_('Una cotizacion debe convertirse primero en solicitud.'))
            rec._validate_for_approval()
            rec.write({
                'state': 'approved',
                'approval_date': fields.Datetime.now(),
                'approved_by': self.env.user.id,
            })
        return True

    def action_mark_contracted(self):
        for rec in self:
            if rec.state != 'approved':
                raise ValidationError(_('La operacion debe estar aprobada antes de contratarse.'))
            if not rec.contract_signed:
                raise ValidationError(_('Debe marcar el contrato como firmado.'))
            rec.write({'state': 'contracted', 'contract_date': rec.contract_date or fields.Date.context_today(rec)})
        return True

    def action_activate(self):
        for rec in self:
            if rec.state != 'contracted':
                raise ValidationError(_('La operacion debe estar contratada antes de activarse.'))
            if rec.disbursed_amount <= 0:
                raise ValidationError(_('Debe existir al menos un desembolso aplicado.'))
            if rec.pending_disbursement > 0.01:
                raise ValidationError(_('Aun existe monto pendiente de desembolsar.'))
            rec.state = 'active'
        return True


class LenkaOperationDocument(models.Model):
    _name = 'lenka.operation.document'
    _description = 'Documento Expediente Lenka'
    _order = 'required desc, document_type, id'

    operation_id = fields.Many2one('lenka.financial.operation', required=True, ondelete='cascade')
    document_type = fields.Selection([
        ('application', 'Solicitud de credito'),
        ('id', 'Identidad'),
        ('rtn', 'RTN'),
        ('deed', 'Escritura / constitucion'),
        ('income', 'Constancia de ingresos'),
        ('guarantor', 'Documentacion de aval'),
        ('quote', 'Cotizacion de equipo'),
        ('contract', 'Contrato'),
        ('promissory', 'Pagare'),
        ('guarantee', 'Documento de garantia'),
        ('other', 'Otro'),
    ], string='Tipo de documento', required=True)
    name = fields.Char(string='Descripcion', required=True)
    required = fields.Boolean(string='Obligatorio')
    state = fields.Selection([
        ('pending', 'Pendiente'), ('received', 'Recibido'), ('expired', 'Vencido'), ('rejected', 'Rechazado')
    ], default='pending', required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Archivo')
    expiration_date = fields.Date(string='Vencimiento')
    notes = fields.Char(string='Observaciones')


class LenkaDisbursement(models.Model):
    _name = 'lenka.disbursement'
    _description = 'Desembolso Lenka'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='Nuevo', readonly=True, copy=False)
    operation_id = fields.Many2one('lenka.financial.operation', required=True, ondelete='restrict', tracking=True)
    currency_id = fields.Many2one(related='operation_id.currency_id', store=True)
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    amount = fields.Monetary(required=True, tracking=True)
    destination_type = fields.Selection([
        ('client', 'Cliente'),
        ('supplier', 'Proveedor'),
        ('group_company', 'Empresa del grupo'),
    ], string='Destino', required=True, default='client')
    destination_partner_id = fields.Many2one('res.partner', string='Beneficiario')
    payment_method = fields.Selection([
        ('cash', 'Efectivo'), ('transfer', 'Transferencia'), ('check', 'Cheque'),
        ('credit_card', 'Tarjeta de credito empresarial'), ('other', 'Otro')
    ], string='Medio', required=True, default='transfer')
    reference = fields.Char(string='Referencia')
    funding_line_id = fields.Many2one('lenka.funding.line', string='Fuente de fondeo')
    state = fields.Selection([('draft', 'Borrador'), ('posted', 'Aplicado'), ('cancelled', 'Anulado')], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('lenka.disbursement') or 'Nuevo'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('El desembolso debe ser mayor que cero.'))

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.operation_id.state != 'contracted':
                raise ValidationError(_('La operacion debe estar contratada y con contrato firmado antes de desembolsar.'))
            funding_total = sum(rec.operation_id.funding_line_ids.mapped('amount'))
            if abs(funding_total - rec.operation_id.financed_amount) > 0.01:
                raise ValidationError(_('El fondeo debe cubrir exactamente el monto financiado antes de desembolsar.'))
            already = sum(rec.operation_id.disbursement_ids.filtered(lambda d: d.state == 'posted' and d.id != rec.id).mapped('amount'))
            if already + rec.amount > rec.operation_id.financed_amount + 0.01:
                raise ValidationError(_('El desembolso excede el monto financiado.'))
            if rec.funding_line_id and rec.funding_line_id.operation_id != rec.operation_id:
                raise ValidationError(_('La fuente de fondeo no pertenece a esta operacion.'))
            if rec.funding_line_id:
                used_source = sum(rec.operation_id.disbursement_ids.filtered(
                    lambda d: d.state == 'posted' and d.id != rec.id and d.funding_line_id == rec.funding_line_id
                ).mapped('amount'))
                if used_source + rec.amount > rec.funding_line_id.amount + 0.01:
                    raise ValidationError(_('El desembolso excede el monto disponible en la fuente de fondeo seleccionada.'))
            rec.state = 'posted'
        return True

    def action_cancel(self):
        for rec in self:
            if rec.move_id and rec.move_id.state == 'posted':
                raise ValidationError(_('No se puede anular el desembolso mientras su asiento contable este publicado. Debe revertirse primero en Contabilidad.'))
            if rec.operation_id.state == 'active':
                raise ValidationError(_('No se puede anular un desembolso de una operacion activa sin reestructurar primero la operacion.'))
            rec.state = 'cancelled'
        return True
