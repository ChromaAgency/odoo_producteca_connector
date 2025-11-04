from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class QueueJob(models.Model):
    _inherit = 'queue.job'

    @api.model
    def cron_cleanup_failed_pricelist_jobs(self):
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        failed_jobs = self.search([
            ('retry', '>=', 5),
            ('model_name', '=', 'product.pricelist'),
            ('date_done', '!=', False),
            ('date_done', '<', one_hour_ago),
            ('state', '=', 'failed')
        ])
        
        if failed_jobs:
            job_count = len(failed_jobs)
            _logger.info(f"Cleaning up {job_count} failed product.pricelist jobs older than 1 hour with 5+ retries")            
            failed_jobs.sudo().unlink()            
            _logger.info(f"Successfully cleaned up {job_count} failed product.pricelist jobs")
        
        return True