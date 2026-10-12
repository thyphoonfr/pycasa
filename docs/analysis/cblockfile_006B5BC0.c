// Address: 006b5bc0
// Function: FUN_006b5bc0
// Target requested: 0x006B5BC0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __thiscall FUN_006b5bc0(undefined4 *param_1,int *param_2,int *param_3)

{
  uint *puVar1;
  byte *pbVar2;
  undefined1 auStack_a38 [1560];
  byte *pbStack_420;
  int iStack_220;
  uint uStack_8;
  
  uStack_8 = _DAT_00d24004 ^ (uint)auStack_a38;
  puVar1 = (uint *)*param_2;
  if ((((puVar1 == (uint *)0x0) || ((*puVar1 & 0xffffff00) == 0)) || ((char)puVar1[1] == '\0')) ||
     (((*puVar1 & 0xffffff00) == 0 || ((char)puVar1[1] != '.')))) {
    func_0x004089e0(param_2);
    if ((pbStack_420 != (byte *)0x0) && (*pbStack_420 < 0x80)) {
      InterlockedIncrement(pbStack_420);
    }
    if (*param_3 == 0) {
      pbVar2 = (byte *)0x0;
    }
    else {
      pbVar2 = (byte *)(*param_3 + 4);
    }
    func_0x00985af0(&stack0xfffff5c4);
    if (iStack_220 == 0) {
      iStack_220 = 0;
    }
    else {
      iStack_220 = iStack_220 + 4;
    }
    func_0x00985af0(&stack0xfffff5bc,iStack_220);
    *param_1 = pbVar2;
    if ((pbVar2 != (byte *)0x0) && (*pbVar2 < 0x80)) {
      InterlockedIncrement(pbVar2);
    }
    func_0x00401000();
    func_0x00408c00();
  }
  else {
    func_0x00408760(param_3);
  }
  func_0x00bef10a();
  return;
}


