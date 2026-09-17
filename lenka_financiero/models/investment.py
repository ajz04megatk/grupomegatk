from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LenkaInvestment(models.Model):
    _name = 'lenka.investment'
    _description = 'Inversion / Deposito Lenka'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(default='Nuevo', readonly=True, copy=False, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Inversionista / Depositante', required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)
    investment_type = fields.Selection([
        ('fixed', 'Plazo fijo'),
        ('current', 'Cuenta corriente / a la vista'),
        ('other', 'Otro'),
    ], string='Tipo', required=True, default='fixed', tracking=True)
    principal_amount = fields.Monetary(string='Capital recibido', required=True, tracking=True)
    passive_rate = fields.Float(string='Tasa pasiva (%)', required=True, tracking=True)
    rate_period = fields.Selection([('monthly', 'Mensual'), ('annual', 'Anual')], default='annual', required=True)
    start_date = fields.Date(string='Fecha de inicio', required=True, default=fields.Date.context_today)
    maturity_date = fields.Date(string='Vencimiento')
    term_months = fields.Integer(string='Plazo (meses)')
    capitalization = fields.Selection([
        ('monthly', 'Capitalizacion mensual'),
        ('maturity', 'Pago al vencimiento'),
        ('manual', 'Manual'),
    ], string='Forma de reconocimiento', default='monthly', required=True)
    receiving_account = fields.Char(string='Cuenta receptora / referencia bancaria')
    contract_reference = fields.Char(string='Referencia de contrato')
    state = fields.Selection([
        ('draft', 'Borrador'), ('active', 'Activa'), ('matured', 'Vencida'),
        ('closed', 'Cerrada'), ('cancelled', 'Cancelada')
    ], default='draft', tracking=True)
    interest_line_ids = fields.One2many('lenka.investment.interest', 'investment_id', string='Intereses')
    withdrawal_ids = fields.One2many('lenka.investment.withdrawal', 'investment_id', string='Retiros')
    accrued_interest = fields.Monetary(string='Interes acumulado', compute='_compute_totals')
    paid_interest = fields.Monetary(string='Interes pagado', compute='_compute_totals')
    withdrawn_principal = fields.Monetary(string='Capital retirado', compute='_compute_totals')
    outstanding_principal = fields.Monetary(string='Capital vigente', compute='_compute_totals')
    notes = fields.Text(string='Observaciones')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('lenka.investment') or 'Nuevo'
        return super().create(vals_list)

    @api.constrains('principal_amount', 'passive_rate', 'term_months', 'start_date', 'maturity_date')
    def _check_values(self):
        for rec in self:
            if rec.principal_amount <= 0:
                raise ValidationError(_('El capital recibido debe ser mayor que cero.'))
            if rec.passive_rate < 0:
                raise ValidationError(_('La tasa pasiva no puede ser negativa.'))
            if rec.term_months < 0:
                raise ValidationError(_('El plazo no puede ser negativo.'))
            if rec.maturity_date and rec.maturity_date < rec.start_date:
                raise ValidationError(_('El vencimiento no puede ser anterior a la fecha de inicio.'))

    @api.depends('interest_line_ids.amount', 'interest_line_ids.state', 'withdrawal_ids.principal_amount', 'withdrawal_ids.state')
    def _compute_totals(self):
        for rec in self:
            posted_interest = rec.interest_line_ids.filtered(lambda l: l.state in ('accrued', 'paid'))
            rec.accrued_interest = sum(posted_interest.mapped('amount'))
            rec.paid_interest = sum(rec.interest_line_ids.filtered(lambda l: l.state == 'paid').mapped('amount'))
            rec.withdrawn_principal = sum(rec.withdrawal_ids.filtered(lambda w: w.state == 'posted').mapped('principal_amount'))
            rec.outstanding_principal = max(rec.principal_amount - rec.withdrawn_principal, 0.0)

    def _monthly_rate(self):
        self.ensure_one()
        return self.passive_rate / 100.0 if self.rate_period == 'monthly' else self.passive_rate / 1200.0

    def action_activate(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.investment_type == 'fixed' and not (rec.maturity_date or rec.term_months):
                raise ValidationError(_('Para una inversion a plazo fijo debe indicar vencimiento o plazo.'))
            if not rec.maturity_date and rec.term_months:
                rec.maturity_date = fields.Date.add(rec.start_date, months=rec.term_months)
            rec.state = 'active'
        return True

    def action_generate_monthly_interest(self):
        for rec in self:
            if rec.state not in ('active', 'matured'):
                raise ValidationError(_('La inversion debe estar activa para generar intereses.'))
            monthly_rate = rec._monthly_rate()
            base = rec.outstanding_principal
            if base <= 0:
                continue
            next_date = rec.start_date
            existing_dates = set(rec.interest_line_ids.mapped('period_date'))
            if existing_dates:
                next_date = fields.Date.add(max(existing_dates), months=1)
            while True:
                next_date = fields.Date.add(next_date, months=1) if next_date == rec.start_date else next_date
                if rec.maturity_date and next_date > rec.maturity_date:
                    break
                if next_date > fields.Date.context_today(rec):
                    break
                if next_date not in existing_dates:
                    amount = base * monthly_rate
                    self.env['lenka.investment.interest'].create({
                        'investment_id': rec.id,
                        'period_date': next_date,
                        'base_amount': base,
                        'rate': rec.passive_rate,
                        'amount': amount,
                        'state': 'accrued',
                    })
                    if rec.capitalization == 'monthly':
                        base += amount
                next_date = fields.Date.add(next_date, months=1)
            if rec.maturity_date and fields.Date.context_today(rec) >= rec.maturity_date:
                rec.state = 'matured'
        return True


class LenkaInvestmentInterest(models.Model):
    _name = 'lenka.investment.interest'
    _description = 'Interes Pasivo Lenka'
    _order = 'period_date, id'

    investment_id = fields.Many2one('lenka.investment', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='investment_id.currency_id')
    period_date = fields.Date(string='Fecha periodo', required=True)
    base_amount = fields.Monetary(string='Base')
    rate = fields.Float(string='Tasa (%)')
    amount = fields.Monetary(string='Interes', required=True)
    state = fields.Selection([('draft', 'Borrador'), ('accrued', 'Devengado'), ('paid', 'Pagado'), ('cancelled', 'Anulado')], default='draft')
    payment_reference = fields.Char(string='Referencia de pago')


class LenkaInvestmentWithdrawal(models.Model):
    _name = 'lenka.investment.withdrawal'
    _description = 'Retiro de Inversion Lenka'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    investment_id = fields.Many2one('lenka.investment', required=True, ondelete='restrict', tracking=True)
    currency_id = fields.Many2one(related='investment_id.currency_id', store=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    principal_amount = fields.Monetary(string='Capital a retirar', required=True)
    accrued_interest_amount = fields.Monetary(string='Interes reconocido')
    early_withdrawal = fields.Boolean(string='Retiro anticipado', compute='_compute_early_withdrawal', store=True)
    penalty_rate = fields.Float(string='Tasa de penalizacion / tasa reducida (%)')
    penalty_amount = fields.Monetary(string='Ajuste por retiro anticipado', compute='_compute_total', store=True)
    total_amount = fields.Monetary(string='Total a pagar', compute='_compute_total', store=True)
    reference = fields.Char(string='Referencia')
    state = fields.Selection([('draft', 'Borrador'), ('posted', 'Aplicado'), ('cancelled', 'Anulado')], default='draft', tracking=True)

    @api.depends('date', 'investment_id.maturity_date')
    def _compute_early_withdrawal(self):
        for rec in self:
            rec.early_withdrawal = bool(rec.investment_id.maturity_date and rec.date < rec.investment_id.maturity_date)

    @api.depends('principal_amount', 'accrued_interest_amount', 'early_withdrawal', 'penalty_rate')
    def _compute_total(self):
        for rec in self:
            rec.penalty_amount = rec.accrued_interest_amount * rec.penalty_rate / 100.0 if rec.early_withdrawal else 0.0
            rec.total_amount = rec.principal_amount + rec.accrued_interest_amount - rec.penalty_amount

    @api.constrains('principal_amount', 'penalty_rate')
    def _check_values(self):
        for rec in self:
            if rec.principal_amount <= 0:
                raise ValidationError(_('El capital a retirar debe ser mayor que cero.'))
            if rec.penalty_rate < 0 or rec.penalty_rate > 100:
                raise ValidationError(_('La tasa de penalizacion debe estar entre 0% y 100%.'))

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.investment_id.state not in ('active', 'matured'):
                raise ValidationError(_('La inversion debe estar activa o vencida para registrar un retiro.'))
            if rec.principal_amount > rec.investment_id.outstanding_principal + 0.01:
                raise ValidationError(_('El retiro excede el capital vigente.'))
            rec.state = 'posted'
            if rec.principal_amount >= rec.investment_id.outstanding_principal - 0.01:
                rec.investment_id.state = 'closed'
        return True
