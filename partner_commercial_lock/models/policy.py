"""Commercial assignments require a dedicated grant, not a generic Sales role."""

# Explicitly excluded from this rollout. This preserves existing behavior;
# no group, ACL or company is added to the exempt account.
EXEMPT_PRINCIPALS = ((535, 'cdiaz@megatk.com'),)


def assignment_locked(env):
    groups = set(env.user.sudo().groups_id.ids)
    denied = env.ref('partner_commercial_lock.group_no_reassign_partner_commercial', raise_if_not_found=False)
    if denied and denied.id in groups:
        return True
    if (env.uid, env.user.sudo().login) in EXEMPT_PRINCIPALS:
        return False
    if env.user.has_group('base.group_system'):
        return False
    allowed = env.ref('partner_commercial_lock.group_manage_commercial_assignment', raise_if_not_found=False)
    return not (allowed and allowed.id in groups)
