from odoo import models, fields
from odoo.api import ondelete

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    producteca_payment_method = fields.Selection([
        ('Cash', 'Efectivo'),
        ('CreditCard', 'Tarjeta de Crédito'),
        ('BankLoan', 'Préstamo Bancario'),
        ('BankTransfer', 'Transferencia Bancaria'),
        ('Check', 'Cheque'),
        ('MercadoPago', 'Mercado Pago'),
        ('DebitCard', 'Tarjeta de Débito'),
        ('BankDeposit', 'Depósito Bancario'),
        ('DineroMail', 'DineroMail'),
        ('Ticket', 'Ticket'),
        ('Decidir', 'Decidir'),
        ('LoyaltyPoints', 'Puntos de Fidelidad'),
        ('PayPal', 'PayPal'),
        ('PayPalPlus', 'PayPal Plus'),
        ('Atm', 'ATM'),
    ], string='Método de diario de pago', ondelete="set null")

    