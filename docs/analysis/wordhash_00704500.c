// Address: 00704500
// Function: FUN_00704500
// Target requested: 0x00704500

int FUN_00704500(undefined4 *param_1)

{
  int iVar1;
  int unaff_EDI;
  undefined4 uStack_24;
  undefined1 auStack_20 [4];
  undefined4 uStack_1c;
  undefined4 uStack_18;
  undefined4 *puStack_14;
  undefined4 uStack_10;
  int iStack_c;
  undefined1 uStack_8;
  
  uStack_18 = 0;
  uStack_1c = 0;
  uStack_24 = 0;
  iVar1 = func_0x00c07a30(auStack_20,4,1,*(undefined4 *)(unaff_EDI + 4));
  if (iVar1 != 1) {
    return 2;
  }
  puStack_14 = param_1 + 5;
  iVar1 = func_0x00a61700();
  if (iVar1 == 0) {
    uStack_24 = *param_1;
    iVar1 = func_0x00c07a30(&uStack_24,4,1,*(undefined4 *)(unaff_EDI + 4));
    if (iVar1 != 1) {
      return 2;
    }
    puStack_14 = param_1;
    uStack_10 = 0xffffffff;
    iStack_c = 0;
    uStack_8 = 0;
    func_0x004ddea0();
    while (iStack_c != 0) {
      if (*(int *)(iStack_c + 4) == 0) {
        return 4;
      }
      iVar1 = func_0x00a61a70(&uStack_1c,auStack_20,&stack0xffffffd8);
      if (iVar1 != 0) {
        return iVar1;
      }
      iVar1 = func_0x00c07a30(&stack0xffffffd0,4,1,*(undefined4 *)(unaff_EDI + 4));
      if (iVar1 != 1) {
        return 2;
      }
      iVar1 = FUN_0099c1e0(*(undefined4 *)(unaff_EDI + 4));
      if (iVar1 != 0) {
        return iVar1;
      }
      func_0x004ddea0();
    }
    iVar1 = 0;
  }
  return iVar1;
}


