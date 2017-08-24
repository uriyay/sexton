import re
from construct import *

def get_offset_of(struct, container, path):
    if type(struct) is not Renamed:
        struct = Renamed('struct', struct)
    offset = 0
    if re.search('\[\d\]', path[0]):
        #got index in path, so the container is list
        index = int(path[0][1:-1])
        #get the corresponding struct is actually an Array or something
        struct = struct.subcon
        #increment the offset
        offset += sum(len(struct.subcon.build(container[x])) for x in range(index))
        #get the container
        container = container[index]
        #increment the path
        path = path[1:]
        if not path:
            return offset

    for key,value in container.items():
        if key == path[0]:
            #increment the path
            path = path[1:]
            if not path:
                return offset
            subcon = [x for x in struct.subcon.subcons if x.name == key][0]
            return offset + get_offset_of(subcon, value, path)
        else:
            subcon = [x for x in struct.subcon.subcons if x.name == key][0]
            offset += len(subcon.build(value, context=container))

def get_size_of(struct, container, path):
    if type(struct) is not Renamed:
        struct = Renamed('struct', struct)
    if re.search('\[\d\]', path[0]):
        #got index in path, so the container is list
        index = int(path[0][1:-1])
        #get the corresponding struct is actually an Array or something
        struct = struct.subcon
        #get the container
        container = container[index]
        #increment the path
        path = path[1:]
        if not path:
            return len(struct.subcon.build(container))

    for key,value in container.items():
        if key == path[0]:
            #increment the path
            path = path[1:]
            subcon = [x for x in struct.subcon.subcons if x.name == key][0]
            if not path:
                return len(subcon.build(value, context=container))
            return get_size_of(subcon, value, path)

def get_from_dict(dict_obj, keys_list):
    return reduce(operator.getitem, keys_list, dict_obj)

def set_dict_value(dict_obj, keys_list, value):
    operator.setitem(get_from_dict(dict_obj, keys_list[:-1]), #get the lowest dict object
                     keys_list[-1], #pass the lowest key (which leads to a value)
                     value)

