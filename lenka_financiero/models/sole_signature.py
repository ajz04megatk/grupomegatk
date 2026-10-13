from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


LOCKED_STATES = ('approved', 'contracted', 'active', 'done')


class LenkaCompany(models.Model):
    _inherit = 'res.company'

    lenka_sole_signature_notify_partner_id = fields.Many2one(
        'res.partner', string='Luis Moran - avisos de prestamos a sola firma',
        groups='lenka_financiero.group_lenka_manager',
        help='Seleccione el contacto verificado de Luis Moran con correo electronico. La aprobacion requiere este destinatario.',
    )


class LenkaSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lenka_sole_signature_notify_partner_id = fields.Many2one(
        related='company_id.lenka_sole_signature_notify_partner_id', readonly=False,
        groups='lenka_financiero.group_lenka_manager',
    )


class LenkaSoleSignature(models.Model):
    _inherit = 'lenka.financial.operation'

    security_mode = fields.Selection([
        ('backed', 'Con aval o garantia'),
        ('sole_signature', 'A sola firma - sin aval ni garantia'),
    ], required=True, default='backed', string='Modalidad de respaldo', tracking=True)
    sole_signature_notification_id = fields.Many2one(
        'mail.mail', string='Aviso a Luis Moran', readonly=True, copy=False,
        groups='lenka_financiero.group_lenka_manager', ondelete='set null',
    )
    sole_signature_notification_state = fields.Selection(
        related='sole_signature_notification_id.state', string='Estado del aviso',
        groups='lenka_financiero.group_lenka_manager', readonly=True,
    )

    def _require_lenka_manager(self):
        if not self.env.su and not self.env.user.has_group('lenka_financiero.group_lenka_manager'):
            raise AccessError(_('Solo la gerencia de Financiero Lenka puede aprobar prestamos.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('security_mode') == 'sole_signature' and vals.get('state', 'draft') not in ('draft', 'review'):
                raise ValidationError(_('Cree la solicitud a sola firma en borrador o revision y utilice Aprobar.'))
            if vals.get('sole_signature_notification_id'):
                raise AccessError(_('El aviso de aprobacion se registra automaticamente.'))
        return super().create(vals_list)

    @api.constrains('security_mode', 'guarantor_ids', 'guarantee_ids')
    def _check_sole_signature_backing(self):
        for rec in self:
            if rec.security_mode == 'sole_signature' and (rec.guarantor_ids or rec.guarantee_ids):
                raise ValidationError(_('Una operacion a sola firma no debe incluir avales ni garantias.'))

    def _validate_for_approval(self):
        self.ensure_one()
        if self.security_mode != 'sole_signature':
            return super()._validate_for_approval()
        self._require_lenka_manager()
        self._check_sole_signature_backing()
        if not (self.approval_notes or '').strip():
            raise ValidationError(_('Registre el motivo de la autorizacion a sola firma en las observaciones de aprobacion.'))
        partner = self.company_id.sudo().lenka_sole_signature_notify_partner_id
        if not partner or not partner.email:
            raise ValidationError(_('Configure el contacto y correo de Luis Moran para los avisos a sola firma en Ajustes de Financiero Lenka.'))
        # Los requisitos financieros y documentales siguen vigentes.
        if not self.partner_id or self.financed_amount <= 0 or self.term_months <= 0 or self.interest_rate < 0:
            raise ValidationError(_('Revise cliente, monto financiado, tasa y plazo antes de aprobar.'))
        if not self.schedule_line_ids:
            raise ValidationError(_('Calcule la tabla de amortizacion antes de aprobar.'))
        if self.document_ids.filtered(lambda d: d.required and (d.state != 'received' or not d.attachment_id)):
            raise ValidationError(_('Faltan documentos obligatorios para aprobar.'))

    def action_approve(self):
        self.check_access('write')
        self._require_lenka_manager()
        for rec in self:
            if rec.state != 'review':
                raise ValidationError(_('Solo una solicitud en revision puede aprobarse.'))
        return super().action_approve()

    def write(self, vals):
        if 'state' in vals and self.filtered(lambda r: (r.state in LOCKED_STATES or r.approval_date) and vals['state'] in ('draft', 'review')):
            raise ValidationError(_('Una operacion aprobada no puede volver a borrador o revision. Use una reestructuracion para conservar el historial.'))
        if 'sole_signature_notification_id' in vals:
            raise AccessError(_('El aviso de aprobacion se registra automaticamente.'))
        sole = self.filtered(lambda r: r.security_mode == 'sole_signature' or vals.get('security_mode') == 'sole_signature')
        if {'security_mode', 'guarantor_ids', 'guarantee_ids', 'approval_notes'}.intersection(vals):
            if self.filtered(lambda r: r.state in LOCKED_STATES or r.approval_date):
                raise ValidationError(_('No puede cambiar el respaldo ni la autorizacion de una operacion aprobada.'))
        if {'approved_by', 'approval_date'}.intersection(vals) and vals.get('state') != 'approved':
            raise AccessError(_('La autorizacion a sola firma se registra al aprobar.'))
        approving = sole.filtered(lambda r: vals.get('state') == 'approved' and r.state != 'approved')
        if sole and {'approved_by', 'approval_date'}.intersection(vals) and len(approving) != len(sole):
            raise AccessError(_('No puede alterar una autorizacion a sola firma registrada.'))
        if approving:
            self.check_access('write')
            self._require_lenka_manager()
            if 'security_mode' in vals and any(r.security_mode != vals['security_mode'] for r in approving):
                raise ValidationError(_('Guarde primero la modalidad de respaldo y luego apruebe la solicitud.'))
            for rec in approving:
                if rec.state != 'review' or rec.is_quote:
                    raise ValidationError(_('Solo puede aprobar una solicitud a sola firma en revision.'))
                rec._validate_for_approval()
            vals = dict(vals, approved_by=self.env.user.id, approval_date=fields.Datetime.now())
        if vals.get('state') in ('contracted', 'active', 'done'):
            if sole.filtered(lambda r: r.state not in LOCKED_STATES or not r.approved_by or not r.sole_signature_notification_id):
                raise ValidationError(_('La operacion a sola firma requiere aprobacion gerencial y aviso antes de continuar.'))
        result = super().write(vals)
        for rec in approving:
            rec._queue_sole_signature_notification()
        return result

    def _queue_sole_signature_notification(self):
        self.ensure_one()
        recipient = self.company_id.sudo().lenka_sole_signature_notify_partner_id
        body = Markup('<p>Se aprobo un prestamo a sola firma, sin aval ni garantia.</p><ul>')
        for label, value in [
            ('Operacion', self.name), ('Empresa', self.company_id.display_name),
            ('Cliente', self.partner_id.display_name),
            ('Monto financiado', '%s %.2f' % (self.currency_id.name, self.financed_amount)),
            ('Tasa', '%s%% %s' % (self.interest_rate, self.rate_period)),
            ('Plazo total', '%s meses' % self.term_months),
            ('Aprobado por', self.env.user.display_name),
            ('Fecha', self.approval_date), ('Motivo', self.approval_notes),
        ]:
            body += Markup('<li><strong>%s:</strong> %s</li>') % (escape(label), escape(value))
        body += Markup('</ul>')
        mail = self.env['mail.mail'].sudo().create({
            'subject': _('Lenka: prestamo a sola firma aprobado - %s') % self.name,
            'body_html': body, 'email_to': recipient.email,
            'email_from': self.company_id.email or self.env.user.email_formatted,
            'model': self._name, 'res_id': self.id, 'auto_delete': False,
        })
        # Escritura interna; el campo de auditoria no admite valores del cliente.
        super(LenkaSoleSignature, self).write({'sole_signature_notification_id': mail.id})
        self.message_post(body=_('Aviso de aprobacion a sola firma en cola para Luis Moran (%s).') % recipient.email)


class LenkaGuaranteeProtection(models.Model):
    _inherit = 'lenka.guarantee'

    @api.model_create_multi
    def create(self, vals_list):
        operations = self.env['lenka.financial.operation'].browse([v['operation_id'] for v in vals_list if v.get('operation_id')])
        if operations.filtered(lambda r: r.state in LOCKED_STATES or r.security_mode == 'sole_signature'):
            raise ValidationError(_('No puede agregar garantias a operaciones aprobadas o a sola firma.'))
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) - {'state'} and self.mapped('operation_id').filtered(lambda r: r.state in LOCKED_STATES):
            raise ValidationError(_('No puede modificar la garantia de una operacion aprobada.'))
        if vals.get('operation_id'):
            operation = self.env['lenka.financial.operation'].browse(vals['operation_id'])
            if operation.state in LOCKED_STATES or operation.security_mode == 'sole_signature':
                raise ValidationError(_('No puede trasladar garantias a operaciones aprobadas o a sola firma.'))
        return super().write(vals)

    def unlink(self):
        if self.mapped('operation_id').filtered(lambda r: r.state in LOCKED_STATES):
            raise ValidationError(_('No puede eliminar la garantia de una operacion aprobada.'))
        return super().unlink()
