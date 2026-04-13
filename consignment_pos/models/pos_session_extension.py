from odoo import models, fields


class PosSession(models.Model):

    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if 'commission.config' not in result:
            result.append('commission.config')
        return result

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'] += ['is_consignment', 'designer_id']
        return result

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        result['search_params']['fields'] += ['is_consignor', 'commission_rate']
        return result

    def _loader_params_commission_config(self):
        return {'search_params': {
            'domain': [],
            'fields': ['designer_id', 'commission_percentage', 'date_from', 'date_to'],
        }}

    def _get_pos_ui_commission_config(self, params):
        today = fields.Date.today()
        domain = [
            '|', ('date_from', '=', False), ('date_from', '<=', today),
            '|', ('date_to',   '=', False), ('date_to',   '>=', today),
        ]
        return self.env['commission.config'].search_read(
            domain,
            params['search_params']['fields'],
        )
