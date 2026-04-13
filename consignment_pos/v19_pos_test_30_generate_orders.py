from datetime import datetime

print("Looking for Consignment Products...")
products = env['product.product'].sudo().search([('is_consignment', '=', True)], limit=8)
if not products:
    print("ERROR: No consignment products found!")
    env.cr.rollback()
    exit()

print("Finding POS Session...")
session = env['pos.session'].sudo().search([('state', '=', 'opened')], limit=1)
if not session:
    print("No open session found. Trying any session...")
    session = env['pos.session'].sudo().search([], limit=1)
    if not session:
        pos_config = env['pos.config'].sudo().search([], limit=1)
        if not pos_config:
            pos_config = env['pos.config'].sudo().create({'name': 'Demo Shop'})
        # Create session manually to bypass UI checks
        session = env['pos.session'].sudo().create({
            'config_id': pos_config.id,
            'user_id': env.user.id,
        })
print(f"Using session: {session.name}")

print("Generating Orders...")
partner = env['res.partner'].sudo().search([('name', 'ilike', 'Deco Addict')], limit=1)
if not partner:
    partner = env['res.partner'].sudo().search([], limit=1)

for i, product in enumerate(products):
    order = env['pos.order'].sudo().create({
        'session_id': session.id,
        'partner_id': partner.id,
        'amount_tax': 0,
        'amount_total': product.list_price,
        'amount_paid': product.list_price,
        'amount_return': 0,
        'lines': [(0, 0, {
            'product_id': product.id,
            'qty': 1,
            'price_unit': product.list_price,
            'price_subtotal': product.list_price,
            'price_subtotal_incl': product.list_price,
            'tax_ids': [(6, 0, [])]
        })]
    })
    
    # Add payment
    payment_method = env['pos.payment.method'].sudo().search([], limit=1)
    if not payment_method:
        payment_method = env['pos.payment.method'].sudo().create({'name': 'Cash'})
        
    env['pos.payment'].sudo().create({
        'pos_order_id': order.id,
        'payment_method_id': payment_method.id,
        'amount': product.list_price,
    })
    order.sudo().action_pos_order_paid()
    print(f"Created order for {product.name}")

print("Syncing has_consignment fields!")
env['pos.order.line'].sudo().search([])._compute_consignment_fields()
env['pos.order'].sudo().search([])._compute_has_consignment()

print("Orders generated successfully!")
env.cr.commit()
