"""Private Todoist availability. Task titles and descriptions never enter Odoo."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


TODOIST_API = "https://api.todoist.com/api/v1"


class ODentalTodoistConnection(models.Model):
    _name = "odental.todoist.connection"
    _description = "Conexión privada de disponibilidad Todoist"
    _rec_name = "professional_id"

    professional_id = fields.Many2one("odental.professional", required=True, ondelete="cascade", index=True)
    organization_id = fields.Many2one("odental.organization", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="organization_id.company_id", store=True, index=True)
    # The user enters this through the short-lived wizard. Only the superuser
    # running the sync can read the stored credential, never clinical staff.
    api_token = fields.Char(copy=False, groups="base.group_system")
    todoist_user_id = fields.Char(copy=False)
    label_name = fields.Char(string="Etiqueta que bloquea", default="reunión", required=True)
    default_duration_minutes = fields.Integer(
        string="Duración si Todoist no indica una", default=60, required=True,
    )
    source_timezone = fields.Char(string="Zona horaria", default="America/Tegucigalpa", required=True)
    active = fields.Boolean(default=True)
    last_synced_at = fields.Datetime(string="Última actualización", readonly=True)
    last_error = fields.Char(string="Estado de sincronización", readonly=True)

    _sql_constraints = [
        ("professional_organization_unique", "unique(professional_id, organization_id)",
         "Ya existe una conexión Todoist para este profesional y organización."),
    ]

    @api.constrains("professional_id", "organization_id", "source_timezone", "default_duration_minutes")
    def _check_scope(self):
        for connection in self:
            if connection.organization_id not in connection.professional_id.organization_ids:
                raise ValidationError("El profesional debe pertenecer a la organización.")
            if connection.professional_id.company_id != connection.organization_id.company_id:
                raise ValidationError("La conexión debe permanecer dentro de la compañía del profesional.")
            if not 0 < connection.default_duration_minutes <= 1440:
                raise ValidationError("La duración predeterminada debe estar entre 1 y 1440 minutos.")
            try:
                ZoneInfo(connection.source_timezone)
            except ZoneInfoNotFoundError as exc:
                raise ValidationError("Indique una zona horaria válida.") from exc

    def _check_owner(self):
        for connection in self:
            if connection.professional_id.user_id != self.env.user:
                raise AccessError("Solo el profesional puede administrar su propia conexión Todoist.")
            if connection.company_id not in self.env.companies:
                raise AccessError("Cambie a la compañía autorizada del profesional.")

    @api.model
    def _get_json(self, token, endpoint, params=None):
        try:
            response = requests.get(
                f"{TODOIST_API}/{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                params=params, timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            # Never include server response bodies, task content, or token.
            raise UserError("No se pudo consultar Todoist. Revise la conexión o autorización.") from exc

    @api.model
    def _fetch_user_id(self, token):
        data = self._get_json(token, "user")
        if not isinstance(data, dict) or not data.get("id"):
            raise UserError("Todoist no devolvió la identidad de la cuenta.")
        return str(data["id"])

    @api.model
    def _fetch_tasks(self, token):
        tasks = []
        cursor = None
        seen_cursors = set()
        for _page in range(100):
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            data = self._get_json(token, "tasks", params=params)
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise UserError("Todoist devolvió una lista de tareas incompleta.")
            tasks.extend(data["results"])
            cursor = data.get("next_cursor")
            if not cursor:
                return tasks
            if cursor in seen_cursors:
                break
            seen_cursors.add(cursor)
        raise UserError("La consulta de Todoist quedó incompleta; no se liberó ningún bloqueo.")

    def _task_interval(self, task):
        self.ensure_one()
        if not isinstance(task, dict) or task.get("checked") or task.get("is_deleted"):
            return None
        labels = {str(label).lstrip("@").casefold() for label in (task.get("labels") or [])}
        if self.label_name.strip().lstrip("@").casefold() not in labels:
            return None
        responsible = task.get("responsible_uid")
        if responsible and str(responsible) != self.todoist_user_id:
            return None
        due = task.get("due") or {}
        if not isinstance(due, dict):
            return None
        date_value = due.get("datetime") or due.get("date") or ""
        duration = task.get("duration") or {}
        if not isinstance(date_value, str) or not isinstance(duration, dict):
            return None
        if "T" not in date_value:
            return None  # All-day tasks do not block.
        minutes = self.default_duration_minutes
        if duration:
            if duration.get("unit") != "minute":
                return None
            minutes = duration.get("amount")
        if not isinstance(minutes, int) or not 0 < minutes <= 1440:
            return None
        try:
            start = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=ZoneInfo(due.get("timezone") or self.source_timezone))
        except (ValueError, TypeError, ZoneInfoNotFoundError):
            return None
        start_utc = start.astimezone(timezone.utc).replace(tzinfo=None)
        return start_utc, minutes

    def _has_clinical_conflict(self, start, end):
        self.ensure_one()
        return bool(self.env["odental.appointment"].sudo().search_count([
            ("entry_type", "=", "clinical"),
            ("professional_id", "=", self.professional_id.id),
            ("state", "in", ("scheduled", "confirmed", "in_progress")),
            ("blocking_start", "<", end),
            ("blocking_end", ">", start),
        ]))

    def _reconcile_tasks(self, tasks):
        self.ensure_one()
        if not self.env.is_superuser():
            raise AccessError("La sincronización requiere el proceso autorizado de O Dental.")
        appointments = self.env["odental.appointment"].sudo().with_company(self.company_id)
        domain = [
            ("entry_type", "=", "busy"),
            ("organization_id", "=", self.organization_id.id),
            ("professional_id", "=", self.professional_id.id),
            ("external_source", "=", "todoist"),
        ]
        existing = {item.external_uid: item for item in appointments.search(domain)}
        seen = set()
        for task in tasks:
            interval = self._task_interval(task)
            task_id = str(task.get("id") or "") if isinstance(task, dict) else ""
            if not interval or not task_id or task_id.startswith("tmp-"):
                continue
            start, minutes = interval
            seen.add(task_id)
            values = {
                "start_datetime": start,
                "duration_minutes": minutes,
                "external_conflict": self._has_clinical_conflict(start, start + timedelta(minutes=minutes)),
                "state": "scheduled",
            }
            current = existing.get(task_id)
            if current:
                changed = {key: value for key, value in values.items() if current[key] != value}
                if changed:
                    current.write(changed)
            else:
                appointments.create({
                    **values, "entry_type": "busy",
                    "organization_id": self.organization_id.id,
                    "professional_id": self.professional_id.id,
                    "external_source": "todoist", "external_uid": task_id,
                })
        for task_id, current in existing.items():
            if task_id not in seen and current.state != "cancelled":
                current.write({"state": "cancelled", "external_conflict": False})

    def _sync_one(self):
        self.ensure_one()
        if not self.env.is_superuser():
            raise AccessError("La sincronización requiere el proceso autorizado de O Dental.")
        if not self.active or not self.api_token:
            return
        tasks = self._fetch_tasks(self.api_token)
        # Reconcile only after every page succeeded: a partial response must
        # never cancel legitimate blocks.
        self._reconcile_tasks(tasks)
        self.sudo().write({"last_synced_at": fields.Datetime.now(), "last_error": False})

    def action_sync_now(self):
        self._check_owner()
        for connection in self:
            connection.sudo()._sync_one()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_disconnect(self):
        self._check_owner()
        for connection in self:
            connection.sudo().write({"active": False, "api_token": False})
            blocks = self.env["odental.appointment"].sudo().search([
                ("entry_type", "=", "busy"),
                ("organization_id", "=", connection.organization_id.id),
                ("professional_id", "=", connection.professional_id.id),
                ("external_source", "=", "todoist"),
                ("state", "!=", "cancelled"),
            ])
            blocks.write({"state": "cancelled"})
        return {"type": "ir.actions.client", "tag": "reload"}

    @api.model
    def _cron_sync(self):
        if not self.env.is_superuser():
            raise AccessError("La tarea de sincronización requiere el usuario del sistema.")
        for connection in self.sudo().search([("active", "=", True)]):
            try:
                with self.env.cr.savepoint():
                    connection._sync_one()
            except Exception:  # One failed account must not block other clinics.
                connection.sudo().write({"last_error": "Todoist no se actualizó; revise la conexión."})
