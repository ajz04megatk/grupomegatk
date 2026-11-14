from odoo import api, fields, models, _
from odoo.exceptions import AccessError

from .context import INTERNAL_APPEND

SCOPE = (8, 9)


class ImmutableAudit(models.AbstractModel):
    _name = 'sentinel.invoice.audit.immutable'
    _description = 'Append-only audit storage'

    @api.model_create_multi
    def create(self, vals_list):
        if not INTERNAL_APPEND.get():
            raise AccessError(_('Solo el registrador interno puede añadir eventos de auditoría.'))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_('El historial de auditoría no se puede modificar.'))

    def unlink(self):
        raise AccessError(_('El historial de auditoría no se puede eliminar.'))


class AuditEvent(models.Model):
    _name = 'sentinel.invoice.audit.event'
    _inherit = 'sentinel.invoice.audit.immutable'
    _description = 'Sentinel invoice audit event'
    _order = 'id asc'
    _rec_name = 'event_uid'

    event_uid = fields.Char(required=True, index=True)
    source_event_uid = fields.Char(required=True, index=True)
    correlation_uid = fields.Char(required=True, index=True)
    company_id = fields.Many2one('res.company', required=True, index=True, ondelete='restrict')
    occurred_at = fields.Datetime(required=True, index=True)
    occurred_at_iso = fields.Char(required=True)
    timezone = fields.Char(required=True, default='UTC')
    actor_res_id = fields.Integer(required=True, index=True)
    actor_name = fields.Char(required=True)
    initiating_uid = fields.Integer()
    execution_kind = fields.Char(required=True)
    origin_evidence = fields.Json()
    elevated_execution = fields.Boolean()
    source_model = fields.Char(required=True, index=True)
    source_res_id = fields.Integer(required=True, index=True)
    operation = fields.Selection([('create', 'Create'), ('write', 'Write'), ('unlink', 'Unlink')], required=True, index=True)
    event_type = fields.Char(required=True, index=True)
    invoice_res_id = fields.Integer(index=True)
    invoice_name = fields.Char()
    invoice_refs = fields.Json()
    payment_refs = fields.Json()
    reconciliation = fields.Json()
    relationship_key = fields.Char(index=True)
    debit_line_res_id = fields.Integer(index=True)
    credit_line_res_id = fields.Integer(index=True)
    applied_amount = fields.Float()
    company_currency_res_id = fields.Integer()
    changes = fields.Json()
    before_snapshot = fields.Json()
    after_snapshot = fields.Json()
    capture_policy = fields.Json()
    _sql_constraints = [
        ('event_uid_unique', 'unique(event_uid)', 'Event UUID must be unique.'),
        ('scope_company', 'CHECK(company_id IN (8,9))', 'Only MEGATK and MEDITEK are audited.'),
    ]


class AuditCoverage(models.Model):
    _name = 'sentinel.invoice.audit.coverage'
    _inherit = 'sentinel.invoice.audit.immutable'
    _description = 'Sentinel audit capture start marker'
    _order = 'id'

    company_id = fields.Many2one('res.company', required=True, index=True, ondelete='restrict')
    capture_started_at = fields.Datetime(required=True)
    capture_started_at_iso = fields.Char(required=True)
    version = fields.Char(required=True)
    policy = fields.Json(required=True)
    _sql_constraints = [
        ('company_unique', 'unique(company_id)', 'One immutable start marker per company.'),
        ('scope_company', 'CHECK(company_id IN (8,9))', 'Only MEGATK and MEDITEK are audited.'),
    ]
