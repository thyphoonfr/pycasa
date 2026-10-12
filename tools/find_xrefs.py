import pefile
import struct

def find_xrefs():
    pe = pefile.PE("bin/Picasa3.exe")
    image_base = pe.OPTIONAL_HEADER.ImageBase
    
    with open("bin/Picasa3.exe", "rb") as f:
        data = f.read()

    # Targets to search
    targets = {
        "picasa_ini_header": 0x00CA77F0, # [encoding]\r\nutf8=1\r\n[Picasa]\r\n
        "dot_picasa_ini": 0x00C80A6C,     # .picasa.ini
        "Picasa_ini": 0x00C8644C,         # Picasa.ini
        "star_yes": 0x00CA7888,           # star=yes\r\n
        "caption_fmt": 0x00CA7894,        # caption=%s\r\n
        "crop64_str": 0x00C80ADC,         # crop64
    }

    text_section = None
    for s in pe.sections:
        name = s.Name.rstrip(b"\x00").decode("latin1")
        if name == ".text":
            text_section = s
            break
            
    print(f"Text section: 0x{text_section.VirtualAddress:08X} - 0x{text_section.VirtualAddress + text_section.Misc_VirtualSize:08X}")
    text_data = text_section.get_data()
    text_va_start = image_base + text_section.VirtualAddress
    text_offset_start = text_section.PointerToRawData

    for name, va in targets.items():
        pattern = struct.pack("<I", va)
        idx = 0
        matches = []
        while True:
            pos = text_data.find(pattern, idx)
            if pos == -1:
                break
            ref_va = text_va_start + pos
            ref_offset = text_offset_start + pos
            matches.append((ref_va, ref_offset))
            idx = pos + 1
        print(f"Target '{name}' (VA 0x{va:08X}): {len(matches)} xrefs found in .text")
        for ref_va, ref_offset in matches:
            # show 16 bytes before and after
            context_start = max(0, pos - 16)
            context_end = min(len(text_data), pos + 20)
            hex_ctx = text_data[context_start:context_end].hex()
            print(f"  -> xref at VA 0x{ref_va:08X} (offset 0x{ref_offset:08X})")

if __name__ == "__main__":
    find_xrefs()
