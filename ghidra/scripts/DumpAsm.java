// DumpAsm.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;

public class DumpAsm extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Address start = currentProgram.getAddressFactory().getAddress(args[0]);
        int count = Integer.parseInt(args[1]);
        Listing listing = currentProgram.getListing();

        Address curr = start;
        for (int i = 0; i < count; i++) {
            Instruction in = listing.getInstructionAt(curr);
            if (in == null) {
                disassemble(curr);
                in = listing.getInstructionAt(curr);
            }
            if (in != null) {
                println(String.format("%s: %s", in.getAddress(), in.toString()));
                curr = in.getMaxAddress().add(1);
            } else {
                println(curr + ": (unable to disassemble)");
                curr = curr.add(1);
            }
        }
    }
}
