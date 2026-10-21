// InspectTrackPopupMenuEx.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectTrackPopupMenuEx extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address addr = currentProgram.getAddressFactory().getAddress("00a6b100");
        FunctionManager fm = currentProgram.getFunctionManager();
        Function f = fm.getFunctionContaining(addr);
        if (f == null) {
            println("No function at 00a6b100, looking backwards...");
            // search for entry
            for (int i = 0; i < 256; i++) {
                Address test = addr.subtract(i);
                byte b = currentProgram.getMemory().getByte(test);
                byte prev = currentProgram.getMemory().getByte(test.subtract(1));
                if ((prev == (byte)0xcc || prev == (byte)0xc3) && (b == (byte)0x55 || b == (byte)0x83 || b == (byte)0x53)) {
                    println("Probable entry: " + test);
                    createFunction(test, "TrackPopupWrapper");
                    f = fm.getFunctionAt(test);
                    break;
                }
            }
        }
        if (f != null) {
            println("Function containing 00a6b100: " + f.getName() + " at " + f.getEntryPoint());
            ReferenceIterator iter = currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
            println("=== Callers of " + f.getName() + " ===");
            while (iter.hasNext()) {
                Reference r = iter.next();
                println("  From: " + r.getFromAddress() + " (" + r.getReferenceType() + ")");
            }
        }
    }
}
