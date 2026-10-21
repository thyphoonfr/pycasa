// InspectAndDecompile.java
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

public class InspectAndDecompile extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("Usage: InspectAndDecompile <hex_address> [output_file]");
            return;
        }

        Address targetAddr = currentProgram.getAddressFactory().getAddress(args[0]);
        String outFile = args.length > 1 ? args[1] : null;

        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();

        Instruction inst = listing.getInstructionAt(targetAddr);
        println("Instruction at " + targetAddr + ": " + (inst != null ? inst.toString() : "null"));

        Function func = fm.getFunctionContaining(targetAddr);
        if (func == null) {
            println("No containing function. Checking instruction at targetAddr...");
            if (inst == null) {
                println("Disassembling at " + targetAddr + "...");
                disassemble(targetAddr);
                inst = listing.getInstructionAt(targetAddr);
            }
            // Try to find function backward or create function
            func = createFunction(targetAddr, "FUN_" + args[0].replace("0x", ""));
        }

        if (func != null) {
            println("Found function: " + func.getName() + " at " + func.getEntryPoint() + " body: " + func.getBody());
            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);
            DecompileResults res = decomp.decompileFunction(func, 120, monitor);
            if (res.decompileCompleted()) {
                String code = res.getDecompiledFunction().getC();
                if (outFile != null) {
                    File f = new File(outFile);
                    f.getParentFile().mkdirs();
                    try (PrintWriter pw = new PrintWriter(new FileWriter(f))) {
                        pw.println("// Address: " + func.getEntryPoint());
                        pw.println("// Function: " + func.getName());
                        pw.println("// Target requested: " + args[0]);
                        pw.println(code);
                    }
                    println("Wrote decompilation to " + outFile);
                } else {
                    println("Decompiled:\n" + code);
                }
            } else {
                println("Decompilation failed: " + res.getErrorMessage());
            }
        } else {
            println("Still could not find or create function.");
            // Print 10 instructions forward
            Address curr = targetAddr;
            for (int i = 0; i < 15; i++) {
                Instruction in = listing.getInstructionAt(curr);
                if (in != null) {
                    println(curr + ": " + in.toString());
                    curr = in.getMaxAddress().add(1);
                } else {
                    println(curr + ": (no instruction)");
                    break;
                }
            }
        }
    }
}
