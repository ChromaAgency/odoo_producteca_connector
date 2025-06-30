from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    producteca_id = fields.Char(string='Producteca ID')

    def _create_producteca_partner(self, producteca_id, account):
        client = account.get_client()
        sale_order = client.SaleOrder.get(producteca_id)
        contact = sale_order.contact
        if not contact:
            contact_ref = self.env.ref('producteca_connector.producteca_contact')
            return contact_ref
        partner = self.env['res.partner'].sudo().search([('producteca_id', '=', str(contact.id))], limit=1)
        if partner:
            return partner
        company = self.env['res.partner'].sudo().search([('vat', '=', contact.billingInfo.docNumber), ('parent_id', '=', False)], limit=1)
        if not company:
            identification = self.env['l10n_latam.identification.type'].sudo().search([('name', '=', contact.billingInfo.docType)], limit=1)
            responsibility = self.env['l10n_ar.afip.responsibility.type'].sudo().search([('name', 'ilike', contact.billingInfo.taxPayerType)], limit=1)
            state = self.env['res.country.state'].sudo().search([('name', '=', contact.billingInfo.state)], limit=1)
            company_info = {
                'name': contact.billingInfo.businessName,
                'l10n_latam_identification_type_id': identification.id,
                'l10n_ar_afip_responsibility_type_id': responsibility.id,
                'vat': contact.billingInfo.docNumber,
                'street': f'{contact.billingInfo.streetName} {contact.billingInfo.streetNumber}',
                'zip': contact.billingInfo.zipCode,
                'city': contact.billingInfo.city,
                'state_id': state.id,
                'country_id': self.env.ref('base.ar').id
            }
            company = self.env['res.partner'].sudo().create(company_info)
        contact_info = {
            'name': contact.name,
            'producteca_id': str(contact.id),
            'email': contact.mail,
            'phone': contact.phoneNumber,
            'parent_id': company.id
        }
        partner = self.env['res.partner'].sudo().create(contact_info)
        return partner
