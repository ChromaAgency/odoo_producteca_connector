from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    producteca_payment_method = fields.Selection([
        ('cash', 'Efectivo'),
        ('credit_card', 'Tarjeta de Crédito'),
        ('bank_loan', 'Préstamo Bancario'),
        ('bank_transfer', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('mercadopago', 'Mercado Pago'),
        ('debit_card', 'Tarjeta de Débito'),
        ('bank_deposit', 'Depósito Bancario'),
        ('dinero_mail', 'DineroMail'),
        ('ticket', 'Ticket'),
        ('decidir', 'Decidir'),
        ('loyalty_points', 'Puntos de Fidelidad'),
        ('paypal', 'PayPal'),
        ('paypal_plus', 'PayPal Plus'),
        ('atm', 'ATM'),
    ], string='Método de diario de pago')

    