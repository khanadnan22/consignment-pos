pos = env['pos.config'].search([], limit=1)
if pos:
    open_sessions = env['pos.session'].search([('config_id', '=', pos.id), ('state', '!=', 'closed')])
    for session in open_sessions:
        session.action_pos_session_closing_control()
    
    pos.write({'module_pos_restaurant': False})
    print("Fixed POS Config to be Retail!")
env.cr.commit()
