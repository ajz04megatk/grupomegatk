{
    'name': 'App Financiero Lenka',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Finance',
    'summary': 'Cotizaciones, prestamos, financiamientos, arrendamientos y fondeo de Inversiones Lenka',
    'author': 'Grupo MEGATK',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account', 'product'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/lenka_financial_views.xml',
        'views/lenka_menu.xml',
    ],
    'application': True,
    'installable': True,
}
