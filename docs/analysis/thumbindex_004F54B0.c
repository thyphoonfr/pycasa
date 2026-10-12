// Address: 004f54b0
// Function: FUN_004f54b0
// Target requested: 0x004F54B0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int __thiscall FUN_004f54b0(int *param_1,undefined4 param_2,char param_3)

{
  int *piVar1;
  uint uVar2;
  char cVar3;
  int iVar4;
  int *piVar5;
  int iVar6;
  uint uVar7;
  int *piVar8;
  uint uStack_4c;
  int *piStack_48;
  uint auStack_44 [4];
  undefined1 uStack_34;
  int iStack_28;
  int iStack_24;
  int iStack_20;
  int iStack_1c;
  int iStack_18;
  int iStack_14;
  undefined1 uStack_10;
  undefined1 uStack_f;
  int iStack_e;
  
  piVar1 = param_1 + -0x16;
  piStack_48 = param_1;
  iVar4 = GetCurrentThreadId();
  if ((param_1[-0xe] == 0) || (param_1[-0xe] != iVar4)) {
    if ((char)param_1[-0x13] == '\0') {
      (**(code **)(*piVar1 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + -0xc);
    }
    param_1[-0xd] = 0;
    param_1[-0xe] = iVar4;
  }
  else {
    param_1[-0xd] = param_1[-0xd] + 1;
  }
  cVar3 = (**(code **)(*param_1 + 0x10))();
  if (cVar3 == '\0') {
    if (((param_1[-0xd] != 0) && (param_1[-0xe] != 0)) &&
       (iVar4 = GetCurrentThreadId(), param_1[-0xe] == iVar4)) goto LAB_004f5803;
    param_1[-0xe] = 0;
    if ((char)param_1[-0x13] != '\0') {
      LeaveCriticalSection(param_1 + -0xc);
      return 0;
    }
    goto LAB_004f5943;
  }
  auStack_44[0] = _DAT_00cf4f4c;
  func_0x009917f0(&UNK_00c863a0);
  uVar2 = auStack_44[3];
  uVar7 = auStack_44[2];
  if (auStack_44[3] == 0) {
    if (auStack_44[2] != 0) {
      iVar4 = InterlockedDecrement(auStack_44[2]);
      if (iVar4 != 0) goto LAB_004f55c1;
      func_0x0097caf0(uVar7);
      auStack_44[2] = 0;
    }
    func_0x0099d890();
LAB_004f55c1:
    if (((param_1[-0xd] != 0) && (param_1[-0xe] != 0)) &&
       (iVar4 = GetCurrentThreadId(), param_1[-0xe] == iVar4)) {
      param_1[-0xd] = param_1[-0xd] + -1;
      return -1;
    }
    param_1[-0xe] = 0;
    if ((char)param_1[-0x13] == '\0') {
      (**(code **)(*piVar1 + 0x1c))();
      return -1;
    }
    LeaveCriticalSection(param_1 + -0xc);
    return -1;
  }
  func_0x00c07a30(auStack_44,4,1,auStack_44[3]);
  if (param_3 != '\0') {
    uStack_34 = 1;
  }
  uVar7 = (uint)piStack_48[0xe7] >> 1;
  uStack_4c = uVar7;
  auStack_44[0] = uVar7;
  func_0x00c07a30(&uStack_4c,4,1,uVar2);
  uStack_4c = 0;
  if (uVar7 != 0) {
    do {
      piVar8 = (int *)(piStack_48[0xe6] + uStack_4c * 4);
      if (*piVar8 == 0) {
        piVar8 = piStack_48 + 0xe8;
      }
      else {
        piVar8 = (int *)*piVar8;
      }
      if (*(char *)((int)piVar8 + 0x1d) == '\0') {
LAB_004f56c3:
        auStack_44[1] = 0;
        piVar8[8] = -1;
        if (*piVar8 != 0) {
          func_0x00401000();
          *piVar8 = 0;
        }
        func_0x00401000();
        *(undefined2 *)((int)piVar8 + 0x1e) = 0xffff;
        *(undefined1 *)((int)piVar8 + 0x1d) = 0;
        *(undefined1 *)(piVar8 + 7) = 0;
        piVar8[6] = 0;
        piVar8[5] = 0;
        piVar8[2] = 0;
        piVar8[1] = 0;
      }
      else if (piVar8[6] == 4) {
        uVar7 = piVar8[8];
        if (uVar7 < auStack_44[0]) {
          if (*(int *)(piStack_48[0xe6] + uVar7 * 4) == 0) {
            piVar5 = piStack_48 + 0xe8;
          }
          else {
            piVar5 = *(int **)(piStack_48[0xe6] + uVar7 * 4);
          }
        }
        else {
          piVar5 = (int *)0x0;
        }
        if ((piVar5 == (int *)0x0) || ((piVar5[6] != 1 && (piVar5[6] != 0x19)))) goto LAB_004f56c3;
      }
      iVar4 = func_0x00996db0(auStack_44[3]);
      uVar7 = auStack_44[2];
      if (iVar4 != 0) {
        if (auStack_44[2] != 0) {
          iVar6 = InterlockedDecrement(auStack_44[2]);
          if (iVar6 != 0) goto LAB_004f583f;
          func_0x0097caf0(uVar7);
          auStack_44[2] = 0;
        }
        func_0x0099d890();
LAB_004f583f:
        if (((param_1[-0xd] != 0) && (param_1[-0xe] != 0)) &&
           (iVar6 = GetCurrentThreadId(), param_1[-0xe] == iVar6)) {
          param_1[-0xd] = param_1[-0xd] + -1;
          return iVar4;
        }
        param_1[-0xe] = 0;
        if ((char)param_1[-0x13] == '\0') {
          (**(code **)(*piVar1 + 0x1c))();
          return iVar4;
        }
        LeaveCriticalSection(param_1 + -0xc);
        return iVar4;
      }
      iStack_e = piVar8[8];
      iStack_28 = piVar8[1];
      iStack_24 = piVar8[2];
      iStack_20 = piVar8[3];
      iStack_1c = piVar8[4];
      iStack_18 = piVar8[5];
      iStack_14 = piVar8[6];
      uStack_10 = (undefined1)piVar8[7];
      uStack_f = *(undefined1 *)((int)piVar8 + 0x1d);
      iVar4 = func_0x00c07a30(&iStack_28,0x1e,1,auStack_44[3]);
      uVar7 = auStack_44[2];
      if (iVar4 != 1) {
        if (auStack_44[2] != 0) {
          iVar4 = InterlockedDecrement(auStack_44[2]);
          if (iVar4 != 0) goto LAB_004f58c6;
          func_0x0097caf0(uVar7);
          auStack_44[2] = 0;
        }
        func_0x0099d890();
LAB_004f58c6:
        if (((param_1[-0xd] != 0) && (param_1[-0xe] != 0)) &&
           (iVar4 = GetCurrentThreadId(), param_1[-0xe] == iVar4)) {
          param_1[-0xd] = param_1[-0xd] + -1;
          return 2;
        }
        param_1[-0xe] = 0;
        if ((char)param_1[-0x13] == '\0') {
          (**(code **)(*piVar1 + 0x1c))();
          return 2;
        }
        LeaveCriticalSection(param_1 + -0xc);
        return 2;
      }
      uStack_4c = uStack_4c + 1;
    } while (uStack_4c < auStack_44[0]);
  }
  FUN_004f25f0(piVar1);
  func_0x004f61c0(piVar1);
  uVar7 = auStack_44[2];
  *(undefined1 *)(piStack_48 + 2) = 0;
  if (auStack_44[2] == 0) {
LAB_004f57d9:
    func_0x0099d890();
  }
  else {
    iVar4 = InterlockedDecrement(auStack_44[2]);
    if (iVar4 == 0) {
      func_0x0097caf0(uVar7);
      auStack_44[2] = 0;
      goto LAB_004f57d9;
    }
  }
  if (((param_1[-0xd] != 0) && (param_1[-0xe] != 0)) &&
     (iVar4 = GetCurrentThreadId(), param_1[-0xe] == iVar4)) {
LAB_004f5803:
    param_1[-0xd] = param_1[-0xd] + -1;
    return 0;
  }
  param_1[-0xe] = 0;
  if ((char)param_1[-0x13] != '\0') {
    LeaveCriticalSection(param_1 + -0xc);
    return 0;
  }
LAB_004f5943:
  (**(code **)(*piVar1 + 0x1c))();
  return 0;
}


