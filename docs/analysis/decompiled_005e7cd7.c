// Address: 005e7cd7
// Function: FUN_005e7cd7
// Target requested: 0x005e7cd7

undefined4 FUN_005e7cd7(void)

{
  int iVar1;
  int *unaff_EBP;
  int unaff_ESI;
  
  iVar1 = TrackPopupMenu();
  func_0x00a6b060();
  if (unaff_EBP != (int *)0x0) {
    *unaff_EBP = iVar1;
  }
  *(bool *)(unaff_ESI + 0x3114) = iVar1 != 0;
  return 1000000;
}


