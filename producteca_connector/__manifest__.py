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

    'category': 'Connector',
    'version': '1.0',
    'external_dependencies': {
        'python': [
            'producteca'
        ],
    },

    'depends': [
        'base', 'stock', 'sale', 'sale_management',
        'contacts', 'product_brand', 'website_sale', 'brand',
        'queue_job'
        ],

    'data': [
        'data/producteca_menu.xml',
        'views/producteca.account.views.xml',
        'views/producteca.connections.views.xml',
        'data/ir.cron.xml',
        'data/ir_actions_server.xml',
        'views/product.template.xml',
        'views/stock.warehouse.xml',
        'wizards/import_producteca_product.xml',
        'wizards/import_producteca_saleorders.xml',
        'wizards/update_producteca_product.xml',
        'views/sale.order.xml',
        'views/sale.order.cart.xml',
        'security/ir.model.access.csv',
        'security/res.groups.xml',
        'data/records.xml',
        'views/account.journal.xml',
        'views/account.move.xml',
        'views/product.pricelist.xml'
    ],
    'demo': [],
    'application': True,
    'installable': True,
    'price': 249.99,
    'currency': 'USD',
    'images': ['static/description/main_screenshot.gif', 'static/description/1.png', 'static/description/2.png'],
    'support': 'odooapps@chroma.agency',
    'live_test_url': 'https://portal.chroma.agency',
}