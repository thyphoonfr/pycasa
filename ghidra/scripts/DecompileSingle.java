// DecompileSingle.java
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;

public class DecompileSingle extends GhidraScript {
    @Override
    public void run() throws Exception {
        String aStr = getScriptArgs().length > 0 ? getScriptArgs()[0] : "005e1b9b";
        Address a = currentProgram.getAddressFactory().getAddress(aStr);
        FunctionManager fm = currentProgram.getFunctionManager();
        Function f = fm.getFunctionContaining(a);
        if (f == null) {
            disassemble(a);
            f = fm.getFunctionContaining(a);
        }
        if (f == null) {
            f = createFunction(a, "FUN_" + aStr);
        }

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        File outFile = new File("ghidra/decompiled_single.c");
        try (PrintWriter pw = new PrintWriter(new FileWriter(outFile))) {
            if (f != null) {
                pw.println("// Function: " + f.getName() + " @ " + f.getEntryPoint());
                DecompileResults res = decomp.decompileFunction(f, 60, monitor);
                if (res.decompileCompleted()) {
                    pw.println(res.getDecompiledFunction().getC());
                } else {
                    pw.println("// Failed: " + res.getErrorMessage());
                }
            } else {
                pw.println("// No function found at " + aStr);
            }
        }
        println("Done: " + outFile.getAbsolutePath());
    }
}
