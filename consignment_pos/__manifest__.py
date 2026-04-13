{
    'name': 'Consignment POS',
    'version': '19.0.9.0.0',
    'summary': 'Designer Clothing Consignment POS — v9 with 4 new features',
    'description': (
        'v9 additions: '
        '(1) Tiered commission — volume thresholds reduce store cut as designer sells more. '
        '(2) Settlement Dispute Workflow — designer raises disputes from portal, admin resolves via wizard. '
        '(3) Product Submission Portal — designers self-submit products for admin approval. '
        '(4) Craft Region Map — Leaflet.js interactive map of Indian craft traditions on /craft-map. '
        'Previous: dual-channel POS+online settlement, KPI dashboard, low-stock alerts, '
        'SHG social equity tiers, designer portal, PDF reports.'
    ),
    'author': 'Adnan Khan (22C21029)',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'account', 'mail', 'portal', 'website', 'website_sale', 'web', 'sale', 'stock', 'purchase', 'mrp', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/designer_views.xml',
        'views/commission_views.xml',
        'views/settlement_views.xml',
        'views/analytics_views.xml',
        'views/dashboard_views.xml',
        'views/website_menu.xml',
        'views/product_submission_views.xml',
        'views/pos_additional_menus.xml',
        'views/order_payment_views.xml',
        'views/pos_order_views.xml',
        'views/pos_config_kanban_extension.xml',
        'wizard/settlement_wizard_views.xml',
        'reports/settlement_report.xml',
        'data/mail_template.xml',
        'data/cron_settlement.xml',
        'data/cron_low_stock.xml',
        'data/demo_data.xml',
        'report/report_settlement.xml',
        'report/report_designer_summary.xml',
        'templates/portal_my_settlements.xml',
        'templates/portal_submissions.xml',
        'templates/website_consignment.xml',
        'templates/website_designers.xml',
        'templates/website_craft_map.xml',
        'templates/website_designer_apply.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'consignment_pos/static/src/js/consignment_pos.js',
            'consignment_pos/static/src/xml/consignment_pos.xml',
        ],
        'web.assets_frontend': [
            'consignment_pos/static/src/css/website_consignment.css',
        ],
        'web.assets_backend': [
            'consignment_pos/static/src/css/dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
