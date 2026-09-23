from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase


class TestLenkaOperationalFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.client = cls.env['res.partner'].create({'name': 'Cliente recorrido operativo Lenka'})
        cls.guarantor = cls.env['res.partner'].create({'name': 'Aval recorrido operativo Lenka'})
        users = cls.env['res.users'].with_context(no_reset_password=True, tracking_disable=True)
        cls.operator = users.create({
            'name': 'Operador flujo Lenka', 'login': 'lenka_flow_operator',
            'company_id': cls.company.id, 'company_ids': [(6, 0, cls.company.ids)],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id, cls.env.ref('lenka_financiero.group_lenka_user').id])],
        })
        cls.outsider = users.create({
            'name': 'Usuario externo flujo Lenka', 'login': 'lenka_flow_outsider',
            'company_id': cls.company.id, 'company_ids': [(6, 0, cls.company.ids)],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    def _quote(self, company=None, user=None):
        company = company or self.company
        model = self.env['lenka.financial.operation'].with_company(company)
        if user:
            model = model.with_user(user)
        return model.create({
            'partner_id': self.client.id, 'guarantor_ids': [(6, 0, self.guarantor.ids)],
            'company_id': company.id, 'operation_type': 'financing',
            'principal_amount': 12000.0, 'down_payment': 2000.0,
            'interest_rate': 3.0, 'rate_period': 'monthly', 'term_months': 12,
            'calculation_method': 'level', 'first_payment_date': fields.Date.today(),
        })

    def _statement(self, operation):
        return self.env['lenka.statement'].create({
            'statement_type': 'operation', 'partner_id': operation.partner_id.id,
            'operation_id': operation.id, 'company_id': operation.company_id.id,
            'currency_id': operation.currency_id.id,
            'date_from': fields.Date.today(), 'date_to': fields.Date.today(),
        })

    def test_operator_quote_through_contract_collection_and_statement(self):
        quote = self._quote(user=self.operator)
        quote.action_generate_schedule()
        quote.action_generate_schedule()
        self.assertEqual(len(quote.schedule_line_ids), 12)
        self.assertAlmostEqual(sum(quote.schedule_line_ids.mapped('capital')), 10000.0, places=2)
        quote.action_convert_to_application()
        self.assertEqual(quote.state, 'review')
        self.assertFalse(quote.is_quote)

        operation = quote.with_env(self.env)
        operation.action_approve()
        self.env['lenka.contract.template'].create({
            'name': 'Contrato flujo operativo', 'company_id': self.company.id,
            'document_type': 'contract', 'operation_type': 'financing',
            'body_html': '<p>{{CLIENTE}} {{MONTO_FINANCIADO}}</p>',
        })
        operation.action_generate_contract_documents()
        document = operation.generated_document_ids[0]
        document.attachment_id = self.env['ir.attachment'].create({
            'name': 'contrato-prueba.pdf', 'datas': 'RklSTUFETw==',
            'res_model': document._name, 'res_id': document.id,
        })
        document.action_mark_signed()
        operation.action_mark_contracted()
        funding = self.env['lenka.funding.line'].create({
            'operation_id': operation.id, 'source_type': 'own', 'amount': 10000.0,
        })
        self.env['lenka.disbursement'].create({
            'operation_id': operation.id, 'amount': 10000.0, 'funding_line_id': funding.id,
            'destination_type': 'client', 'destination_partner_id': self.client.id,
        }).action_post()
        operation.action_activate()

        payment = self.env['lenka.payment'].with_user(self.operator).create({
            'operation_id': operation.id, 'payment_date': fields.Date.today(),
            'amount': 2300.0, 'payment_method': 'cash',
        })
        payment.action_post()
        statement = self._statement(operation).with_user(self.operator)
        statement.action_generate()
        statement.action_generate()
        self.assertEqual(len(statement.line_ids), 1)
        self.assertAlmostEqual(statement.period_interest, 300.0, places=2)
        self.assertAlmostEqual(statement.period_capital, 2000.0, places=2)
        self.assertAlmostEqual(statement.closing_balance, 8000.0, places=2)
        self.assertAlmostEqual(statement.closing_balance, operation.outstanding_capital, places=2)
        with self.assertRaises(AccessError):
            statement.line_ids.write({'capital': 9000.0})

        report = self.env.ref('lenka_financiero.action_report_lenka_statement').with_user(self.operator)
        html, _ = report._render_qweb_html(report.report_name, docids=statement.ids)
        self.assertIn(self.client.name, html.decode())
        payment.action_cancel()
        statement.action_generate()
        self.assertFalse(statement.line_ids)
        self.assertAlmostEqual(statement.closing_balance, 10000.0, places=2)

    def test_operator_can_generate_investment_statement(self):
        investment = self.env['lenka.investment'].create({
            'partner_id': self.client.id, 'principal_amount': 10000.0,
            'passive_rate': 12.0, 'investment_type': 'current',
        })
        self.env['lenka.investment.interest'].create({
            'investment_id': investment.id, 'period_date': fields.Date.today(),
            'amount': 100.0, 'state': 'accrued',
        })
        statement = self.env['lenka.statement'].with_user(self.operator).create({
            'statement_type': 'investment', 'partner_id': self.client.id,
            'investment_id': investment.id, 'company_id': self.company.id,
            'currency_id': investment.currency_id.id,
            'date_from': fields.Date.today(), 'date_to': fields.Date.today(),
        })
        statement.action_generate()
        statement.action_generate()
        self.assertEqual(len(statement.line_ids), 1)
        self.assertAlmostEqual(statement.period_interest, 100.0, places=2)
        self.assertAlmostEqual(statement.closing_balance, 10100.0, places=2)

    def test_outsider_cannot_generate_schedule_or_statement(self):
        quote = self._quote()
        statement = self._statement(quote)
        with self.assertRaises(AccessError):
            quote.with_user(self.outsider).action_generate_schedule()
        with self.assertRaises(AccessError):
            statement.with_user(self.outsider).action_generate()
        self.assertFalse(quote.schedule_line_ids)
        self.assertEqual(statement.state, 'draft')

    def test_operator_cannot_generate_other_company_details(self):
        company = self.env['res.company'].create({'name': 'Empresa flujo aislado'})
        quote = self._quote(company=company)
        statement = self._statement(quote)
        with self.assertRaises(AccessError):
            quote.with_user(self.operator).with_context(allowed_company_ids=self.company.ids).action_generate_schedule()
        with self.assertRaises(AccessError):
            statement.with_user(self.operator).with_context(allowed_company_ids=self.company.ids).action_generate()
        self.assertFalse(quote.schedule_line_ids)
        self.assertFalse(statement.line_ids)

    def test_mixed_company_generation_rejects_entire_batch(self):
        own = self._quote()
        company = self.env['res.company'].create({'name': 'Empresa lote flujo aislado'})
        other = self._quote(company=company)
        own_statement, other_statement = self._statement(own), self._statement(other)
        with self.assertRaises(AccessError):
            (own | other).with_user(self.operator).with_context(allowed_company_ids=self.company.ids).action_generate_schedule()
        with self.assertRaises(AccessError):
            (own_statement | other_statement).with_user(self.operator).with_context(allowed_company_ids=self.company.ids).action_generate()
        self.assertFalse(own.schedule_line_ids)
        self.assertEqual(own_statement.state, 'draft')

    def test_operator_cannot_manually_edit_generated_schedule(self):
        quote = self._quote(user=self.operator)
        quote.action_generate_schedule()
        with self.assertRaises(AccessError):
            quote.schedule_line_ids[0].write({'capital': 1.0})
        with self.assertRaises(AccessError):
            quote.schedule_line_ids.unlink()
