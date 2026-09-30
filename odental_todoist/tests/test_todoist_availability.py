from datetime import datetime
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestTodoistAvailability(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organization = cls.env["odental.organization"].create({
            "name": "Clínica piloto", "code": "TODOIST-TEST",
            "user_ids": [(4, cls.env.user.id)],
        })
        cls.professional = cls.env["odental.professional"].create({
            "name": "Jennifer Ejemplo", "user_id": cls.env.user.id,
            "organization_ids": [(4, cls.organization.id)],
        })
        cls.patient = cls.env["odental.patient"].create({
            "name": "Paciente sintético", "organization_id": cls.organization.id,
        })
        cls.site = cls.env["odental.site"].create({
            "name": "Sede de prueba", "organization_id": cls.organization.id,
        })
        cls.service = cls.env["odental.service"].create({
            "name": "Valoración", "code": "TEST-TODOIST",
            "organization_id": cls.organization.id, "duration_minutes": 30,
            "require_room": False, "require_chair": False,
        })
        cls.connection = cls.env["odental.todoist.connection"].sudo().create({
            "professional_id": cls.professional.id,
            "organization_id": cls.organization.id,
            "api_token": "synthetic-test-token",
            "todoist_user_id": "doctor-1",
        })

    def _task(self, date="2026-10-02T10:00:00-06:00", labels=None, checked=False):
        return {
            "id": "task-A", "labels": labels if labels is not None else ["reunión"],
            "due": {"date": date}, "duration": {"amount": 60, "unit": "minute"},
            "checked": checked, "is_deleted": False,
            "responsible_uid": "doctor-1",
            "content": "Motivo privado que nunca debe copiarse a la clínica",
        }

    def _clinical_values(self, start):
        return {
            "organization_id": self.organization.id,
            "professional_id": self.professional.id,
            "patient_id": self.patient.id,
            "site_id": self.site.id,
            "service_id": self.service.id,
            "start_datetime": start,
            "state": "scheduled",
        }

    def _block(self):
        return self.env["odental.appointment"].sudo().search([
            ("entry_type", "=", "busy"),
            ("professional_id", "=", self.professional.id),
            ("external_uid", "=", "task-A"),
        ])

    def test_private_block_conflict_and_completion_release(self):
        self.connection._reconcile_tasks([self._task()])
        block = self._block()
        self.assertEqual(len(block), 1)
        self.assertEqual(block.name, "No disponible")
        self.assertEqual(block.start_datetime, datetime(2026, 10, 2, 16))
        self.assertFalse(block.patient_id or block.service_id or block.site_id or block.notes)
        self.assertNotIn("Motivo privado", block.name)
        with self.assertRaisesRegex(ValidationError, "no está disponible"), self.env.cr.savepoint():
            self.env["odental.appointment"].create(
                self._clinical_values(datetime(2026, 10, 2, 16, 15))
            )
        self.connection._reconcile_tasks([self._task(checked=True)])
        self.assertEqual(block.state, "cancelled")
        clinical = self.env["odental.appointment"].create(
            self._clinical_values(datetime(2026, 10, 2, 16, 15))
        )
        self.assertEqual(clinical.state, "scheduled")

    def test_move_and_label_removal_release_original_slot(self):
        self.connection._reconcile_tasks([self._task()])
        self.connection._reconcile_tasks([self._task(date="2026-10-02T12:00:00-06:00")])
        block = self._block()
        self.assertEqual(len(block), 1)
        self.assertEqual(block.start_datetime, datetime(2026, 10, 2, 18))
        self.connection._reconcile_tasks([self._task(labels=["personal"])])
        self.assertEqual(block.state, "cancelled")

    def test_incomplete_provider_response_keeps_existing_block(self):
        self.connection._reconcile_tasks([self._task()])
        with patch.object(type(self.connection), "_get_json", return_value={"results": None}):
            with self.assertRaises(UserError):
                self.connection._sync_one()
        self.assertEqual(self._block().state, "scheduled")

    def test_other_organization_block_is_untouched(self):
        second = self.env["odental.organization"].create({
            "name": "Otra clínica sintética", "code": "OTHER-TODOIST-TEST",
            "user_ids": [(4, self.env.user.id)],
        })
        self.professional.organization_ids = [(4, second.id)]
        other_connection = self.env["odental.todoist.connection"].sudo().create({
            "professional_id": self.professional.id,
            "organization_id": second.id,
            "api_token": "synthetic-test-token", "todoist_user_id": "doctor-1",
        })
        self.connection._reconcile_tasks([self._task()])
        other_connection._reconcile_tasks([self._task()])
        self.connection._reconcile_tasks([])
        blocks = self._block()
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks.filtered(lambda item: item.organization_id == second).state, "scheduled")
        self.assertEqual(blocks.filtered(lambda item: item.organization_id == self.organization).state, "cancelled")

    def test_untimed_task_never_blocks_and_cancelled_action_exists(self):
        self.connection._reconcile_tasks([self._task(date="2026-10-02")])
        self.assertFalse(self._block())
        action = self.env.ref("odental_core.action_odental_appointment")
        self.assertIn("cancelled", action.domain)

    def test_timed_task_without_paid_duration_uses_default(self):
        task = self._task()
        task["duration"] = None
        self.connection.default_duration_minutes = 45
        self.connection._reconcile_tasks([task])
        self.assertEqual(self._block().duration_minutes, 45)
