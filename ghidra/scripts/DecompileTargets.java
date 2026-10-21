// DecompileTargets.java
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;

public class DecompileTargets extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] addrs = {
            "0074aee6", // unknownfaceheaderpanel
            "0048ab57", // FRSortThreshold 1
            "0048acc6", // FRSortThreshold 2
            "006e0eee", // FRSortThreshold 3
            "006e34e9", // FRSortThreshold 4
            "00415790", // facetemplatesV2.db
            "004ac6c5"  // unknownfacealbum
        };

        File outFile = new File("ghidra/decompiled_face_clustering.c");
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();

        try (PrintWriter pw = new PrintWriter(new FileWriter(outFile))) {
            for (String aStr : addrs) {
                Address a = currentProgram.getAddressFactory().getAddress(aStr);
                pw.println("// =========================================================");
                pw.println("// Target Address: " + aStr);

                Function f = fm.getFunctionContaining(a);
                if (f == null) {
                    // Try to disassemble or find enclosing
                    Instruction inst = listing.getInstructionAt(a);
                    if (inst == null) {
                        disassemble(a);
                    }
                    f = createFunction(a, "FUN_" + aStr);
                }

                if (f != null) {
                    pw.println("// Function: " + f.getName() + " @ " + f.getEntryPoint());
                    DecompileResults res = decomp.decompileFunction(f, 60, monitor);
                    if (res.decompileCompleted()) {
                        pw.println(res.getDecompiledFunction().getC());
                    } else {
                        pw.println("// Decompilation failed: " + res.getErrorMessage());
                    }
                } else {
                    pw.println("// No function found or created at " + aStr);
                }
                pw.println();
            }
        }
        println("Wrote decompiled code to " + outFile.getAbsolutePath());
    }
}
