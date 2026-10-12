// DecompileFunction.java - Ghidra headless script to disassemble & decompile functions
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Listing;

public class DecompileFunction extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("Usage: DecompileFunction <hex_address> [output_file]");
            return;
        }

        String addrStr = args[0];
        String outFile = args.length > 1 ? args[1] : null;

        Address targetAddr = currentProgram.getAddressFactory().getAddress(addrStr);
        if (targetAddr == null) {
            println("Invalid address: " + addrStr);
            return;
        }

        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();

        // If there's an existing function that does not start at targetAddr, remove it
        Function existing = fm.getFunctionContaining(targetAddr);
        if (existing != null && !existing.getEntryPoint().equals(targetAddr)) {
            println("Removing overlapping function " + existing.getName() + " at " + existing.getEntryPoint());
            removeFunction(existing);
        }

        // Ensure disassembled
        if (listing.getInstructionAt(targetAddr) == null) {
            println("Disassembling at " + addrStr + "...");
            disassemble(targetAddr);
        }

        Function func = fm.getFunctionAt(targetAddr);
        if (func == null) {
            println("Creating function at " + addrStr + "...");
            func = createFunction(targetAddr, "FUN_" + addrStr.replace("0x", ""));
        }

        if (func == null) {
            println("Failed to get/create function at " + addrStr);
            return;
        }

        println("Decompiling function: " + func.getName() + " at " + func.getEntryPoint() + " (size: " + func.getBody().getNumAddresses() + " addresses)");

        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        DecompileResults res = decomp.decompileFunction(func, 120, monitor);

        if (!res.decompileCompleted()) {
            println("Decompilation failed: " + res.getErrorMessage());
            return;
        }

        String code = res.getDecompiledFunction().getC();
        if (outFile != null) {
            File f = new File(outFile);
            f.getParentFile().mkdirs();
            try (PrintWriter pw = new PrintWriter(new FileWriter(f))) {
                pw.println("// Address: " + func.getEntryPoint());
                pw.println("// Function: " + func.getName());
                pw.println("// Target requested: " + addrStr);
                pw.println(code);
            }
            println("Wrote decompilation to " + outFile);
        } else {
            println("Decompiled code:\n" + code);
        }
    }
}
