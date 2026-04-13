from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommissionConfig(models.Model):
    _name        = 'commission.config'
    _description = 'Commission Configuration'
    _rec_name    = 'designer_id'

    designer_id           = fields.Many2one('res.partner', string='Designer', required=True,
        domain=[('is_consignor', '=', True)], ondelete='cascade')
    commission_percentage = fields.Float(string='Commission Rate (%)', required=True, digits=(5, 2))
    date_from             = fields.Date(string='Valid From')
    date_to               = fields.Date(string='Valid To')
    settlement_period     = fields.Selection([
        ('weekly',    'Weekly'),
        ('biweekly',  'Bi-Weekly'),
        ('monthly',   'Monthly'),
    ], string='Settlement Period', default='weekly')

    use_tiered = fields.Boolean(string='Use Tiered Commission', default=False)
    tier_ids   = fields.One2many('commission.tier', 'config_id', string='Tiers')

    notes = fields.Text(string='Notes')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for r in self:
            if r.date_from and r.date_to and r.date_to < r.date_from:
                raise ValidationError('Valid To must be on or after Valid From.')


class CommissionTier(models.Model):
    _name        = 'commission.tier'
    _description = 'Commission Tier'

    config_id        = fields.Many2one('commission.config', string='Commission Config', required=True, ondelete='cascade')
    label            = fields.Char(string='Tier Label', required=True)
    min_sales_amount = fields.Float(string='Min Sales Amount', required=True)
    tier_percentage  = fields.Float(string='Commission Rate (%)', required=True, digits=(5, 2))

