from odoo import models, fields, api


class ProductecaQueue(models.Model):
    _name = 'producteca.queue'
    _description = 'Producteca Queue'

    active = fields.Boolean(string='Active', default=True)
    producteca_account_id = fields.Many2one('producteca.account', string='Producteca Account')
    producteca_body = fields.Text(string='Producteca Body')
    producteca_method = fields.Selection([
        ('get', 'Get'),
        ('post', 'Post'),
        ('put', 'Put'),
        ('delete', 'Delete')
    ], string='Producteca Method')
    producteca_url = fields.Char(string='Producteca URL')
    producteca_response = fields.Text(string='Producteca Response')
    
