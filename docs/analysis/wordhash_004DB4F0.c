// Address: 004db4f0
// Function: FUN_004db4f0
// Target requested: 0x004DB4F0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int __thiscall FUN_004db4f0(int *param_1,undefined4 param_2,char param_3)

{
  int *piVar1;
  int *piVar2;
  char cVar3;
  int iVar4;
  int iVar5;
  undefined4 uStack_24;
  int *piStack_20;
  int iStack_1c;
  int iStack_18;
  undefined1 uStack_14;
  
  piVar1 = param_1 + -0x12;
  piStack_20 = param_1;
  iVar4 = GetCurrentThreadId();
  if ((param_1[-10] == 0) || (param_1[-10] != iVar4)) {
    if ((char)param_1[-0xf] == '\0') {
      (**(code **)(*piVar1 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + -8);
    }
    param_1[-9] = 0;
    param_1[-10] = iVar4;
  }
  else {
    param_1[-9] = param_1[-9] + 1;
  }
  cVar3 = (**(code **)(*param_1 + 0x10))();
  if (cVar3 == '\0') {
LAB_004db6bd:
    if ((param_1[-9] != 0) && (param_1[-10] != 0)) {
      iVar4 = GetCurrentThreadId();
      if (param_1[-10] == iVar4) {
        param_1[-9] = param_1[-9] + -1;
        return 0;
      }
    }
    param_1[-10] = 0;
    if ((char)param_1[-0xf] != '\0') {
      LeaveCriticalSection(param_1 + -8);
      return 0;
    }
    (**(code **)(*piVar1 + 0x1c))();
    return 0;
  }
  uStack_24 = _DAT_00d678e0;
  func_0x009917f0(&UNK_00c85efc);
  if (iStack_18 != 0) {
    func_0x00c07a30(&uStack_24,4,1,iStack_18);
    piVar2 = piStack_20;
    if (iStack_18 != 0) {
      if (param_3 != '\0') {
        uStack_14 = 1;
      }
      iVar4 = func_0x00704500(piStack_20 + 3);
      if (iVar4 != 0) {
        func_0x00408490();
        if ((param_1[-9] != 0) && (param_1[-10] != 0)) {
          iVar5 = GetCurrentThreadId();
          if (param_1[-10] == iVar5) {
            param_1[-9] = param_1[-9] + -1;
            return iVar4;
          }
        }
        param_1[-10] = 0;
        if ((char)param_1[-0xf] != '\0') {
          LeaveCriticalSection(param_1 + -8);
          return iVar4;
        }
        (**(code **)(*piVar1 + 0x1c))();
        return iVar4;
      }
      *(undefined1 *)(piVar2 + 2) = 0;
      func_0x00408490();
      goto LAB_004db6bd;
    }
  }
  iVar4 = iStack_1c;
  if (iStack_1c != 0) {
    iVar5 = InterlockedDecrement(iStack_1c);
    if (iVar5 != 0) goto LAB_004db5c4;
    func_0x0097caf0(iVar4);
    iStack_1c = 0;
  }
  func_0x0099d890();
LAB_004db5c4:
  if ((param_1[-9] != 0) && (param_1[-10] != 0)) {
    iVar4 = GetCurrentThreadId();
    if (param_1[-10] == iVar4) {
      param_1[-9] = param_1[-9] + -1;
      return 2;
    }
  }
  param_1[-10] = 0;
  if ((char)param_1[-0xf] != '\0') {
    LeaveCriticalSection(param_1 + -8);
    return 2;
  }
  (**(code **)(*piVar1 + 0x1c))();
  return 2;
}


