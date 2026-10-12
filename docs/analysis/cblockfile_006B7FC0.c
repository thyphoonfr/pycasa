// Address: 006b7fc0
// Function: FUN_006b7fc0
// Target requested: 0x006B7FC0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int __thiscall FUN_006b7fc0(int *param_1,undefined4 param_2,char param_3)

{
  int *piVar1;
  int *piVar2;
  char cVar3;
  int iVar4;
  int iVar5;
  undefined4 uStack_24;
  int *piStack_20;
  undefined1 auStack_1c [4];
  int iStack_18;
  undefined1 uStack_14;
  
  if ((char)param_1[0x18] != '\0') {
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
    if ((param_1[8] & 0xfffffffeU) != 0) {
      cVar3 = (**(code **)(*param_1 + 0x10))();
      if (cVar3 != '\0') {
        func_0x006b71b0();
        if (((uint)param_1[0xb] < (uint)param_1[0xe] >> 1) &&
           (param_1[0xd] + param_1[0xb] * 0x14 != 0)) {
          func_0x0099de70();
        }
        if (param_1[0xf] == 0) {
          iVar4 = 0;
        }
        else {
          iVar4 = param_1[0xf] + 4;
        }
        uStack_24 = _DAT_00d678e0;
        func_0x009917f0(iVar4);
        if (iStack_18 == 0) {
LAB_006b80b2:
          func_0x00408490();
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
        func_0x00c07a30(&uStack_24,4,1,iStack_18);
        piVar2 = piStack_20;
        if (iStack_18 == 0) goto LAB_006b80b2;
        if (param_3 != '\0') {
          uStack_14 = 1;
        }
        iVar4 = func_0x00996d50(piStack_20[0xb]);
        if (iVar4 != 0) {
LAB_006b8141:
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
        iVar4 = func_0x0099c1e0(iStack_18);
        if (iVar4 != 0) goto LAB_006b8141;
        iVar4 = func_0x0099c1e0(iStack_18);
        if (iVar4 != 0) goto LAB_006b8141;
        iVar4 = func_0x0099c1e0(iStack_18);
        if (iVar4 != 0) goto LAB_006b8141;
        iVar4 = (**(code **)(*piVar1 + 0x20))(auStack_1c);
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
      }
    }
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
  }
  return 0;
}


