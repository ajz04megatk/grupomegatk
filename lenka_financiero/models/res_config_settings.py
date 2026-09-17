from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lenka_card_fee_rate = fields.Float(
        string='Comision de tarjeta (%)',
        config_parameter='lenka_financiero.card_fee_rate',
        default=3.5,
        help='Porcentaje retenido por el banco/POS en pagos con tarjeta. El neto despues de esta comision es el monto que se aplica a la deuda del cliente.'
    )
