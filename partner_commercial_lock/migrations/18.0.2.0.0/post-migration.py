from odoo import api, SUPERUSER_ID
from odoo.addons.partner_commercial_lock.hooks import grant_verified_managers


def migrate(cr, version):
    grant_verified_managers(api.Environment(cr, SUPERUSER_ID, {}))
