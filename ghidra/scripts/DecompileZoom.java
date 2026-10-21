// DecompileZoom.java
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

public class DecompileZoom extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] addrs = new String[] { "005e1315", "005e1b57", "0074bb5c", "0074bf68", "005e12f0", "0074bb20" };
        FunctionManager fm = currentProgram.getFunctionManager();
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        File outFile = new File("ghidra/decompiled_zoom.c");
        try (PrintWriter pw = new PrintWriter(new FileWriter(outFile))) {
            for (String aStr : addrs) {
                Address a = currentProgram.getAddressFactory().getAddress(aStr);
                Function f = fm.getFunctionContaining(a);
                if (f == null) {
                    disassemble(a);
                    f = fm.getFunctionContaining(a);
                }
                if (f != null) {
                    pw.println("// ===========================================================================");
                    pw.println("// Function: " + f.getName() + " @ " + f.getEntryPoint() + " (containing " + aStr + ")");
                    pw.println("// ===========================================================================");
                    DecompileResults res = decomp.decompileFunction(f, 60, monitor);
                    if (res.decompileCompleted()) {
                        pw.println(res.getDecompiledFunction().getC());
                    } else {
                        pw.println("// Failed: " + res.getErrorMessage());
                    }
                } else {
                    pw.println("// No function found containing " + aStr);
                }
            }
        }
        println("Done: " + outFile.getAbsolutePath());
    }
}
