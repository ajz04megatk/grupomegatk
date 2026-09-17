from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LenkaFinancialOperation(models.Model):
    _name = 'lenka.financial.operation'
    _description = 'Operacion Financiera Lenka'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(default='Nuevo', readonly=True, copy=False, tracking=True)
    is_quote = fields.Boolean(string='Es cotizacion', default=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True)
    guarantor_ids = fields.Many2many('res.partner', 'lenka_operation_guarantor_rel', 'operation_id', 'partner_id', string='Avales')
    operation_type = fields.Selection([
        ('loan', 'Prestamo'),
        ('financing', 'Financiamiento'),
        ('lease', 'Arrendamiento'),
    ], string='Tipo de operacion', required=True, default='financing', tracking=True)
    product_id = fields.Many2one('product.product', string='Equipo / Producto')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)
    date = fields.Date(required=True, default=fields.Date.context_today)
    principal_amount = fields.Monetary(string='Monto / Valor', required=True, tracking=True)
    down_payment = fields.Monetary(string='Prima', default=0.0)
    financed_amount = fields.Monetary(string='Monto financiado', compute='_compute_financed_amount', store=True)
    interest_rate = fields.Float(string='Tasa de interes (%)', required=True, tracking=True)
    rate_period = fields.Selection([('monthly', 'Mensual'), ('annual', 'Anual')], default='monthly', required=True)
    term_months = fields.Integer(string='Plazo (meses)', required=True, default=12)
    first_payment_date = fields.Date(string='Primera cuota')
    calculation_method = fields.Selection([
        ('level', 'Cuota nivelada'),
        ('balance', 'Interes sobre saldo'),
        ('interest_only', 'Solo intereses + capital al final'),
        ('balloon', 'Cuota bomba / extraordinarios'),
        ('custom', 'Plan personalizado'),
    ], string='Metodo de calculo', required=True, default='level')
    residual_purchase_percent = fields.Float(string='Opcion de compra (%)', default=0.0)
    residual_purchase_amount = fields.Monetary(string='Opcion de compra', compute='_compute_residual_purchase_amount', store=True)
    state = fields.Selection([
        ('draft', 'Borrador'), ('review', 'En revision'), ('approved', 'Aprobada'),
        ('contracted', 'Contratada'), ('active', 'Activa'), ('done', 'Finalizada'),
        ('rejected', 'Rechazada'), ('cancelled', 'Cancelada')
    ], default='draft', tracking=True)
    schedule_line_ids = fields.One2many('lenka.amortization.line', 'operation_id', string='Tabla de amortizacion', copy=False)
    funding_line_ids = fields.One2many('lenka.funding.line', 'operation_id', string='Fondeo')
    guarantee_ids = fields.One2many('lenka.guarantee', 'operation_id', string='Garantias')
    notes = fields.Text(string='Observaciones')

    @api.depends('principal_amount', 'down_payment')
    def _compute_financed_amount(self):
        for rec in self:
            rec.financed_amount = max(rec.principal_amount - rec.down_payment, 0.0)

    @api.depends('principal_amount', 'residual_purchase_percent')
    def _compute_residual_purchase_amount(self):
        for rec in self:
            rec.residual_purchase_amount = rec.principal_amount * rec.residual_purchase_percent / 100.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('lenka.financial.operation') or 'Nuevo'
        return super().create(vals_list)

    @api.constrains('principal_amount', 'down_payment', 'interest_rate', 'term_months')
    def _check_financial_values(self):
        for rec in self:
            if rec.principal_amount <= 0:
                raise ValidationError(_('El monto debe ser mayor que cero.'))
            if rec.down_payment < 0 or rec.down_payment > rec.principal_amount:
                raise ValidationError(_('La prima debe estar entre cero y el valor de la operacion.'))
            if rec.interest_rate < 0:
                raise ValidationError(_('La tasa no puede ser negativa.'))
            if rec.term_months <= 0:
                raise ValidationError(_('El plazo debe ser mayor que cero.'))

    def action_generate_schedule(self):
        for rec in self:
            if rec.calculation_method == 'custom':
                continue
            rec.schedule_line_ids.unlink()
            principal = rec.financed_amount
            n = rec.term_months
            monthly_rate = rec.interest_rate / 100.0 if rec.rate_period == 'monthly' else rec.interest_rate / 1200.0
            balance = principal
            if rec.calculation_method in ('level', 'balance'):
                payment = principal / n if not monthly_rate else principal * monthly_rate / (1 - (1 + monthly_rate) ** -n)
            elif rec.calculation_method == 'interest_only':
                payment = principal * monthly_rate
            else:
                payment = principal / n if n else 0.0
            payment_date = rec.first_payment_date or rec.date
            lines = []
            for number in range(1, n + 1):
                interest = balance * monthly_rate
                if rec.calculation_method == 'interest_only':
                    capital = principal if number == n else 0.0
                    total = interest + capital
                else:
                    capital = min(max(payment - interest, 0.0), balance)
                    if number == n:
                        capital = balance
                    total = capital + interest
                end_balance = max(balance - capital, 0.0)
                lines.append((0, 0, {
                    'sequence': number,
                    'date': payment_date,
                    'opening_balance': balance,
                    'capital': capital,
                    'interest': interest,
                    'payment': total,
                    'closing_balance': end_balance,
                }))
                balance = end_balance
                payment_date = fields.Date.add(payment_date, months=1)
            rec.schedule_line_ids = lines
        return True

    def action_convert_to_application(self):
        self.write({'is_quote': False, 'state': 'review'})
        return True


