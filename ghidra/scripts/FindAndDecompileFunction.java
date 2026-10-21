// FindAndDecompileFunction.java
import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import ghidra.app.script.GhidraScript;
import ghidra.app.cmd.disassemble.DisassembleCommand;
import ghidra.app.cmd.function.CreateFunctionCmd;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;

public class FindAndDecompileFunction extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Address targetAddr = currentProgram.getAddressFactory().getAddress(args[0]);
        String outFile = args.length > 1 ? args[1] : null;

        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();
        Memory mem = currentProgram.getMemory();

        // Search backwards up to 4096 bytes for function entry (e.g. 0x55 0x8b 0xec or after 0xc3/0xcc)
        Address search = targetAddr;
        Address entry = null;

        for (int offset = 1; offset < 4096; offset++) {
            Address test = targetAddr.subtract(offset);
            byte b0 = mem.getByte(test);
            byte b1 = mem.getByte(test.add(1));
            byte b2 = mem.getByte(test.add(2));

            // check 55 8b ec
            if ((b0 == (byte)0x55) && (b1 == (byte)0x8b) && (b2 == (byte)0xec)) {
                // check if byte before is cc or c3 or 90
                byte prev = mem.getByte(test.subtract(1));
                if (prev == (byte)0xcc || prev == (byte)0xc3 || prev == (byte)0x90 || prev == (byte)0xc2) {
                    entry = test;
                    break;
                }
            }
            // check 83 ec or 81 ec after ret/int3
            if ((b0 == (byte)0x83 || b0 == (byte)0x81) && (b1 == (byte)0xec)) {
                byte prev = mem.getByte(test.subtract(1));
                if (prev == (byte)0xcc || prev == (byte)0xc3 || prev == (byte)0x90) {
                    entry = test;
                    break;
                }
            }
            // check 53 8b dc or similar push registers after cc/c3
            if (b0 == (byte)0x53 || b0 == (byte)0x56 || b0 == (byte)0x57) {
                byte prev = mem.getByte(test.subtract(1));
                if (prev == (byte)0xcc || prev == (byte)0xc3) {
                    // Check if it's an entry
                    entry = test;
                    // don't break immediately if 55 8b ec is closer? We are searching backwards, so this is the closest!
                    break;
                }
            }
        }

        if (entry != null) {
            println("Found probable function entry at " + entry);
            // Clear any functions in the range
            Address curr = entry;
            while (curr.compareTo(targetAddr.add(512)) < 0) {
                Function f = fm.getFunctionContaining(curr);
                if (f != null) {
                    println("Removing overlapping function " + f.getName() + " at " + f.getEntryPoint());
                    fm.removeFunction(f.getEntryPoint());
                }
                curr = curr.add(32);
            }

            // Disassemble from entry
            DisassembleCommand cmd = new DisassembleCommand(entry, null, true);
            cmd.applyTo(currentProgram);

            // Create function
            CreateFunctionCmd fcmd = new CreateFunctionCmd(entry);
            fcmd.applyTo(currentProgram);

            Function func = fm.getFunctionAt(entry);
            if (func != null) {
                println("Created function " + func.getName() + " at " + func.getEntryPoint() + " body: " + func.getBody());
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
                println("Failed to create function at " + entry);
            }
        } else {
            println("Could not find function entry for " + targetAddr);
        }
    }
}
