from odoo import models, fields, api

# ==========================================
# WOW FACTOR 3: MANUFACTURING (MRP)
# ==========================================
class MrpBom(models.Model):
    """Extends standard Bill of Materials to detect consigned raw materials."""
    _inherit = 'mrp.bom'

    contains_consignment_materials = fields.Boolean(
        string="Contains Consigned Materials", 
        compute='_compute_consignment_materials', store=True,
        help="Flags if this manufactured product relies on designer consignment components."
    )

    @api.depends('bom_line_ids.product_id')
    def _compute_consignment_materials(self):
        for bom in self:
            bom.contains_consignment_materials = any(
                line.product_id.product_tmpl_id.is_consignment for line in bom.bom_line_ids
            )


# ==========================================
# WOW FACTOR 5: SUBSCRIPTIONS / RENTAL FEES
# ==========================================
class ResPartnerRental(models.Model):
    _inherit = 'res.partner'

    monthly_gallery_fee = fields.Float(
        string='Monthly Gallery Display Fee ($)',
        help='A fixed shelf-rental fee subtracted from the designer\'s monthly settlement.'
    )

class SettlementRecordRental(models.Model):
    _inherit = 'settlement.record'

    gallery_fee_deduction = fields.Float('Gallery Fee Deduction', readonly=True)

    def _aggregate_for_designer(self, designer_id, period_start, period_end, record=None):
        """Override to deduct the gallery rental fee from their payout."""
        # 1. Get original calculations
        vals = super()._aggregate_for_designer(designer_id, period_start, period_end, record=record)
        
        # 2. Subtract the rental fee if it is a full month (simplified for demo)
        designer = self.env['res.partner'].browse(designer_id)
        if designer.monthly_gallery_fee > 0:
            fee = designer.monthly_gallery_fee
            vals['gallery_fee_deduction'] = fee
            vals['payout_amount'] = vals['payout_amount'] - fee
            
            if record:
                record.write({
                    'gallery_fee_deduction': fee,
                    'payout_amount': vals['payout_amount']
                })
        return vals
