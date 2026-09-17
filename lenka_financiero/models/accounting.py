from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompanyLenkaAccounting(models.Model):
    _inherit = 'res.company'

    lenka_disbursement_journal_id = fields.Many2one('account.journal', string='Lenka: Diario de desembolsos', domain="[('company_id', '=', id)]")
    lenka_collection_journal_id = fields.Many2one('account.journal', string='Lenka: Diario de cobros', domain="[('company_id', '=', id)]")
    lenka_portfolio_account_id = fields.Many2one('account.account', string='Lenka: Cartera / capital por cobrar')
    lenka_interest_income_account_id = fields.Many2one('account.account', string='Lenka: Ingreso por intereses')
    lenka_late_fee_income_account_id = fields.Many2one('account.account', string='Lenka: Ingreso por mora')
    lenka_unapplied_account_id = fields.Many2one('account.account', string='Lenka: Cobros no aplicados / anticipos')


class ResConfigSettingsLenkaAccounting(models.TransientModel):
    _inherit = 'res.config.settings'

    lenka_disbursement_journal_id = fields.Many2one(related='company_id.lenka_disbursement_journal_id', readonly=False)
    lenka_collection_journal_id = fields.Many2one(related='company_id.lenka_collection_journal_id', readonly=False)
    lenka_portfolio_account_id = fields.Many2one(related='company_id.lenka_portfolio_account_id', readonly=False)
    lenka_interest_income_account_id = fields.Many2one(related='company_id.lenka_interest_income_account_id', readonly=False)
    lenka_late_fee_income_account_id = fields.Many2one(related='company_id.lenka_late_fee_income_account_id', readonly=False)
    lenka_unapplied_account_id = fields.Many2one(related='company_id.lenka_unapplied_account_id', readonly=False)


class LenkaDisbursementAccounting(models.Model):
    _inherit = 'lenka.disbursement'

    move_id = fields.Many2one('account.move', string='Partida contable', readonly=True, copy=False)

    def _get_accounting_company(self):
        self.ensure_one()
        return self.operation_id.company_id

    def _prepare_disbursement_move(self):
        self.ensure_one()
        company = self._get_accounting_company()
        journal = company.lenka_disbursement_journal_id
        portfolio = company.lenka_portfolio_account_id
        if not journal or not portfolio:
            raise ValidationError(_('Configure el diario de desembolsos y la cuenta de cartera de Lenka antes de contabilizar.'))
        liquidity = journal.default_account_id
        if not liquidity:
            raise ValidationError(_('El diario de desembolsos debe tener una cuenta contable por defecto.'))
        amount_company = self.currency_id._convert(self.amount, company.currency_id, company, self.date)
        partner = self.operation_id.partner_id
        return {
            'move_type': 'entry',
            'date': self.date,
            'journal_id': journal.id,
            'ref': '%s - %s' % (self.operation_id.name, self.name),
            'line_ids': [
                (0, 0, {
                    'name': _('Capital financiado - %s') % self.operation_id.name,
                    'partner_id': partner.id,
                    'account_id': portfolio.id,
                    'debit': amount_company,
                    'credit': 0.0,
                    'currency_id': self.currency_id.id if self.currency_id != company.currency_id else False,
                    'amount_currency': self.amount if self.currency_id != company.currency_id else 0.0,
                }),
                (0, 0, {
                    'name': _('Desembolso - %s') % self.operation_id.name,
                    'partner_id': self.destination_partner_id.id if self.destination_partner_id else partner.id,
                    'account_id': liquidity.id,
                    'debit': 0.0,
                    'credit': amount_company,
                    'currency_id': self.currency_id.id if self.currency_id != company.currency_id else False,
                    'amount_currency': -self.amount if self.currency_id != company.currency_id else 0.0,
                }),
            ],
        }

    def action_create_account_move(self):
        for rec in self:
            if rec.state != 'posted':
                raise ValidationError(_('El desembolso debe estar aplicado antes de crear la partida contable.'))
            if rec.move_id:
                continue
            move = self.env['account.move'].with_company(rec.operation_id.company_id).create(rec._prepare_disbursement_move())
            move.action_post()
            rec.move_id = move.id
        return True


class LenkaPaymentAccounting(models.Model):
    _inherit = 'lenka.payment'

    move_id = fields.Many2one('account.move', string='Partida contable', readonly=True, copy=False)

    def _prepare_collection_move(self):
        self.ensure_one()
        company = self.operation_id.company_id
        journal = company.lenka_collection_journal_id
        portfolio = company.lenka_portfolio_account_id
        interest_income = company.lenka_interest_income_account_id
        late_income = company.lenka_late_fee_income_account_id
        unapplied_account = company.lenka_unapplied_account_id
        if not journal or not portfolio or not interest_income or not late_income:
            raise ValidationError(_('Configure el diario de cobros y las cuentas de cartera, intereses y mora de Lenka antes de contabilizar.'))
        liquidity = journal.default_account_id
        if not liquidity:
            raise ValidationError(_('El diario de cobros debe tener una cuenta contable por defecto.'))

        applied_total = self.capital_amount + self.interest_amount + self.late_fee_amount
        total_to_book = applied_total + self.unapplied_amount
        if self.unapplied_amount and not unapplied_account:
            raise ValidationError(_('Existe saldo no aplicado. Configure la cuenta de cobros no aplicados / anticipos.'))
        amount_company = self.currency_id._convert(total_to_book, company.currency_id, company, self.payment_date)
        partner = self.partner_id
        lines = [(0, 0, {
            'name': _('Cobro neto Lenka - %s') % self.name,
            'partner_id': partner.id,
            'account_id': liquidity.id,
            'debit': amount_company,
            'credit': 0.0,
            'currency_id': self.currency_id.id if self.currency_id != company.currency_id else False,
            'amount_currency': total_to_book if self.currency_id != company.currency_id else 0.0,
        })]

        def credit_line(account, amount, label):
            if amount <= 0:
                return
            company_amount = self.currency_id._convert(amount, company.currency_id, company, self.payment_date)
            lines.append((0, 0, {
                'name': label,
                'partner_id': partner.id,
                'account_id': account.id,
                'debit': 0.0,
                'credit': company_amount,
                'currency_id': self.currency_id.id if self.currency_id != company.currency_id else False,
                'amount_currency': -amount if self.currency_id != company.currency_id else 0.0,
            }))

        credit_line(portfolio, self.capital_amount, _('Capital cobrado - %s') % self.operation_id.name)
        credit_line(interest_income, self.interest_amount, _('Intereses cobrados - %s') % self.operation_id.name)
        credit_line(late_income, self.late_fee_amount, _('Mora cobrada - %s') % self.operation_id.name)
        if self.unapplied_amount:
            credit_line(unapplied_account, self.unapplied_amount, _('Cobro no aplicado - %s') % self.operation_id.name)

        return {
            'move_type': 'entry',
            'date': self.payment_date,
            'journal_id': journal.id,
            'ref': '%s - %s' % (self.operation_id.name, self.name),
            'line_ids': lines,
        }

    def action_create_account_move(self):
        for rec in self:
            if rec.state != 'posted':
                raise ValidationError(_('El cobro debe estar aplicado antes de crear la partida contable.'))
            if rec.move_id:
                continue
            move = self.env['account.move'].with_company(rec.operation_id.company_id).create(rec._prepare_collection_move())
            move.action_post()
            rec.move_id = move.id
        return True
