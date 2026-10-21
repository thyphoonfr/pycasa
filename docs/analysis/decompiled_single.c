// Function: FUN_006d0180 @ 006d0180

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_006d0180(int *param_1,int param_2,int param_3,undefined4 *param_4)

{
  char cVar1;
  int iVar2;
  int iVar3;
  int iVar4;
  undefined4 uVar5;
  undefined4 *puVar6;
  bool bVar7;
  bool bVar8;
  char cStack_49;
  undefined1 auStack_48 [28];
  undefined4 auStack_2c [2];
  undefined1 uStack_24;
  undefined1 uStack_c;
  undefined1 uStack_b;
  undefined4 uStack_8;
  
  if ((_DAT_00d9ff5c & 1) == 0) {
    _DAT_00d9ff5c = _DAT_00d9ff5c | 1;
    func_0x00407a20(auStack_48,&UNK_00c7eafc,&UNK_00ca87b8);
    DAT_00d9ff58 = func_0x004019b0();
    func_0x00401000();
    func_0x00401000();
  }
  cStack_49 = *(char *)((int)param_4 + 0x21);
  if (DAT_00d9ff58 == '\0') goto LAB_006d05b8;
  bVar7 = false;
  iVar2 = GetCurrentThreadId();
  if ((param_1[8] == 0) || (param_1[8] != iVar2)) {
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + 10);
    }
    param_1[9] = 0;
    param_1[8] = iVar2;
  }
  else {
    param_1[9] = param_1[9] + 1;
  }
  if (param_1[0x1a] == 0) {
    iVar2 = 0;
LAB_006d024f:
    bVar7 = param_1[0x1b] != 0;
    if (bVar7) {
      iVar2 = param_1[0x1b] + 4;
    }
    bVar8 = iVar2 == 0;
  }
  else {
    iVar2 = param_1[0x1a] + 4;
    bVar8 = false;
    if (iVar2 == 0) goto LAB_006d024f;
  }
  if (!bVar8) {
    if (*(int *)(iVar2 + 0x38) != param_2) {
      bVar8 = true;
    }
    cVar1 = func_0x006cfda0(*param_4,param_4[1],param_4[3],param_1[0x22]);
    if (cVar1 == '\0') {
      bVar8 = true;
    }
    if (*(int *)(iVar2 + 0x60) != param_4[9]) {
      bVar8 = true;
    }
    if (*(char *)(iVar2 + 0x5d) != '\0') {
      cStack_49 = '\x01';
    }
  }
  if (((param_1[9] == 0) || (param_1[8] == 0)) ||
     (iVar2 = GetCurrentThreadId(), param_1[8] != iVar2)) {
    param_1[8] = 0;
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x1c))();
    }
    else {
      LeaveCriticalSection(param_1 + 10);
    }
  }
  else {
    param_1[9] = param_1[9] + -1;
  }
  if (!bVar8) {
    if (bVar7) {
      iVar2 = 1;
      do {
        iVar3 = GetCurrentThreadId();
        if ((param_1[8] == 0) || (param_1[8] != iVar3)) {
          if ((char)param_1[3] == '\0') {
            (**(code **)(*param_1 + 0x18))();
          }
          else {
            EnterCriticalSection(param_1 + 10);
          }
          param_1[9] = 0;
          param_1[8] = iVar3;
        }
        else {
          param_1[9] = param_1[9] + 1;
        }
        if (param_1[0x1b] == 0) {
          if (((param_1[9] == 0) || (param_1[8] == 0)) ||
             (iVar2 = GetCurrentThreadId(), param_1[8] != iVar2)) {
            param_1[8] = 0;
            if ((char)param_1[3] == '\0') {
              (**(code **)(*param_1 + 0x1c))();
            }
            else {
              LeaveCriticalSection(param_1 + 10);
            }
          }
          else {
            param_1[9] = param_1[9] + -1;
          }
          break;
        }
        if (iVar2 < 500) {
          iVar2 = iVar2 * 2;
        }
        if (((param_1[9] == 0) || (param_1[8] == 0)) ||
           (iVar3 = GetCurrentThreadId(), param_1[8] != iVar3)) {
          param_1[8] = 0;
          if ((char)param_1[3] == '\0') {
            (**(code **)(*param_1 + 0x1c))();
          }
          else {
            LeaveCriticalSection(param_1 + 10);
          }
        }
        else {
          param_1[9] = param_1[9] + -1;
        }
      } while (((iVar2 != -1) && (iVar2 < 0)) ||
              ((iVar3 = WaitForSingleObject(_DAT_00d689cc,iVar2), iVar3 == 0x80 || (iVar3 != 0))));
    }
    iVar2 = GetCurrentThreadId();
    if ((param_1[8] == 0) || (param_1[8] != iVar2)) {
      if ((char)param_1[3] == '\0') {
        (**(code **)(*param_1 + 0x18))();
      }
      else {
        EnterCriticalSection(param_1 + 10);
      }
      param_1[9] = 0;
      param_1[8] = iVar2;
    }
    else {
      param_1[9] = param_1[9] + 1;
    }
    iVar2 = param_1[0x19];
    if ((iVar2 != 0) && (iVar2 != -4)) {
      iVar3 = *(int *)(iVar2 + 0x3c);
      cVar1 = func_0x006cfda0(*param_4,param_4[1],param_4[3],param_1[0x22]);
      if (cVar1 == '\0') {
        uStack_c = 1;
      }
      iVar4 = (**(code **)(*(int *)param_1[0x1f] + 8))(uStack_8);
      if (*(char *)(iVar2 + 0x61) != '\0') {
        cStack_49 = '\x01';
      }
      if (*(int *)(iVar2 + 0x28) == iVar4 && iVar3 == param_2) {
        iVar2 = *(int *)(param_3 + 0x30);
        func_0x006a8ed0();
        if (iVar2 != 0) {
          *(int *)(param_3 + 0x30) = iVar2;
          func_0x006bbe50();
        }
        func_0x0049a490(param_1 + 0x18);
        if (((param_1[9] != 0) && (param_1[8] != 0)) &&
           (iVar2 = GetCurrentThreadId(), param_1[8] == iVar2)) {
          param_1[9] = param_1[9] + -1;
          return 0;
        }
        param_1[8] = 0;
        if ((char)param_1[3] != '\0') {
          LeaveCriticalSection(param_1 + 10);
          return 0;
        }
        (**(code **)(*param_1 + 0x1c))();
        return 0;
      }
    }
    if (((param_1[9] == 0) || (param_1[8] == 0)) ||
       (iVar2 = GetCurrentThreadId(), param_1[8] != iVar2)) {
      param_1[8] = 0;
      if ((char)param_1[3] == '\0') {
        (**(code **)(*param_1 + 0x1c))();
      }
      else {
        LeaveCriticalSection(param_1 + 10);
      }
    }
    else {
      param_1[9] = param_1[9] + -1;
    }
  }
LAB_006d05b8:
  puVar6 = auStack_2c;
  for (iVar2 = 10; iVar2 != 0; iVar2 = iVar2 + -1) {
    *puVar6 = *param_4;
    param_4 = param_4 + 1;
    puVar6 = puVar6 + 1;
  }
  uStack_24 = 1;
  if (cStack_49 != '\0') {
    uStack_b = 1;
  }
  uVar5 = (**(code **)(*(int *)param_1[0x1f] + 4))(param_2,param_3,auStack_2c);
  return uVar5;
}


