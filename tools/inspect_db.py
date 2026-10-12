import os
import glob
import struct

def inspect_dbs():
    db3_dir = os.path.expandvars(r"%LOCALAPPDATA%\Google\Picasa2\db3")
    db_files = sorted(glob.glob(os.path.join(db3_dir, "*.db")))
    
    print(f"Examining {len(db_files)} .db files:")
    for path in db_files:
        name = os.path.basename(path)
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read(64)
        hex_data = data[:16].hex()
        # unpack first few 32-bit ints
        ints = [struct.unpack("<I", data[i:i+4])[0] for i in range(0, min(len(data), 32), 4)]
        print(f"\n{name} (size: {size} bytes):")
        print(f"  Hex[:16] : {hex_data}")
        print(f"  Ints[:8] : {ints}")

if __name__ == "__main__":
    inspect_dbs()
