#description: this is an example for a construct struct that can be used in sexton for parsing
#note that there must be defined a main_struct as the struct that you want to parse, but you can assign to it your struct
from construct import *

QwertyFile = Struct('magic' / Bytes(3),
    'sections_number' / Int16ul,
    'sections' / Array(this.sections_number,
        Struct('name' / CString(),
            'length' / Int32ul,
            'data' / Bytes(this.length)
        )
    )
)

main_struct = QwertyFile

if __name__ == '__main__':
    #check the struct
    main_struct.parse('\x11\x22\x33' + '\x02\x00' + ('.data\0' + '\x10\x00\x00\x00' + 'A'*0x10) + ('.text\0' + '\x05\x00\x00\x00' + 'B'*5))
