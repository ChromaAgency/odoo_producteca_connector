# -*- coding: utf-8 -*-
{
    'name': "Producteca Odoo Conector",

    'summary': """
        Conector del servicio de Producteca - Odoo""",

    'description': """
        Conector del servicio de Producteca - Odoo
    """,

    'author': "Chroma",
    'website': "https://portal.chroma.agency/",
    "license": "AGPL-3",

    'category': 'Uncategorized',
    'version': '1.0',

    'depends': ['base','stock','sale','sale_management','contacts','product_brand','website_sale', 'brand','l10n_ar'],

    'data': [
        'data/producteca_menu.xml', 
        'views/producteca.account.views.xml', 
        'views/producteca.queue.views.xml',
        'views/producteca.connections.views.xml',
        'data/ir.cron.xml',
        'views/product.template.xml',
        'views/stock.warehouse.xml',
        'wizards/import_producteca_product.xml',
        'wizards/import_producteca_saleorders.xml',
        'views/sale.order.xml',
        'views/sale.order.cart.xml',
        'security/ir.model.access.csv',
        'security/res.groups.xml',
        'data/records.xml',
        'views/account.journal.xml',
        'views/account.move.xml',
    ],
    'demo': [],
    'application': True,
    'installable': True,
    'price': 249.99,
    'currency': 'USD',
}