class LenkaAmortizationLine(models.Model):
    _name = 'lenka.amortization.line'
    _description = 'Linea de Amortizacion Lenka'
    _order = 'sequence'

    operation_id = fields.Many2one('lenka.financial.operation', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='operation_id.currency_id')
    sequence = fields.Integer(string='#', required=True)
    date = fields.Date(string='Fecha', required=True)
    opening_balance = fields.Monetary(string='Saldo inicial')
    capital = fields.Monetary(string='Capital')
    interest = fields.Monetary(string='Interes')
    extra_charge = fields.Monetary(string='Otros cargos')
    payment = fields.Monetary(string='Cuota')
    closing_balance = fields.Monetary(string='Saldo final')


class LenkaFundingLine(models.Model):
    _name = 'lenka.funding.line'
    _description = 'Fuente de Fondeo Lenka'

    operation_id = fields.Many2one('lenka.financial.operation', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='operation_id.currency_id')
    source_type = fields.Selection([
        ('own', 'Capital propio'), ('cash', 'Efectivo'), ('bank', 'Cuenta bancaria'),
        ('bank_loan', 'Prestamo bancario'), ('credit_card', 'Tarjeta de credito empresarial'),
        ('investor', 'Inversionista / depositante'), ('third_party', 'Fondos de terceros'), ('other', 'Otro')
    ], string='Fuente', required=True)
    partner_id = fields.Many2one('res.partner', string='Banco / Inversionista / Tercero')
    reference = fields.Char(string='Cuenta / Instrumento / Referencia')
    amount = fields.Monetary(string='Monto', required=True)
    cost_rate = fields.Float(string='Costo financiero (%)')
    cost_period = fields.Selection([('monthly', 'Mensual'), ('annual', 'Anual')], default='annual')


class LenkaGuarantee(models.Model):
    _name = 'lenka.guarantee'
    _description = 'Garantia Lenka'

    operation_id = fields.Many2one('lenka.financial.operation', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='operation_id.currency_id')
    guarantee_type = fields.Selection([
        ('equipment', 'Equipo financiado'), ('vehicle', 'Vehiculo'), ('property', 'Inmueble'),
        ('labor', 'Derechos laborales'), ('deposit', 'Deposito'), ('other', 'Otra')
    ], string='Tipo', required=True)
    owner_id = fields.Many2one('res.partner', string='Propietario')
    description = fields.Char(string='Descripcion', required=True)
    declared_value = fields.Monetary(string='Valor declarado')
    appraisal_value = fields.Monetary(string='Valor de avaluo')
    serial_reference = fields.Char(string='Serie / VIN / Matricula')
    state = fields.Selection([
        ('proposed', 'Propuesta'), ('accepted', 'Aceptada'), ('active', 'Vigente'),
        ('released', 'Liberada'), ('executed', 'Ejecutada')
    ], default='proposed')
