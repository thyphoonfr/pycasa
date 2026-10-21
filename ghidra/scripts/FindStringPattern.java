// FindStringPattern.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.DataType;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

public class FindStringPattern extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] searches = {"ID_PICTURE_", "Picture::", "eMenuPicture", "ID_FILE_LOCATEONDISK", "ID_FILE_EXPORTTOFOLDER", "ID_PICTURE_ROTATECLOCKWISE"};
        for (String pattern : searches) {
            println("=== Search for: " + pattern + " ===");
            for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
                if (!block.isInitialized()) continue;
                byte[] bytes = new byte[(int)block.getSize()];
                block.getBytes(block.getStart(), bytes);
                String blockStr = new String(bytes, "ISO-8859-1");
                int idx = 0;
                while ((idx = blockStr.indexOf(pattern, idx)) != -1) {
                    println("  Found at " + block.getStart().add(idx) + ": " + blockStr.substring(idx, Math.min(idx + 50, blockStr.length())).replace('\0', ' '));
                    idx += pattern.length();
                }
            }
        }
    }
}
