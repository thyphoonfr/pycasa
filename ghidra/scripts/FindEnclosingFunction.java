// FindEnclosingFunction.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

public class FindEnclosingFunction extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] targets = {"0074aee6", "0048ab57", "0048acc6", "004ac6c5", "004ac762"};
        for (String t : targets) {
            Address addr = currentProgram.getAddressFactory().getAddress(t);
            println("=== Target: " + t + " ===");
            Instruction inst = currentProgram.getListing().getInstructionAt(addr);
            if (inst == null) {
                println("  Not instruction. Disassembling...");
                disassemble(addr);
                inst = currentProgram.getListing().getInstructionAt(addr);
            }
            println("  Instruction: " + (inst != null ? inst.toString() : "null"));
            
            // Search backwards for function entry point (e.g. push ebp / sub esp)
            Address cur = addr;
            Function f = null;
            for (int i = 0; i < 500; i++) {
                f = currentProgram.getFunctionManager().getFunctionContaining(cur);
                if (f != null) {
                    println(String.format("  Function containing %s: %s @ %s (size %d)", cur, f.getName(), f.getEntryPoint(), f.getBody().getNumAddresses()));
                    break;
                }
                cur = cur.subtract(1);
            }
        }
    }
}
