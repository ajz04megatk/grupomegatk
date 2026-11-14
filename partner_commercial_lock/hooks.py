from odoo import Command

# Exact accounts already verified in this Odoo instance. No company/ACL changes.
ASSIGNMENT_MANAGERS = (
    (60, 'lmoran@megatk.com'),
    (62, 'msauceda@megatk.com'),
    (126, 'dvasquez@megatk.com'),
    (45, 'erodriguez@megatk.com'),
    (553, 'administracion@megatk.com'),
    (63, 'nfuentes@meditekhn.com'),
    (68, 'yalvarado@megatk.com'),
    (67, 'facturacion@megatk.com'),
)


def grant_verified_managers(env):
    group = env.ref('partner_commercial_lock.group_manage_commercial_assignment')
    users = env['res.users'].sudo()
    for uid, login in ASSIGNMENT_MANAGERS:
        user = users.search([('id', '=', uid), ('login', '=', login), ('active', '=', True)], limit=1)
        if user and set(user.company_ids.ids) & {8, 9} and group not in user.groups_id:
            user.write({'groups_id': [Command.link(group.id)]})


def post_init_hook(env):
    grant_verified_managers(env)
