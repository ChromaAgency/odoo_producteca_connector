from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    producteca_id = fields.Char(string='Producteca ID')

    def _create_producteca_partner(self, producteca_id, account):
        client = account.get_client()
        sale_order = client.SalesOrder.get(producteca_id)
        contact = sale_order.contact
        if not contact:
            contact_ref = self.env.ref('producteca_connector.producteca_contact')
            return contact_ref
        partner = self.env['res.partner'].sudo().search([('producteca_id', '=', str(contact.id))], limit=1)
        if partner:
            return partner
        company = self.env['res.partner'].sudo().search([('vat', '=', contact.billing_info.doc_number), ('parent_id', '=', False)], limit=1)
        if not company and contact.billing_info.doc_number:
            identification = None
            responsibility = None
            
            if 'l10n_latam.identification.type' in self.env:
                identification = self.env['l10n_latam.identification.type'].sudo().search([('name', '=', contact.billing_info.doc_type)], limit=1)
            
            if 'l10n_ar.afip.responsibility.type' in self.env:
                responsibility = self.env['l10n_ar.afip.responsibility.type'].sudo().search([('name', 'ilike', contact.billing_info.tax_payer_type)], limit=1)
            
            state = self.env['res.country.state'].sudo().search([('name', '=', contact.billing_info.state)], limit=1)
            company_info = {
                'name': contact.billing_info.business_name if contact.billing_info.business_name else contact.name,
                'vat': contact.billing_info.doc_number,
                'street': f'{contact.billing_info.street_name} {contact.billing_info.street_number}',
                'zip': contact.billing_info.zip_code,
                'city': contact.billing_info.city,
                'state_id': state.id,
                'country_id': self.env.ref('base.ar').id,
                'company_type': 'company',
            }
            
            if identification:
                company_info['l10n_latam_identification_type_id'] = identification.id
            if responsibility:
                company_info['l10n_ar_afip_responsibility_type_id'] = responsibility.id
            
            company = self.env['res.partner'].sudo().create(company_info)
        contact_info = {
            'name': contact.name,
            'producteca_id': str(contact.id),
            'email': contact.mail,
            'phone': contact.phone_number,
            
        }
        if company:
            contact_info['parent_id'] = company.id
        partner = self.env['res.partner'].sudo().create(contact_info)
        return partner
