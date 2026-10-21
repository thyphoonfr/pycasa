// DecompileFRSort.java
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DecompileFRSort extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] addrs = {"0064d1b7", "0078a205", "006028aa"};
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        for (String aStr : addrs) {
            Address a = currentProgram.getAddressFactory().getAddress(aStr);
            Function f = currentProgram.getFunctionManager().getFunctionContaining(a);
            if (f != null) {
                println("=== Found function for " + aStr + ": " + f.getName() + " @ " + f.getEntryPoint() + " ===");
                DecompileResults res = decomp.decompileFunction(f, 60, monitor);
                if (res.decompileCompleted()) {
                    println(res.getDecompiledFunction().getC());
                }
            } else {
                println("No function at " + aStr);
            }
        }
    }
}
