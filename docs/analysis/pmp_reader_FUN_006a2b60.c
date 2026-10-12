// Address: 006a2b60
// Function: FUN_006a2b60
// Target requested: 0x006A2B60

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_006a2b60(char *param_1,undefined4 param_2,char param_3)

{
  int iVar1;
  int iVar2;
  undefined1 auStack_12c [4];
  undefined4 uStack_128;
  int iStack_124;
  int iStack_120;
  undefined1 uStack_11c;
  undefined1 auStack_110 [268];
  uint uStack_4;
  
  uStack_4 = _DAT_00d24004 ^ (uint)auStack_12c;
  if (*param_1 != '\0') {
    if (*(int *)(param_1 + 0xc) == 0) {
      iVar2 = 0;
    }
    else {
      iVar2 = *(int *)(param_1 + 0xc) + 4;
    }
    func_0x00c08243(auStack_110,&UNK_00ca80f8,param_2,iVar2,&UNK_00ca80f4);
    uStack_128 = _DAT_00d678e0;
    func_0x009917f0(auStack_110);
    if ((iStack_120 == 0) || (func_0x00c07a30(&uStack_128,4,1,iStack_120), iStack_120 == 0)) {
      iVar2 = iStack_124;
      if (iStack_124 != 0) {
        iVar1 = InterlockedDecrement(iStack_124);
        if (iVar1 != 0) goto LAB_006a2cb6;
        func_0x0097caf0(iVar2);
        iStack_124 = 0;
      }
      func_0x0099d890();
    }
    else {
      uStack_128 = *(undefined4 *)(param_1 + 0x10);
      iVar2 = func_0x00c07a30(&uStack_128,4,1,iStack_120);
      if (iVar2 == 1) {
        uStack_128 = *(undefined4 *)(param_1 + 8);
        iVar2 = func_0x00c07a30(&uStack_128,4,1,iStack_120);
        if (iVar2 == 1) {
          iVar2 = func_0x006d17f0();
          if (iVar2 == 0) {
            *param_1 = '\0';
            if (param_3 != '\0') {
              uStack_11c = 1;
            }
            func_0x00408490();
          }
          else {
            func_0x00408490();
          }
          goto LAB_006a2cb6;
        }
      }
      func_0x00408490();
    }
  }
LAB_006a2cb6:
  func_0x00bef10a();
  return;
}


