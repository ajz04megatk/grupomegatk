"""Exercise onboarding decisions using record doubles; not an Odoo ORM test."""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace as Record
import sys
import unittest
from unittest.mock import patch


class AccessError(Exception):
    pass


class ValidationError(Exception):
    pass


class Datetime:
    def __new__(cls, **kwargs):
        return None

    @staticmethod
    def now():
        return '2026-10-10 00:00:00'


def load_model():
    odoo = ModuleType('odoo')
    odoo.api = Record(model_create_multi=lambda method: method)
    odoo.fields = Record(Boolean=lambda **kw: None, Datetime=Datetime,
                         Many2one=lambda *args, **kw: None)
    odoo.models = Record(Model=object)
    odoo._ = lambda text: text
    exceptions = ModuleType('odoo.exceptions')
    exceptions.AccessError, exceptions.ValidationError = AccessError, ValidationError
    path = Path(__file__).resolve().parents[1] / 'lenka_financiero/models/mobile_access.py'
    spec = importlib.util.spec_from_file_location('mobile_onboarding_test_source', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'odoo': odoo, 'odoo.exceptions': exceptions}):
        spec.loader.exec_module(module)
    return module.ResPartnerLenkaMobile


Model = load_model()


class Partner:
    id = 17
    name = 'Fictional client'
    email = 'new@example.invalid'

    def __init__(self):
        self.writes = []

    def write(self, values):
        self.writes.append(values)


class Users:
    def __init__(self, existing=None, collision=False):
        self.existing, self.collision = existing, collision
        self.created = []
        self.context = {}

    def sudo(self):
        return self

    def with_context(self, **values):
        self.context.update(values)
        return self

    def search(self, domain, limit=1):
        return self.existing if domain[0][0] == 'partner_id' else self.collision

    def create(self, values):
        self.created.append(values)
        return Record(id=90)


class Environment:
    su = False

    def __init__(self, users, manager=True):
        self.users = users
        self.company = Record(id=8)
        self.user = Record(has_group=lambda group: manager)

    def ref(self, key):
        return Record(id=2 if key == 'base.group_portal' else 3)

    def __getitem__(self, name):
        assert name == 'res.users'
        return self.users


class Partners(Model):
    def __iter__(self):
        return iter(self.partners)


class OnboardingTest(unittest.TestCase):
    def prepare(self, users=None, manager=True):
        model = Partners()
        model.env = Environment(users or Users(), manager)
        model.partners = [Partner()]
        return model

    def test_new_user_only_gets_selected_company_and_portal_roles(self):
        model = self.prepare()
        model.action_enable_lenka_mobile()
        values = model.env.users.created[0]
        self.assertEqual(values['company_id'], 8)
        self.assertEqual(values['company_ids'], [(6, 0, [8])])
        self.assertEqual(values['groups_id'], [(6, 0, [2, 3])])
        self.assertTrue(model.env.users.context['active_test'] is False)
        self.assertNotIn('password', values)

    def test_unauthorized_manager_is_stopped_before_creation(self):
        model = self.prepare(manager=False)
        with self.assertRaises(AccessError):
            model.action_enable_lenka_mobile()
        self.assertEqual(model.env.users.created, [])

    def test_other_contacts_login_is_not_reused(self):
        model = self.prepare(Users(collision=True))
        with self.assertRaises(ValidationError):
            model.action_enable_lenka_mobile()
        self.assertEqual(model.env.users.created, [])
        self.assertEqual(model.partners[0].writes, [])

    def test_archived_user_is_not_recreated(self):
        model = self.prepare(Users(existing=Record(active=False)))
        with self.assertRaises(ValidationError):
            model.action_enable_lenka_mobile()
        self.assertEqual(model.env.users.created, [])

    def test_existing_company_permissions_are_not_expanded(self):
        model = self.prepare(Users(existing=Record(active=True, company_ids=[])))
        with self.assertRaises(ValidationError):
            model.action_enable_lenka_mobile()
        self.assertEqual(model.partners[0].writes, [])


if __name__ == '__main__':
    unittest.main()
