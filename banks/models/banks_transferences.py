# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Vittbankstransferences(models.Model):
    _name = 'banks.transferences'
    _inherit = ['mail.thread']
    _description = "Transferencias entre Bancos"

    def get_sequence(self):
        if self.journal_id_out:
            for seq in self.journal_id_out.secuencia_ids:
                if seq.move_type == 'transference_banks':
                    return seq.id

    def update_seq(self):
        deb_obj = self.env["banks.transferences"].search([('state', '=', 'draft')])
        n = ""
        for seq in self.journal_id_out.secuencia_ids:
            if seq.move_type == 'transference_banks':
                n = seq.prefix + '%%0%sd' % seq.padding % (seq.number_next_actual + 1)
        for db in deb_obj:
            db.write({'number': n})

    def get_msg_number(self):
        if self.journal_id_out and self.state == 'draft':
            flag = False
            for seq in self.journal_id_out.secuencia_ids:
                if seq.move_type == 'transference_banks':
                    self.number_calc = seq.prefix + '%%0%sd' % seq.padding % seq.number_next_actual
                    flag = True
            if not flag:
                self.msg = "No existe numeración para este banco, verifique la configuración"
                self.number_calc = ""
            else:
                self.msg = ""

    def get_currency(self):
        return self.env.user.company_id.currency_id.id

    journal_id_out = fields.Many2one("account.journal", "De Banco", required=True, domain="[('type', 'in',['bank'])]")
    journal_id_in = fields.Many2one("account.journal", "A Banco", required=True, domain="[('type', 'in',['bank'])]")
    date = fields.Date(string="Fecha", help="Fecha efectia de transacción", required=True)
    total = fields.Float(string='Total', required=True)
    memo = fields.Text(string="Descripción", required=True)
    currency_id = fields.Many2one("res.currency", "Moneda", default=get_currency)
    state = fields.Selection([('draft', 'Borrador'), ('validated', 'Validado'), ('anulated', "Anulado")], 
    	string="Estado", default='draft')
    number = fields.Char("Número")
    msg = fields.Char("Error de configuración", compute=get_msg_number)
    number_calc = fields.Char("Número de Transacción", compute=get_msg_number)
    move_id = fields.Many2one('account.move', 'Apunte Contable', readonly=True)
    company_id = fields.Many2one("res.company", "Empresa", required=True)
    es_moneda_base = fields.Boolean("Es moneda base")

    @api.onchange("journal_id_out")
    def onchangejournal(self):
        self.get_msg_number()

    @api.multi
    def action_validate(self):
        if not self.number_calc:
            raise Warning(_("El banco no cuenta con configuraciones/parametros para registrar débitos bancarios"))
        if self.total < 0:
            raise Warning(_("El total debe de ser mayor que cero"))

        self.write({'state': 'validated'})
        self.number = self.env["ir.sequence"].search([('id', '=', self.get_sequence())]).next_by_id()
        self.write({'move_id': self.generate_asiento()})
        self.update_seq()

    def generate_asiento(self):
        account_move = self.env['account.move']
        lineas = []
        vals_haber = {
            'debit': 0.0,
            'credit': self.total,
            'amount_currency': 0.0,
            'name': self.memo,
            'account_id': self.journal_id_out.default_credit_account_id.id,
            'date': self.date,
        }
        vals_debe = {
            'debit': self.total,
            'credit': 0.0,
            'amount_currency': 0.0,
            'name': self.memo,
            'account_id': self.journal_id_in.default_credit_account_id.id,
            'date': self.date,
        }
        lineas.append((0, 0, vals_debe))
        lineas.append((0, 0, vals_haber))
        values = {
            'journal_id': self.journal_id_out.id,
            'date': self.date,
            'ref': self.memo,
            'line_ids': lineas,
            'state': 'posted',
        }
        id_move = account_move.create(values)
        id_move.write({'name': str(self.number)})
        return id_move.id