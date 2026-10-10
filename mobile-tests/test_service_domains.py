"""Execute real service methods with a query recorder, without Odoo/DB/network.

Checks query construction and access gating, NOT ORM record-rule integration.
The TransactionCase suite must still run on an isolated Odoo test database.
"""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'lenka_financiero/models'


class AccessError(Exception):
    pass


def load_service():
    package = ModuleType('lenka_service_test')
    package.__path__ = [str(ROOT)]
    odoo = ModuleType('odoo')
    odoo.api = SimpleNamespace(model=lambda function: function)
    odoo.fields = SimpleNamespace()
    odoo.models = SimpleNamespace(AbstractModel=object)
    odoo._ = lambda text: text
    exceptions = ModuleType('odoo.exceptions')
    exceptions.AccessError = AccessError
    spec = importlib.util.spec_from_file_location(
        'lenka_service_test.mobile_service', ROOT / 'mobile_service.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'odoo': odoo, 'odoo.exceptions': exceptions,
                                 'lenka_service_test': package}):
        spec.loader.exec_module(module)
    return module.LenkaMobileService


Service = load_service()


class QueryRecorder:
    def __init__(self):
        self.calls = []
        self.user = SimpleNamespace(
            partner_id=SimpleNamespace(id=17, lenka_mobile_enabled=True,
                                       display_name='Fictional client', email='', phone='', mobile=''),
            company_ids=SimpleNamespace(ids=[8, 9]),
            has_group=lambda group: group == 'lenka_financiero.group_lenka_mobile_client')

    def __getitem__(self, model):
        recorder = self

        class Search:
            def sudo(self):
                return self

            def search(self, domain, **kwargs):
                recorder.calls.append((model, domain, kwargs))
                return []

        return Search()


class ServiceDomainsTest(unittest.TestCase):
    methods = ('get_my_dashboard', 'get_my_operations', 'get_my_operation_detail',
               'get_my_investments', 'get_my_investment_detail', 'get_my_statements')

    def setUp(self):
        self.service = Service()
        self.service.env = QueryRecorder()

    def call(self, method):
        return getattr(self.service, method)(42) if method.endswith('_detail') else getattr(self.service, method)()

    def test_all_queries_require_exact_contact_and_allowed_company(self):
        for method in self.methods:
            with self.subTest(method=method):
                self.service.env.calls.clear()
                try:
                    self.call(method)
                except AccessError:
                    self.assertTrue(method.endswith('_detail'))
                self.assertTrue(self.service.env.calls)
                for model, domain, _ in self.service.env.calls:
                    self.assertIn(('partner_id', '=', 17), domain)
                    self.assertIn(('company_id', 'in', [8, 9]), domain)
                    states = {
                        'lenka.financial.operation': ('approved', 'contracted', 'active', 'done'),
                        'lenka.investment': ('active', 'matured', 'closed'),
                        'lenka.statement': ('generated', 'sent'),
                    }
                    self.assertIn(('state', 'in', states[model]), domain)
                    if model == 'lenka.financial.operation':
                        self.assertIn(('is_quote', '=', False), domain)
                    if method.endswith('_detail'):
                        self.assertIn(('id', '=', 42), domain)

    def test_disabled_access_stops_before_any_sudo_search(self):
        self.service.env.user.partner_id.lenka_mobile_enabled = False
        self.assert_all_denied()

    def test_missing_mobile_group_stops_before_any_sudo_search(self):
        self.service.env.user.has_group = lambda group: False
        self.assert_all_denied()

    def test_missing_partner_stops_before_any_sudo_search(self):
        self.service.env.user.partner_id = None
        self.assert_all_denied()

    def assert_all_denied(self):
        for method in self.methods:
            with self.subTest(method=method), self.assertRaises(AccessError):
                self.call(method)
        self.assertEqual(self.service.env.calls, [])


if __name__ == '__main__':
    unittest.main()
