// Address: 00579550
// Function: FUN_00579550
// Target requested: 0x00579550

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __thiscall FUN_00579550(int param_1,undefined4 param_2)

{
  char cVar1;
  int iVar2;
  undefined4 uVar3;
  bool bVar4;
  
  bVar4 = _DAT_00d67914 != 0;
  *(undefined1 *)(param_1 + 0xb3d) = 1;
  if (bVar4) {
    iVar2 = func_0x009c2fc0();
    if (iVar2 != 0) {
      cVar1 = func_0x009e39b0();
      if (cVar1 != '\0') {
        if (_DAT_00d67914 == 0) {
          uVar3 = 0;
        }
        else {
          uVar3 = func_0x009c2fc0();
        }
        iVar2 = func_0x00c07db2(uVar3,0,0xd3b8a0,0xd3e7a0,0);
        if ((iVar2 != 0) && (*(int *)(iVar2 + 0x288) != 0)) {
          func_0x00750b30(*(int *)(iVar2 + 0x288),param_2);
        }
      }
    }
    if (_DAT_00d67914 != 0) {
      iVar2 = func_0x009c2fc0();
      if (iVar2 != 0) {
        cVar1 = func_0x009e39b0();
        if (cVar1 != '\0') {
          if (_DAT_00d67914 == 0) {
            uVar3 = 0;
          }
          else {
            uVar3 = func_0x009c2fc0();
          }
          iVar2 = func_0x00c07db2(uVar3,0,0xd3b8a0,0xd3e7bc,0);
          if (iVar2 != 0) {
            func_0x00622150(param_2);
          }
        }
      }
      if (_DAT_00d67914 != 0) {
        iVar2 = func_0x009c2fc0();
        if (iVar2 != 0) {
          cVar1 = func_0x009e39b0();
          if (cVar1 != '\0') {
            if (_DAT_00d67914 == 0) {
              uVar3 = 0;
            }
            else {
              uVar3 = func_0x009c2fc0();
            }
            iVar2 = func_0x00c07db2(uVar3,0,0xd3b8a0,0xd3e7dc,0);
            if (iVar2 != 0) {
              func_0x0064d2f0(iVar2,param_2);
            }
          }
        }
        if (_DAT_00d67914 != 0) {
          uVar3 = func_0x009c2fc0();
          goto LAB_00579695;
        }
      }
    }
  }
  uVar3 = 0;
LAB_00579695:
  iVar2 = func_0x00c07db2(uVar3,0,0xd3b8a0,0xd3e688,0);
  if (iVar2 != 0) {
    func_0x005a6950(param_2);
  }
  return 0;
}


