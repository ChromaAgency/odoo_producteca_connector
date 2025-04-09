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

    'depends': ['base','stock','sale','sale_management','contacts'],

    'data': [
        'data/producteca_menu.xml', 
        'views/producteca_account_views.xml', 
        'views/producteca_queue_views.xml',
        'views/producteca_connections_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
}