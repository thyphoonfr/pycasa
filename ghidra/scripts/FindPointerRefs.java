// FindPointerRefs.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class FindPointerRefs extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] ptrs = {"00c408f0", "00c407c4", "00c407c8", "00c407a8", "00c4079c", "00c407a0", "00c40798", "00c40818", "00c40810"};
        for (String p : ptrs) {
            Address addr = currentProgram.getAddressFactory().getAddress(p);
            ReferenceIterator iter = currentProgram.getReferenceManager().getReferencesTo(addr);
            println("=== Refs to " + p + " ===");
            while (iter.hasNext()) {
                Reference r = iter.next();
                println("  From: " + r.getFromAddress() + " (" + r.getReferenceType() + ")");
            }
        }
    }
}
