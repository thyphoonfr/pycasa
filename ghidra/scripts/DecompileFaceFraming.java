// DecompileFaceFraming.java
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

public class DecompileFaceFraming extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] addrs = {
            "00570511",
            "0057a4f0",
            "005c785f",
            "005cb316",
            "005e5290",
            "005e8bf2",
            "00787d7a",
            "00412d26",
            "009b93f0",
            "009b9290",
            "00456a15"
        };

        File outFile = new File("ghidra/decompiled_face_framing.c");
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
