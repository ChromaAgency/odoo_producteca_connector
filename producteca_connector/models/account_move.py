from odoo import fields,models

class AccountMove(models.Model):
    _inherit = 'account.move'
   
    producteca_payment_state = fields.Selection([
        ('pending', 'Pending'),
        ('on_delivery', 'On Delivery'),
        ('in_process', 'In Process'),
        ('in_mediation', 'In Mediation'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('charged_back', 'Charged Back')
    ], string='Estado del pago')

    producteca_payment_data = fields.Text(string='Datos del pago de producteca')