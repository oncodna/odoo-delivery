{
    "name": "Easypost Delivery (complete module for all carriers)",
    "version": "2.0",
    "depends": ["delivery"],
    'external_dependencies': {'python': ['easypost']},
    'author': 'OncoDNA',
    'category': 'Stock',
    'license': 'AGPL-3',
    "description": """
        """,
    'demo': [],
    'data': [
        'views/settings.xml',
        'views/carrier.xml',
        'views/picking.xml',
        'views/product.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
