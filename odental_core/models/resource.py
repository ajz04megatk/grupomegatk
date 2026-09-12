from odoo import fields, models


class ODentalSite(models.Model):
    _name = "odental.site"
    _description = "Sede O Dental"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    organization_id = fields.Many2one("odental.organization", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="organization_id.company_id", store=True, index=True)
    address = fields.Char()


class ODentalResource(models.Model):
    _name = "odental.resource"
    _description = "Recurso reservable O Dental"
    _order = "resource_type, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    resource_type = fields.Selection(
        [
            ("room", "Consultorio"),
            ("chair", "Sillón/unidad dental"),
            ("equipment", "Equipo"),
            ("assistant", "Asistente"),
        ],
        required=True,
        index=True,
    )
    organization_id = fields.Many2one("odental.organization", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="organization_id.company_id", store=True, index=True)
    site_id = fields.Many2one("odental.site", required=True, ondelete="restrict")
    user_id = fields.Many2one("res.users", string="Usuario vinculado")
    notes = fields.Text()

