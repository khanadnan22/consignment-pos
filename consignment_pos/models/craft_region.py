from odoo import models, fields


class CraftRegion(models.Model):
    _name        = 'craft.region'
    _description = 'Craft Origin Region'
    _rec_name    = 'name'

    name             = fields.Char('Region Name', required=True)
    state            = fields.Char('State / Province')
    latitude         = fields.Float('Latitude',  digits=(10, 6))
    longitude        = fields.Float('Longitude', digits=(10, 6))
    craft_tradition  = fields.Text('Craft Tradition Description')
    designer_ids     = fields.One2many('res.partner', 'craft_region_id', string='Designers')
    designer_count   = fields.Integer('Designers', compute='_compute_designer_count')

    def _compute_designer_count(self):
        for rec in self:
            rec.designer_count = len(rec.designer_ids.filtered('is_consignor'))
