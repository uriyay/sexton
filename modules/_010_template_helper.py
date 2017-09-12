import re
from construct import *

def get_offset_of(parsed_object, path):
    #We can just return the object _pfp__offset
    #but we need to find the object
    return get_from_template(parsed_object, path)._pfp__offset

def get_size_of(parsed_object, path):
    return get_from_template(parsed_object, path)._pfp__width()

def get_from_template(template_obj, keys_list):
    current = template_obj
    while keys_list:
        key = keys_list[0]
        keys_list = keys_list[1:]
        if re.match('\[\d+\]', key):
            current = current[int(key[1:-1])]
        else:
            current = getattr(current, key)
    return current

def set_template_value(template_obj, keys_list, value):
    operator.setitem(get_from_template(template_obj, keys_list[:-1]), #get the lowest dict object
                     keys_list[-1], #pass the lowest key (which leads to a value)
                     value)

