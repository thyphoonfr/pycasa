// DecompileFaceCallers.java
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

public class DecompileFaceCallers extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] entries = {
            "0042a23d",
            "0042a570",
            "00430832",
            "004467b2",
            "004482a1",
            "00464273",
            "00464301",
            "00470629",
            "0047db16",
            "0047dc1c",
            "0049c2b0",
            "0049d560",
            "006adc25",
            "006ae280"
        };

        File outFile = new File("ghidra/decompiled_face_callers.c");
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();

        try (PrintWriter pw = new PrintWriter(new FileWriter(outFile))) {
            for (String aStr : entries) {
                Address a = currentProgram.getAddressFactory().getAddress(aStr);
                Function f = fm.getFunctionAt(a);
                if (f == null) {
                    Instruction inst = listing.getInstructionAt(a);
                    if (inst == null) {
                        disassemble(a);
                    }
                    f = createFunction(a, "FUN_" + aStr);
                }

                if (f != null) {
                    pw.println("// =========================================================");
                    pw.println("// Function: " + f.getName() + " @ " + f.getEntryPoint());
                    DecompileResults res = decomp.decompileFunction(f, 60, monitor);
                    if (res.decompileCompleted()) {
                        pw.println(res.getDecompiledFunction().getC());
                    } else {
                        pw.println("// Decompilation failed: " + res.getErrorMessage());
                    }
                } else {
                    pw.println("// Could not create function at " + aStr);
                }
                pw.println();
            }
        }
        println("Wrote decompiled code to " + outFile.getAbsolutePath());
    }
}
