// Address: 005ce090
// Function: FUN_005ce090
// Target requested: 0x005CE090

/* WARNING: Removing unreachable block (ram,0x005ce1ae) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_005ce090(int param_1)

{
  int iVar1;
  int *piVar2;
  undefined4 uVar3;
  undefined4 unaff_ESI;
  undefined4 unaff_EDI;
  undefined4 uVar4;
  float fVar5;
  char cStack_58;
  undefined8 uVar6;
  
  uVar6 = CONCAT44(unaff_ESI,unaff_EDI);
  if (*(uint *)(*(int *)(param_1 + 0x2c0) + 0x154) >> 1 != 0) {
    if (_DAT_00d67914 == 0) {
      iVar1 = 0;
    }
    else {
      iVar1 = func_0x009c2fc0();
    }
    if (*(int *)(iVar1 + 0x248) != 0) {
      piVar2 = (int *)func_0x00c07db2(iVar1,0,0xd3b8a0,0xd3e610,0,uVar6);
      if (piVar2 != (int *)0x0) {
        (**(code **)(*piVar2 + 4))(0,1);
      }
      func_0x00a54b70(param_1,1,1,0,1,0xffffffff,0xffffffff,0xffffffff,0xffffffff);
    }
    uVar6 = _DAT_00cf3a08;
    func_0x0076a4b0(0,_DAT_00cf3a08);
    fVar5 = (float)uVar6;
    func_0x0076a4b0(1,0);
    uVar3 = func_0x004ae180((int)(longlong)ROUND(fVar5));
    uVar3 = func_0x004af790(uVar3);
    func_0x009d2660(uVar3);
    if ((_DAT_00d67914 != 0) && (piVar2 = (int *)func_0x009c2fc0(), piVar2 != (int *)0x0)) {
      (**(code **)(*piVar2 + 0x6c))();
      piVar2[0x5b] = 0x3f800000;
      piVar2[0x5a] = 0x3f800000;
      piVar2[0x5d] = 0x3f800000;
      *(undefined1 *)((int)piVar2 + 0x139) = 0;
      piVar2[0x5c] = 0x3f800000;
      *(undefined1 *)((int)piVar2 + 0xed) = 0;
      *(undefined1 *)((int)piVar2 + 0xa1) = 0;
      uVar4 = 0;
      *(undefined1 *)((int)piVar2 + 0x55) = 0;
      uVar3 = func_0x00409ea0(0,0,0,0);
      func_0x009df010(uVar3);
      uVar4 = func_0x00409ea0(0,uVar4,0,0);
      func_0x009df060(uVar4);
      uVar3 = func_0x00409ea0(0x3f800000,uVar3,0,0);
      func_0x009df060(uVar3);
      if (cStack_58 != '\0') {
        func_0x00a54b70(param_1,1,1,0,1,0xffffffff,0xffffffff,0xffffffff,0xffffffff);
      }
    }
  }
  return 0;
}


