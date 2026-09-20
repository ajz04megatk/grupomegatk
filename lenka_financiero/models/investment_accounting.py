from odoo import fields, models, _
from odoo.exceptions import ValidationError


class ResCompanyLenkaInvestmentAccounting(models.Model):
    _inherit = 'res.company'

    lenka_investment_journal_id = fields.Many2one('account.journal', string='Lenka: Diario de inversiones')
    lenka_investor_liability_account_id = fields.Many2one('account.account', string='Lenka: Obligacion con inversionistas')
    lenka_passive_interest_expense_account_id = fields.Many2one('account.account', string='Lenka: Gasto por intereses pasivos')


class ResConfigSettingsLenkaInvestmentAccounting(models.TransientModel):
    _inherit = 'res.config.settings'

    lenka_investment_journal_id = fields.Many2one(related='company_id.lenka_investment_journal_id', readonly=False)
    lenka_investor_liability_account_id = fields.Many2one(related='company_id.lenka_investor_liability_account_id', readonly=False)
    lenka_passive_interest_expense_account_id = fields.Many2one(related='company_id.lenka_passive_interest_expense_account_id', readonly=False)


class LenkaInvestmentAccounting(models.Model):
    _inherit = 'lenka.investment'

    receipt_move_id = fields.Many2one('account.move', string='Partida de recepcion', readonly=True, copy=False)

    def action_create_receipt_move(self):
        for rec in self:
            if rec.state not in ('active', 'matured', 'closed'):
                raise ValidationError(_('La inversion debe estar activa antes de contabilizar la recepcion.'))
            if rec.receipt_move_id:
                continue
            company = rec.company_id
            journal = company.lenka_investment_journal_id
            liability = company.lenka_investor_liability_account_id
            if not journal or not liability:
                raise ValidationError(_('Configure el diario de inversiones y la cuenta de obligacion con inversionistas.'))
            if journal.company_id != company:
                raise ValidationError(_('El diario de inversiones debe pertenecer a la misma empresa.'))
            liquidity = journal.default_account_id
            if not liquidity:
                raise ValidationError(_('El diario de inversiones debe tener una cuenta contable por defecto.'))
            amount_company = rec.currency_id._convert(rec.principal_amount, company.currency_id, company, rec.start_date)
            lines = [
                (0, 0, {
                    'name': _('Deposito recibido - %s') % rec.name,
                    'partner_id': rec.partner_id.id,
                    'account_id': liquidity.id,
                    'debit': amount_company,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': _('Obligacion con inversionista - %s') % rec.name,
                    'partner_id': rec.partner_id.id,
                    'account_id': liability.id,
                    'debit': 0.0,
                    'credit': amount_company,
                }),
            ]
            move = self.env['account.move'].with_company(company).create({
                'move_type': 'entry',
                'date': rec.start_date,
                'journal_id': journal.id,
                'ref': '%s - Recepcion deposito' % rec.name,
                'line_ids': lines,
            })
            rec.receipt_move_id = move.id
        return True


class LenkaInvestmentInterestAccounting(models.Model):
    _inherit = 'lenka.investment.interest'

    move_id = fields.Many2one('account.move', string='Partida contable', readonly=True, copy=False)
    adjustment_move_id = fields.Many2one('account.move', string='Partida de ajuste', readonly=True, copy=False)

    def action_create_account_move(self):
        for rec in self:
            if rec.state not in ('accrued', 'paid'):
                raise ValidationError(_('El interes debe estar devengado antes de contabilizarse.'))
            if rec.move_id:
                continue
            investment = rec.investment_id
            company = investment.company_id
            journal = company.lenka_investment_journal_id
            liability = company.lenka_investor_liability_account_id
            expense = company.lenka_passive_interest_expense_account_id
            if not journal or not liability or not expense:
                raise ValidationError(_('Configure diario, obligacion con inversionistas y gasto de intereses pasivos.'))
            amount_company = investment.currency_id._convert(rec.amount, company.currency_id, company, rec.period_date)
            move = self.env['account.move'].with_company(company).create({
                'move_type': 'entry',
                'date': rec.period_date,
                'journal_id': journal.id,
                'ref': '%s - Interes pasivo' % investment.name,
                'line_ids': [
                    (0, 0, {
                        'name': _('Gasto interes pasivo - %s') % investment.name,
                        'partner_id': investment.partner_id.id,
                        'account_id': expense.id,
                        'debit': amount_company,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': _('Interes por pagar / capitalizado - %s') % investment.name,
                        'partner_id': investment.partner_id.id,
                        'account_id': liability.id,
                        'debit': 0.0,
                        'credit': amount_company,
                    }),
                ],
            })
            rec.move_id = move.id
        return True


