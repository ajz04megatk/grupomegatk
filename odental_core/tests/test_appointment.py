from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestODentalAppointment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organization = cls.env["odental.organization"].create({
            "name": "Clínica de prueba", "code": "TEST", "user_ids": [(4, cls.env.user.id)]
        })
        cls.professional = cls.env["odental.professional"].create({
            "name": "Dra. Prueba", "organization_ids": [(4, cls.organization.id)]
        })
        cls.patient = cls.env["odental.patient"].create({
            "name": "Paciente prueba", "organization_id": cls.organization.id
        })
        cls.site = cls.env["odental.site"].create({
            "name": "Sede principal", "organization_id": cls.organization.id
        })
        cls.room = cls.env["odental.resource"].create({
            "name": "Consultorio 1", "resource_type": "room",
            "organization_id": cls.organization.id, "site_id": cls.site.id
        })
        cls.chair = cls.env["odental.resource"].create({
            "name": "Sillón 1", "resource_type": "chair",
            "organization_id": cls.organization.id, "site_id": cls.site.id
        })
        cls.service = cls.env["odental.service"].create({
            "name": "Evaluación", "code": "EVAL", "organization_id": cls.organization.id,
            "duration_minutes": 30, "preparation_minutes": 5, "cleaning_minutes": 10
        })

    def _appointment_values(self, start):
        return {
            "organization_id": self.organization.id,
            "patient_id": self.patient.id,
            "professional_id": self.professional.id,
            "service_id": self.service.id,
            "site_id": self.site.id,
            "resource_ids": [(6, 0, (self.room | self.chair).ids)],
            "start_datetime": start,
            "state": "confirmed",
        }

    def test_service_defaults_and_blocking_window(self):
        start = datetime(2026, 9, 14, 14, 0)
        appointment = self.env["odental.appointment"].create(self._appointment_values(start))
        self.assertEqual(appointment.end_datetime, start + timedelta(minutes=30))
        self.assertEqual(appointment.blocking_start, start - timedelta(minutes=5))
        self.assertEqual(appointment.blocking_end, start + timedelta(minutes=40))

    def test_prevent_professional_overlap(self):
        start = datetime(2026, 9, 14, 14, 0)
        self.env["odental.appointment"].create(self._appointment_values(start))
        with self.assertRaises(ValidationError):
            self.env["odental.appointment"].create(self._appointment_values(start + timedelta(minutes=35)))

    def test_allow_adjacent_appointment_after_cleaning(self):
        start = datetime(2026, 9, 14, 14, 0)
        self.env["odental.appointment"].create(self._appointment_values(start))
        second = self.env["odental.appointment"].create(self._appointment_values(start + timedelta(minutes=40)))
        self.assertTrue(second)

