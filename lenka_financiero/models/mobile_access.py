from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class ResPartnerLenkaMobile(models.Model):
    _inherit = 'res.partner'

    def _check_mobile_manager(self):
        if not self.env.su and not self.env.user.has_group('lenka_financiero.group_lenka_manager'):
            raise AccessError(_('Solo un gerente de Lenka puede habilitar o deshabilitar el acceso movil.'))

    @api.model_create_multi
    def create(self, vals_list):
        if any('lenka_mobile_enabled' in vals or 'lenka_mobile_enabled_date' in vals for vals in vals_list):
            self._check_mobile_manager()
        return super().create(vals_list)

    def write(self, vals):
        if {'lenka_mobile_enabled', 'lenka_mobile_enabled_date'}.intersection(vals):
            self._check_mobile_manager()
        return super().write(vals)

    lenka_mobile_enabled = fields.Boolean(
        string='Acceso App Financiero Lenka',
        tracking=True,
        help='Habilita a este cliente para consultar su informacion financiera desde la app Lenka.',
    )
    lenka_mobile_enabled_date = fields.Datetime(string='Acceso Lenka habilitado el', readonly=True)
    lenka_mobile_user_id = fields.Many2one(
        'res.users',
        string='Usuario App Lenka',
        compute='_compute_lenka_mobile_user',
    )

    def _compute_lenka_mobile_user(self):
        Users = self.env['res.users'].sudo()
        for partner in self:
            user = Users.search([('partner_id', '=', partner.id)], limit=1)
            partner.lenka_mobile_user_id = user

    def action_enable_lenka_mobile(self):
        self._check_mobile_manager()
        group = self.env.ref('lenka_financiero.group_lenka_mobile_client')
        portal_group = self.env.ref('base.group_portal')
        Users = self.env['res.users'].sudo().with_context(active_test=False)
        for partner in self:
            if not partner.email or not partner.email.strip():
                raise ValidationError(_('El cliente debe tener un correo electronico antes de habilitar la app Lenka.'))
            user = Users.search([('partner_id', '=', partner.id)], limit=1)
            if not user:
                if Users.search([('login', '=ilike', partner.email.strip())], limit=1):
                    raise ValidationError(_('Este correo ya corresponde a otro usuario. Revise el contacto y la cuenta antes de habilitar el acceso.'))
                user = Users.with_context(no_reset_password=True).create({
                    'name': partner.name,
                    'login': partner.email.strip(),
                    'email': partner.email,
                    'partner_id': partner.id,
                    'company_id': self.env.company.id,
                    'company_ids': [(6, 0, [self.env.company.id])],
                    'groups_id': [(6, 0, [portal_group.id, group.id])],
                })
            else:
                if not user.active:
                    raise ValidationError(_('La cuenta del cliente esta archivada. Un administrador debe revisarla antes de habilitar la app.'))
                if self.env.company not in user.company_ids:
                    raise ValidationError(_('La cuenta no tiene autorizada la empresa seleccionada. Un administrador debe revisar sus empresas permitidas; habilitar la app no amplia esos permisos.'))
                # An internal operator must not be assigned the incompatible portal role.
                groups = [(4, group.id)]
                if user.share:
                    groups.append((4, portal_group.id))
                user.write({'groups_id': groups})
            partner.write({
                'lenka_mobile_enabled': True,
                'lenka_mobile_enabled_date': fields.Datetime.now(),
            })
        return True

    def action_disable_lenka_mobile(self):
        self._check_mobile_manager()
        group = self.env.ref('lenka_financiero.group_lenka_mobile_client')
        for partner in self:
            user = self.env['res.users'].sudo().search([('partner_id', '=', partner.id)], limit=1)
            if user:
                user.write({'groups_id': [(3, group.id)]})
            partner.lenka_mobile_enabled = False
        return True
