from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ODentalAppointment(models.Model):
    _name = "odental.appointment"
    _description = "Cita O Dental"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc"

    name = fields.Char(default="Nuevo", readonly=True, copy=False, index=True)
    active = fields.Boolean(default=True)
    organization_id = fields.Many2one("odental.organization", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="organization_id.company_id", store=True, index=True)
    patient_id = fields.Many2one("odental.patient", required=True, ondelete="restrict", index=True, tracking=True)
    professional_id = fields.Many2one("odental.professional", required=True, ondelete="restrict", index=True, tracking=True)
    service_id = fields.Many2one("odental.service", required=True, ondelete="restrict", tracking=True)
    site_id = fields.Many2one("odental.site", required=True, ondelete="restrict")
    resource_ids = fields.Many2many(
        "odental.resource", "odental_appointment_resource_rel", "appointment_id", "resource_id",
        string="Recursos reservados"
    )
    start_datetime = fields.Datetime(required=True, index=True, tracking=True)
    duration_minutes = fields.Integer(required=True, default=30, tracking=True)
    preparation_minutes = fields.Integer(default=0)
    cleaning_minutes = fields.Integer(default=0)
    end_datetime = fields.Datetime(compute="_compute_datetimes", store=True, index=True)
    blocking_start = fields.Datetime(compute="_compute_datetimes", store=True, index=True)
    blocking_end = fields.Datetime(compute="_compute_datetimes", store=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("scheduled", "Programada"),
            ("confirmed", "Confirmada"),
            ("in_progress", "En atención"),
            ("done", "Finalizada"),
            ("cancelled", "Cancelada"),
            ("no_show", "No asistió"),
        ],
        default="draft", required=True, index=True, tracking=True
    )
    notes = fields.Text()

    @api.depends("start_datetime", "duration_minutes", "preparation_minutes", "cleaning_minutes")
    def _compute_datetimes(self):
        for appointment in self:
            if not appointment.start_datetime:
                appointment.end_datetime = False
                appointment.blocking_start = False
                appointment.blocking_end = False
                continue
            appointment.end_datetime = appointment.start_datetime + timedelta(minutes=appointment.duration_minutes)
            appointment.blocking_start = appointment.start_datetime - timedelta(minutes=appointment.preparation_minutes)
            appointment.blocking_end = appointment.end_datetime + timedelta(minutes=appointment.cleaning_minutes)

    @api.onchange("service_id", "professional_id")
    def _onchange_service_professional(self):
        if self.service_id:
            self.duration_minutes = self.service_id.duration_for(self.professional_id) if self.professional_id else self.service_id.duration_minutes
            self.preparation_minutes = self.service_id.preparation_minutes
            self.cleaning_minutes = self.service_id.cleaning_minutes

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("odental.appointment") or "Nuevo"
            self._apply_service_defaults(vals)
        return super().create(vals_list)

    @api.model
    def _apply_service_defaults(self, vals):
        if not vals.get("service_id"):
            return
        service = self.env["odental.service"].browse(vals["service_id"])
        professional = self.env["odental.professional"].browse(vals.get("professional_id"))
        vals.setdefault("duration_minutes", service.duration_for(professional) if professional else service.duration_minutes)
        vals.setdefault("preparation_minutes", service.preparation_minutes)
        vals.setdefault("cleaning_minutes", service.cleaning_minutes)

    @api.constrains(
        "organization_id", "patient_id", "professional_id", "service_id", "site_id",
        "resource_ids", "start_datetime", "duration_minutes", "preparation_minutes",
        "cleaning_minutes", "state"
    )
    def _check_appointment(self):
        blocking_states = ("scheduled", "confirmed", "in_progress")
        for appointment in self:
            if appointment.duration_minutes <= 0 or appointment.preparation_minutes < 0 or appointment.cleaning_minutes < 0:
                raise ValidationError("Las duraciones de la cita no son válidas.")
            if appointment.patient_id.organization_id != appointment.organization_id:
                raise ValidationError("El paciente no pertenece a la organización de la cita.")
            if appointment.service_id.organization_id != appointment.organization_id:
                raise ValidationError("El servicio no pertenece a la organización de la cita.")
            if appointment.site_id.organization_id != appointment.organization_id:
                raise ValidationError("La sede no pertenece a la organización de la cita.")
            if appointment.professional_id not in appointment.organization_id.mapped("professional_ids"):
                raise ValidationError("El profesional no está autorizado en esta organización.")
            if any(resource.organization_id != appointment.organization_id for resource in appointment.resource_ids):
                raise ValidationError("Todos los recursos deben pertenecer a la organización de la cita.")
            appointment._check_required_resources()
            if appointment.state not in blocking_states or not appointment.blocking_start or not appointment.blocking_end:
                continue
            base_domain = [
                ("id", "!=", appointment.id),
                ("state", "in", blocking_states),
                ("blocking_start", "<", appointment.blocking_end),
                ("blocking_end", ">", appointment.blocking_start),
            ]
            if self.search_count(base_domain + [("professional_id", "=", appointment.professional_id.id)]):
                raise ValidationError("El profesional ya tiene otra cita durante este horario.")
            if appointment.resource_ids and self.search_count(base_domain + [("resource_ids", "in", appointment.resource_ids.ids)]):
                raise ValidationError("Uno o más recursos ya están reservados durante este horario.")

    def _check_required_resources(self):
        self.ensure_one()
        present_types = set(self.resource_ids.mapped("resource_type"))
        requirements = {
            "room": self.service_id.require_room,
            "chair": self.service_id.require_chair,
            "assistant": self.service_id.require_assistant,
            "equipment": self.service_id.require_equipment,
        }
        missing = [resource_type for resource_type, required in requirements.items() if required and resource_type not in present_types]
        if missing:
            labels = dict(self.env["odental.resource"]._fields["resource_type"].selection)
            raise ValidationError("Faltan recursos obligatorios: %s" % ", ".join(labels[item] for item in missing))

    def action_schedule(self):
        self.write({"state": "scheduled"})

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})


class ODentalOrganizationProfessional(models.Model):
    _inherit = "odental.organization"

    professional_ids = fields.Many2many(
        "odental.professional", "odental_professional_organization_rel",
        "organization_id", "professional_id", string="Profesionales"
    )

