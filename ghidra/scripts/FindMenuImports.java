// FindMenuImports.java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class FindMenuImports extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] funcs = {"CreatePopupMenu", "TrackPopupMenu", "AppendMenuA", "AppendMenuW", "InsertMenuA", "InsertMenuW", "InsertMenuItemA", "InsertMenuItemW", "EnableMenuItem", "CheckMenuItem"};
        for (String f : funcs) {
            SymbolIterator iter = currentProgram.getSymbolTable().getSymbols(f);
            while (iter.hasNext()) {
                Symbol s = iter.next();
                println("Symbol: " + s.getName() + " at " + s.getAddress());
                ReferenceIterator refIter = currentProgram.getReferenceManager().getReferencesTo(s.getAddress());
                int count = 0;
                while (refIter.hasNext()) {
                    Reference ref = refIter.next();
                    println("  Ref from: " + ref.getFromAddress() + " (" + ref.getReferenceType() + ")");
                    count++;
                    if (count > 25) {
                        println("  (truncated...)");
                        break;
                    }
                }
            }
        }
    }
}
