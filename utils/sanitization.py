import html
import re

def sanitize_string(value:str) -> str:
    #sanitize a string to prevent XSS and other injection attacks

    if not isinstance(value,str):
        value = str(value)
    # prevent XSS 
    value = html.escape(value)
    # remove script tags
    value = re.sub(r"&lt;script.*?&gt;.*?&lt;/script&gt;","",value,flags=re.DOTALL)
    # remove null bytes
    value = value.replace("\0","")
    return value