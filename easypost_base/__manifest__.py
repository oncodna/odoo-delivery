{
    "name": "Easypost Delivery (base module)",
    "version": "1.0",
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
    ],
    'installable': True,
    'auto_install': False,
}
