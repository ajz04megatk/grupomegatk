{
    "name": "MEGATK - Protección del representante comercial",
    "version": "18.0.2.0.0",
    "category": "Sales",
    "license": "LGPL-3",
    "summary": "Protege el comercial del contacto y los responsables de cotizaciones y líneas",
    "depends": ["base", "sale", "fields_megatk", "grupos_accesos"],
    "data": [
        "security/groups.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}
