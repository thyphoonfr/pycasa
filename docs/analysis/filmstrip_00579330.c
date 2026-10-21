// Address: 00579330
// Function: FUN_00579330
// Target requested: 0x00579330

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

bool FUN_00579330(void)

{
  int iVar1;
  
  if (_DAT_00d67914 != 0) {
    iVar1 = func_0x009c2fc0();
    if (iVar1 != 0) {
      return *(char *)(iVar1 + 0x20c) == '\0';
    }
  }
  return false;
}


