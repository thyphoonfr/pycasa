// DumpStringsRange.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;

public class DumpStringsRange extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address start = currentProgram.getAddressFactory().getAddress("00cad900");
        Address end = currentProgram.getAddressFactory().getAddress("00cae100");
        Memory mem = currentProgram.getMemory();

        Address curr = start;
        while (curr.compareTo(end) < 0) {
            byte b = mem.getByte(curr);
            if (b >= 32 && b <= 126) {
                // string starts
                StringBuilder sb = new StringBuilder();
                Address sAddr = curr;
                while (curr.compareTo(end) < 0) {
                    byte c = mem.getByte(curr);
                    if (c == 0) break;
                    if (c >= 32 && c <= 126) sb.append((char)c);
                    else sb.append('.');
                    curr = curr.add(1);
                }
                if (sb.length() >= 3) {
                    println(sAddr + ": " + sb.toString());
                }
            }
            curr = curr.add(1);
        }
    }
}
