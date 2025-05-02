# -*- coding: utf-8 -*-
{
    'name': "Producteca Odoo Conector",

    'summary': """
        Conector del servicio de Producteca - Odoo""",

    'description': """
        Conector del servicio de Producteca - Odoo
    """,

    'author': "Chroma",
    'website': "https://www.making.com.ar",

    'category': 'Uncategorized',
    'version': '1.0',

    'depends': ['base','stock','sale','sale_management','contacts','product_brand','website_sale', 'brand'],

    'data': [
        'data/producteca_menu.xml', 
        'views/producteca_account_views.xml', 
        'views/producteca_queue_views.xml',
        'views/producteca_connections_views.xml',
        'data/ir.cron.xml',
        'views/product_template.xml',
        'views/stock_warehouse.xml',
        'wizards/import_producteca_product.xml',
        'wizards/import_producteca_saleorders.xml',
        'views/sale.order.xml',
        'views/sale.order.cart.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
}