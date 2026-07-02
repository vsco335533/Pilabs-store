import zipfile
import struct

def parse_axml_package(apk_path):
    with zipfile.ZipFile(apk_path, 'r') as z:
        data = z.read('AndroidManifest.xml')
        
    if len(data) < 8:
        return
        
    magic, file_size = struct.unpack("<II", data[0:8])
    if magic != 0x00080003:
        raise ValueError("Not a valid AXML file (magic mismatch)")
        
    offset = 8
    strings = []
    
    while offset < len(data):
        chunk_type, chunk_size = struct.unpack("<II", data[offset:offset+8])
        chunk_data = data[offset : offset + chunk_size]
        
        if chunk_type == 0x001C0001:  # String Pool chunk
            sp_data = chunk_data
            string_count, style_count, flags, string_start, styles_start = struct.unpack("<IIIII", sp_data[8:28])
            is_utf8 = bool(flags & (1 << 8))
            
            offsets = []
            for i in range(string_count):
                offsets.append(struct.unpack("<I", sp_data[28 + i*4 : 32 + i*4])[0])
                
            pool_bytes = sp_data[string_start:]
            
            for off in offsets:
                if is_utf8:
                    u8len_offset = off
                    l1 = pool_bytes[u8len_offset]
                    if l1 & 0x80:
                        l1 = ((l1 & 0x7F) << 8) | pool_bytes[u8len_offset + 1]
                        u8len_offset += 2
                    else:
                        u8len_offset += 1
                        
                    l2 = pool_bytes[u8len_offset]
                    if l2 & 0x80:
                        l2 = ((l2 & 0x7F) << 8) | pool_bytes[u8len_offset + 1]
                        u8len_offset += 2
                    else:
                        u8len_offset += 1
                        
                    s_bytes = pool_bytes[u8len_offset : u8len_offset + l2]
                    try:
                        strings.append(s_bytes.decode('utf-8'))
                    except:
                        strings.append("")
                else:
                    u16len_offset = off
                    l1 = struct.unpack("<H", pool_bytes[u16len_offset : u16len_offset + 2])[0]
                    if l1 & 0x8000:
                        l1 = ((l1 & 0x7FFF) << 16) | struct.unpack("<H", pool_bytes[u16len_offset+2 : u16len_offset+4])[0]
                        u16len_offset += 4
                    else:
                        u16len_offset += 2
                    s_bytes = pool_bytes[u16len_offset : u16len_offset + l1*2]
                    try:
                        strings.append(s_bytes.decode('utf-16'))
                    except:
                        strings.append("")
            
        elif chunk_type == 0x00100102:  # Start Element chunk
            if len(chunk_data) >= 30:
                ns_idx, name_idx, attr_start, attr_size, attr_count = struct.unpack("<IIHHH", chunk_data[16:30])
                
                elem_name = strings[name_idx] if name_idx < len(strings) else f"unknown_{name_idx}"
                
                if elem_name == "manifest":
                    print(f"Found XML tag: <{elem_name}>")
                    print("String pool index for 'manifest':", name_idx)
                    print("attr_start =", attr_start, "attr_size =", attr_size, "attr_count =", attr_count)
                    
                    # Print chunk data around attr_start in hex
                    raw_attrs = chunk_data[attr_start : attr_start + attr_size * attr_count]
                    print("Raw attributes hex:")
                    for i in range(attr_count):
                        attr_bytes = raw_attrs[i * attr_size : (i + 1) * attr_size]
                        words = struct.unpack("<" + "I" * (attr_size // 4), attr_bytes)
                        print(f"  Attr {i} words:", words)
                        # Print string representations for indices
                        decoded_words = []
                        for w in words:
                            if w != 0xFFFFFFFF and w < len(strings):
                                decoded_words.append(f"'{strings[w]}'")
                            else:
                                decoded_words.append(hex(w))
                        print(f"    Decoded:", decoded_words)
                        
        offset += chunk_size
        
    return None

if __name__ == '__main__':
    import os
    apk_dir = "uploads/apks"
    for f in os.listdir(apk_dir):
        if f.endswith('.apk') and not 'test' in f:
            path = os.path.join(apk_dir, f)
            print(f"\nParsing {path}...")
            try:
                parse_axml_package(path)
            except Exception as e:
                print("Error:", e)
