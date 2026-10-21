// DumpStringsAt.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;

public class DumpStringsAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] addrs = {
            "00cae3c4", "00cae134", "00cae3e4", "00cae188", "00cae414",
            "00cae43c", "00cae460", "00cae338", "00cae308", "00cade6c",
            "00cae360", "00cae38c", "00caf334", "00caf30c", "00caf2ec",
            "00caf2b8", "00cae1b4", "00cae1d8", "00cae204", "00cae22c",
            "00cae258", "00cae278", "00cae29c", "00cae2c4", "00cae2f0"
        };
        Memory mem = currentProgram.getMemory();
        for (String a : addrs) {
            Address addr = currentProgram.getAddressFactory().getAddress(a);
            StringBuilder sb = new StringBuilder();
            try {
                for (int i = 0; i < 64; i++) {
                    byte b = mem.getByte(addr.add(i));
                    if (b == 0) break;
                    if (b >= 32 && b <= 126) sb.append((char)b);
                    else sb.append(String.format("\\x%02x", b));
                }
            } catch (Exception e) {}
            println(a + ": \"" + sb.toString() + "\"");
        }
    }
}
