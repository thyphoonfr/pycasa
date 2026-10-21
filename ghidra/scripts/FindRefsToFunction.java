// FindRefsToFunction.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class FindRefsToFunction extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("Usage: FindRefsToFunction <hex_address>");
            return;
        }
        Address targetAddr = currentProgram.getAddressFactory().getAddress(args[0]);
        ReferenceIterator iter = currentProgram.getReferenceManager().getReferencesTo(targetAddr);
        println("=== References to " + args[0] + " ===");
        while (iter.hasNext()) {
            Reference ref = iter.next();
            println("From: " + ref.getFromAddress() + " (Type: " + ref.getReferenceType() + ")");
        }
        println("=== End ===");
    }
}
