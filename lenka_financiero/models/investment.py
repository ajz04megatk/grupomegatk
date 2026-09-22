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
        ('fixed', 'Plazo fijo'), ('current', 'Cuenta corriente / a la vista'), ('other', 'Otro')
    ], string='Tipo', required=True, default='fixed', tracking=True)
    principal_amount = fields.Monetary(string='Capital recibido', required=True, tracking=True)
    passive_rate = fields.Float(string='Tasa contractual preferencial (%)', required=True, tracking=True)
    early_withdrawal_rate = fields.Float(string='Tasa por retiro anticipado (%)', default=0.0, tracking=True)
    rate_period = fields.Selection([('monthly', 'Mensual'), ('annual', 'Anual')], default='annual', required=True)
    start_date = fields.Date(string='Fecha de inicio', required=True, default=fields.Date.context_today)
    maturity_date = fields.Date(string='Vencimiento')
    term_months = fields.Integer(string='Plazo (meses)')
    capitalization = fields.Selection([
        ('monthly', 'Capitalizacion mensual'), ('maturity', 'Pago al vencimiento'), ('manual', 'Manual')
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
    withheld_interest_tax = fields.Monetary(string='Impuesto retenido sobre intereses', compute='_compute_totals')
    withdrawn_principal = fields.Monetary(string='Capital retirado', compute='_compute_totals')
    outstanding_principal = fields.Monetary(string='Capital vigente', compute='_compute_totals')
    notes = fields.Text(string='Observaciones')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('lenka.investment') or 'Nuevo'
        return super().create(vals_list)

    @api.constrains('principal_amount', 'passive_rate', 'early_withdrawal_rate', 'term_months', 'start_date', 'maturity_date')
    def _check_values(self):
        for rec in self:
            if rec.principal_amount <= 0:
                raise ValidationError(_('El capital recibido debe ser mayor que cero.'))
            if rec.passive_rate < 0 or rec.early_withdrawal_rate < 0:
                raise ValidationError(_('Las tasas no pueden ser negativas.'))
            if rec.term_months < 0:
                raise ValidationError(_('El plazo no puede ser negativo.'))
            if rec.maturity_date and rec.maturity_date < rec.start_date:
                raise ValidationError(_('El vencimiento no puede ser anterior a la fecha de inicio.'))

    @api.depends('interest_line_ids.amount', 'interest_line_ids.net_amount', 'interest_line_ids.tax_amount', 'interest_line_ids.state', 'withdrawal_ids.principal_amount', 'withdrawal_ids.state')
    def _compute_totals(self):
        for rec in self:
            posted_interest = rec.interest_line_ids.filtered(lambda l: l.state in ('accrued', 'paid'))
            rec.accrued_interest = sum(posted_interest.mapped('amount'))
            rec.paid_interest = sum(rec.interest_line_ids.filtered(lambda l: l.state == 'paid').mapped('net_amount'))
            rec.withheld_interest_tax = sum(posted_interest.mapped('tax_amount'))
            rec.withdrawn_principal = sum(rec.withdrawal_ids.filtered(lambda w: w.state == 'posted').mapped('principal_amount'))
            rec.outstanding_principal = max(rec.principal_amount - rec.withdrawn_principal, 0.0)

    def _monthly_rate_for(self, rate):
        self.ensure_one()
        return rate / 100.0 if self.rate_period == 'monthly' else rate / 1200.0

    def _monthly_rate(self):
        self.ensure_one()
        return self._monthly_rate_for(self.passive_rate)

    def action_activate(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.investment_type == 'fixed' and rec.early_withdrawal_rate <= 0:
                raise ValidationError(_('Para una inversion a plazo fijo debe indicar la tasa aplicable por retiro anticipado.'))
            if rec.investment_type == 'fixed' and rec.early_withdrawal_rate > rec.passive_rate:
                raise ValidationError(_('La tasa por retiro anticipado no puede ser mayor que la tasa contractual preferencial.'))
            if rec.investment_type == 'fixed' and not (rec.maturity_date or rec.term_months):
                raise ValidationError(_('Para una inversion a plazo fijo debe indicar vencimiento o plazo.'))
            if not rec.maturity_date and rec.term_months:
                rec.maturity_date = fields.Date.add(rec.start_date, months=rec.term_months)
            rec.state = 'active'
        return True

    def _generate_interest_until(self, end_date, rate, replace=False):
        self.ensure_one()
        if replace:
            self.interest_line_ids.filtered(lambda l: l.state != 'paid').unlink()
        monthly_rate = self._monthly_rate_for(rate)
        base = self.principal_amount
        current = fields.Date.add(self.start_date, months=1)
        existing_dates = set(self.interest_line_ids.filtered(lambda l: l.state != 'cancelled').mapped('period_date'))
        while current <= end_date:
            if self.maturity_date and current > self.maturity_date:
                break
            if current not in existing_dates:
                amount = base * monthly_rate
                self.env['lenka.investment.interest'].create({
                    'investment_id': self.id,
                    'period_date': current,
                    'base_amount': base,
                    'rate': rate,
                    'amount': amount,
                    'state': 'accrued',
                })
                if self.capitalization == 'monthly':
                    base += amount
            else:
                existing = self.interest_line_ids.filtered(lambda l: l.period_date == current and l.state != 'cancelled')[:1]
                if existing and self.capitalization == 'monthly':
                    base = existing.base_amount + existing.amount
            current = fields.Date.add(current, months=1)
        return base

    def action_generate_monthly_interest(self):
        for rec in self:
            if rec.state not in ('active', 'matured'):
                raise ValidationError(_('La inversion debe estar activa para generar intereses.'))
            end_date = min(fields.Date.context_today(rec), rec.maturity_date) if rec.maturity_date else fields.Date.context_today(rec)
            rec._generate_interest_until(end_date, rec.passive_rate, replace=False)
            if rec.maturity_date and fields.Date.context_today(rec) >= rec.maturity_date:
                rec.state = 'matured'
        return True

    def action_recalculate_early_withdrawal(self, withdrawal_date):
        self.ensure_one()
        if not self.maturity_date or withdrawal_date >= self.maturity_date:
            return self.accrued_interest
        if self.early_withdrawal_rate <= 0:
            raise ValidationError(_('Configure la tasa aplicable por retiro anticipado.'))
        paid_lines = self.interest_line_ids.filtered(lambda l: l.state == 'paid')
        if paid_lines:
            raise ValidationError(_('Existen intereses ya pagados. Debe regularizarse el ajuste contable antes de recalcular el retiro anticipado.'))
        self._generate_interest_until(withdrawal_date, self.early_withdrawal_rate, replace=True)
        return sum(self.interest_line_ids.filtered(lambda l: l.state == 'accrued' and l.period_date <= withdrawal_date).mapped('amount'))


class LenkaInvestmentInterest(models.Model):
    _name = 'lenka.investment.interest'
    _description = 'Interes Pasivo Lenka'
    _order = 'period_date, id'

    investment_id = fields.Many2one('lenka.investment', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='investment_id.currency_id')
    period_date = fields.Date(string='Fecha periodo', required=True)
    base_amount = fields.Monetary(string='Base')
    rate = fields.Float(string='Tasa (%)')
    amount = fields.Monetary(string='Interes bruto', required=True)
    tax_rate = fields.Float(string='Impuesto sobre interes (%)', default=lambda self: self._default_tax_rate())
    tax_amount = fields.Monetary(string='Impuesto retenido', compute='_compute_tax', store=True)
    net_amount = fields.Monetary(string='Interes neto', compute='_compute_tax', store=True)
    state = fields.Selection([('draft', 'Borrador'), ('accrued', 'Devengado'), ('paid', 'Pagado'), ('cancelled', 'Anulado')], default='draft')
    payment_reference = fields.Char(string='Referencia de pago')


    def _default_tax_rate(self):
        value = self.env['ir.config_parameter'].sudo().get_param('lenka_financiero.passive_interest_tax_rate', '0')
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @api.depends('amount', 'tax_rate')
    def _compute_tax(self):
        for rec in self:
            rate = min(max(rec.tax_rate or 0.0, 0.0), 100.0) / 100.0
            rec.tax_amount = rec.amount * rate
            rec.net_amount = rec.amount - rec.tax_amount

    @api.constrains('tax_rate')
    def _check_tax_rate(self):
        for rec in self:
            if rec.tax_rate < 0 or rec.tax_rate > 100:
                raise ValidationError(_('El impuesto sobre intereses debe estar entre 0% y 100%.'))

class LenkaInvestmentWithdrawal(models.Model):
    _name = 'lenka.investment.withdrawal'
    _description = 'Retiro de Inversion Lenka'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    investment_id = fields.Many2one('lenka.investment', required=True, ondelete='restrict', tracking=True)
    currency_id = fields.Many2one(related='investment_id.currency_id', store=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    principal_amount = fields.Monetary(string='Capital a retirar', required=True)
    accrued_interest_amount = fields.Monetary(string='Interes reconocido', readonly=True)
    early_withdrawal = fields.Boolean(string='Retiro anticipado', compute='_compute_early_withdrawal', store=True)
    effective_rate = fields.Float(string='Tasa efectiva aplicada (%)', readonly=True)
    total_amount = fields.Monetary(string='Total a pagar', compute='_compute_total', store=True)
    reference = fields.Char(string='Referencia')
    state = fields.Selection([('draft', 'Borrador'), ('posted', 'Aplicado'), ('cancelled', 'Anulado')], default='draft', tracking=True)

    @api.depends('date', 'investment_id.maturity_date')
    def _compute_early_withdrawal(self):
        for rec in self:
            rec.early_withdrawal = bool(rec.investment_id.maturity_date and rec.date < rec.investment_id.maturity_date)

    @api.depends('principal_amount', 'accrued_interest_amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = rec.principal_amount + rec.accrued_interest_amount

    @api.constrains('principal_amount')
    def _check_values(self):
        for rec in self:
            if rec.principal_amount <= 0:
                raise ValidationError(_('El capital a retirar debe ser mayor que cero.'))

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            investment = rec.investment_id
            if investment.state not in ('active', 'matured'):
                raise ValidationError(_('La inversion debe estar activa o vencida para registrar un retiro.'))
            if rec.date < investment.start_date:
                raise ValidationError(_('La fecha del retiro no puede ser anterior al inicio de la inversion.'))
            if rec.principal_amount > investment.outstanding_principal + 0.01:
                raise ValidationError(_('El retiro excede el capital vigente.'))
            previous_withdrawals = investment.withdrawal_ids.filtered(lambda w: w.state == 'posted' and w.id != rec.id)
            if previous_withdrawals and rec.early_withdrawal:
                raise ValidationError(_('Un segundo retiro anticipado requiere una reestructuracion del contrato. No se recalculara automaticamente para evitar duplicar intereses.'))
            if rec.early_withdrawal:
                recalculated = investment.action_recalculate_early_withdrawal(rec.date)
                rec.write({
                    'accrued_interest_amount': recalculated,
                    'effective_rate': investment.early_withdrawal_rate,
                })
            else:
                investment.action_generate_monthly_interest()
                unpaid_interest = investment.interest_line_ids.filtered(lambda l: l.state == 'accrued')
                rec.write({
                    'accrued_interest_amount': sum(unpaid_interest.mapped('net_amount')),
                    'effective_rate': investment.passive_rate,
                })
            rec.state = 'posted'
            if rec.principal_amount >= investment.outstanding_principal - 0.01:
                investment.state = 'closed'
        return True
