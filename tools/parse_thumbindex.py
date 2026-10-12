import struct
import os

def parse_thumbindex():
    path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3\thumbindex.db")
    with open(path, "rb") as f:
        data = f.read()

    print(f"File: {path}, total bytes: {len(data)}")
    
    # Header: 8 bytes
    magic, count = struct.unpack("<II", data[:8])
    magic_f = struct.unpack("<f", data[:4])[0]
    print(f"Magic: 0x{magic:08X} ({magic_f}f), Count: {count}")

    # Now let's inspect the records
    offset = 8
    paths = []
    for i in range(min(count, 20)):
        # Check if length-prefixed or null-terminated
        # In our inspect_db earlier:
        # 43 3a 5c 55 73 65 72 73 -> 'C:\Users...'
        # Let's find null terminator
        end = data.find(b"\x00", offset)
        if end == -1:
            break
        p = data[offset:end].decode("latin1", errors="replace")
        paths.append((i, offset, p))
        offset = end + 1

    print(f"First {len(paths)} records (offset-based):")
    for idx, off, p in paths:
        print(f"  [{idx:4d}] @ 0x{off:08X}: {p}")

    # Let's verify total records up to end of file
    offset = 8
    all_paths = []
    for i in range(count):
        end = data.find(b"\x00", offset)
        if end == -1:
            break
        all_paths.append(data[offset:end])
        offset = end + 1

    print(f"Successfully parsed {len(all_paths)} / {count} paths. Consumed {offset} / {len(data)} bytes.")

if __name__ == "__main__":
    parse_thumbindex()