class LenkaInvestmentWithdrawalAccounting(models.Model):
    _inherit = 'lenka.investment.withdrawal'

    move_id = fields.Many2one('account.move', string='Partida contable', readonly=True, copy=False)
    adjustment_move_id = fields.Many2one('account.move', string='Ajuste por retiro anticipado', readonly=True, copy=False)

    def action_create_early_withdrawal_adjustment(self):
        for rec in self:
            if not rec.early_withdrawal:
                continue
            investment = rec.investment_id
            company = investment.company_id
            journal = company.lenka_investment_journal_id
            liability = company.lenka_investor_liability_account_id
            expense = company.lenka_passive_interest_expense_account_id
            if not journal or not liability or not expense:
                raise ValidationError(_('Configure diario, obligacion con inversionistas y gasto de intereses pasivos.'))
            if rec.adjustment_move_id:
                continue

            contractual_interest = sum(
                investment.interest_line_ids.filtered(
                    lambda l: l.period_date <= rec.date and l.move_id
                ).mapped('amount')
            )
            recalculated_interest = rec.accrued_interest_amount
            difference = contractual_interest - recalculated_interest
            if difference <= 0:
                continue

            amount_company = investment.currency_id._convert(difference, company.currency_id, company, rec.date)
            move = self.env['account.move'].with_company(company).create({
                'move_type': 'entry',
                'date': rec.date,
                'journal_id': journal.id,
                'ref': '%s - Ajuste retiro anticipado' % investment.name,
                'line_ids': [
                    (0, 0, {
                        'name': _('Disminucion obligacion por tasa penalizada - %s') % investment.name,
                        'partner_id': investment.partner_id.id,
                        'account_id': liability.id,
                        'debit': amount_company,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': _('Reversion gasto interes pasivo - %s') % investment.name,
                        'partner_id': investment.partner_id.id,
                        'account_id': expense.id,
                        'debit': 0.0,
                        'credit': amount_company,
                    }),
                ],
            })
            rec.adjustment_move_id = move.id
        return True

    def action_create_account_move(self):
        for rec in self:
            if rec.state != 'posted':
                raise ValidationError(_('El retiro debe estar aplicado antes de contabilizarse.'))
            if rec.early_withdrawal:
                rec.action_create_early_withdrawal_adjustment()
            if rec.move_id:
                continue
            investment = rec.investment_id
            company = investment.company_id
            journal = company.lenka_investment_journal_id
            liability = company.lenka_investor_liability_account_id
            if not journal or not liability:
                raise ValidationError(_('Configure el diario de inversiones y la cuenta de obligacion con inversionistas.'))
            liquidity = journal.default_account_id
            if not liquidity:
                raise ValidationError(_('El diario de inversiones debe tener una cuenta contable por defecto.'))
            amount = rec.total_amount
            amount_company = investment.currency_id._convert(amount, company.currency_id, company, rec.date)
            move = self.env['account.move'].with_company(company).create({
                'move_type': 'entry',
                'date': rec.date,
                'journal_id': journal.id,
                'ref': '%s - Retiro inversionista' % investment.name,
                'line_ids': [
                    (0, 0, {
                        'name': _('Disminucion obligacion inversionista - %s') % investment.name,
                        'partner_id': investment.partner_id.id,
                        'account_id': liability.id,
                        'debit': amount_company,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': _('Pago a inversionista - %s') % investment.name,
                        'partner_id': investment.partner_id.id,
                        'account_id': liquidity.id,
                        'debit': 0.0,
                        'credit': amount_company,
                    }),
                ],
            })
            rec.move_id = move.id
        return True
