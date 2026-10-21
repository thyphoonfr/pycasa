// FindPointerToAddress.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

public class FindPointerToAddress extends GhidraScript {
    @Override
    public void run() throws Exception {
        int[] targets = {
            0x00cb10a4, // unknownfaceheaderpanel
            0x00c81cf4, // FRSortThreshold
            0x00c81cc0, // FRSuggestionThreshold
            0x00c833c8, // CThumbDB::unknownfacealbum
            0x00c80e20  // facetemplatesV2.db
        };

        Memory mem = currentProgram.getMemory();
        for (int t : targets) {
            println(String.format("=== Searching for pointer to 0x%08X ===", t));
            byte[] targetBytes = new byte[] {
                (byte)(t & 0xFF),
                (byte)((t >> 8) & 0xFF),
                (byte)((t >> 16) & 0xFF),
                (byte)((t >> 24) & 0xFF)
            };

            for (MemoryBlock block : mem.getBlocks()) {
                if (!block.isInitialized()) continue;
                byte[] bytes = new byte[(int)block.getSize()];
                block.getBytes(block.getStart(), bytes);

                for (int i = 0; i <= bytes.length - 4; i++) {
                    if (bytes[i] == targetBytes[0] &&
                        bytes[i+1] == targetBytes[1] &&
                        bytes[i+2] == targetBytes[2] &&
                        bytes[i+3] == targetBytes[3]) {
                        Address found = block.getStart().add(i);
                        Function f = currentProgram.getFunctionManager().getFunctionContaining(found);
                        String fname = (f != null) ? f.getName() + " @ " + f.getEntryPoint() : "(no func)";
                        println(String.format("  Pointer found at %s in %s", found, fname));
                    }
                }
            }
        }
    }
}
