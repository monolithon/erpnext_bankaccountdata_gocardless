# Expenses © 2024
# Author:  Ameen Ahmed
# Company: Level Up Marketing & Software Development Services
# Licence: Please refer to LICENSE file


# [G Settings]
def is_valid_secret_id(data):
    if data and isinstance(data, str) and len(data) == 36:
        import re
        
        rgx = r"([a-z0-9]{8})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{4})-([a-z0-9]{12})"
        if re.match(rgx, data, flags=re.I):
            return True
    
    return False


# [G Settings]
def is_valid_secret_key(data):
    if data and isinstance(data, str) and len(data) == 128:
        import re
        
        if re.match(r"([a-z0-9]+)", data, flags=re.I):
            return True
    
    return False