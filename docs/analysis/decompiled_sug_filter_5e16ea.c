// Address: 005e0ef0
// Function: FUN_005e0ef0
// Target requested: 005e16ea

/* WARNING: Restarted to delay deadcode elimination for space: stack */

undefined4 FUN_005e0ef0(int *param_1)

{
  int *piVar1;
  int unaff_EDI;
  int unaff_retaddr;
  
  piVar1 = (int *)func_0x00926c20();
  (**(code **)(*piVar1 + 4))();
  func_0x00431360(*(undefined4 *)(unaff_retaddr + 700));
  (**(code **)(*param_1 + 0x3c))(2);
  if (&stack0x00000000 != (undefined1 *)0x18) {
    (**(code **)(unaff_EDI + 8))();
  }
  func_0x00401000();
  return 0;
}


