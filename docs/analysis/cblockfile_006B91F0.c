// Address: 006b91f0
// Function: FUN_006b91f0
// Target requested: 0x006B91F0

/* WARNING: Removing unreachable block (ram,0x006b9284) */
/* WARNING: Removing unreachable block (ram,0x006b928f) */
/* WARNING: Removing unreachable block (ram,0x006b92a2) */

int __thiscall FUN_006b91f0(int param_1,char *param_2)

{
  int *piVar1;
  char cVar2;
  int iVar3;
  char *pcVar4;
  int iVar5;
  int unaff_EBX;
  int aiStack_20 [7];
  
  piVar1 = (int *)(param_1 + -0x48);
  aiStack_20[0] = param_1;
  iVar3 = GetCurrentThreadId();
  if ((*(int *)(param_1 + -0x28) == 0) || (*(int *)(param_1 + -0x28) != iVar3)) {
    if (*(char *)(param_1 + -0x3c) == '\0') {
      (**(code **)(*piVar1 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + -0x20);
    }
    *(undefined4 *)(param_1 + -0x24) = 0;
    *(int *)(param_1 + -0x28) = iVar3;
  }
  else {
    *(int *)(param_1 + -0x24) = *(int *)(param_1 + -0x24) + 1;
  }
  pcVar4 = param_2;
  iVar3 = param_1;
  if (param_2 != (char *)0x0) {
    do {
      cVar2 = *pcVar4;
      pcVar4 = pcVar4 + 1;
    } while (cVar2 != '\0');
    func_0x00985ff0(param_2);
    iVar3 = aiStack_20[0];
  }
  if (*(int *)(iVar3 + 0x24) != 0) {
    func_0x00401000();
    *(int *)(iVar3 + 0x24) = 0;
  }
  func_0x00401000();
  iVar3 = FUN_006b82e0(param_2);
  if (iVar3 != 0) {
    if (((*(int *)(param_1 + -0x24) != 0) && (*(int *)(param_1 + -0x28) != 0)) &&
       (iVar5 = GetCurrentThreadId(), *(int *)(param_1 + -0x28) == iVar5)) {
      *(int *)(param_1 + -0x24) = *(int *)(param_1 + -0x24) + -1;
      return iVar3;
    }
    goto LAB_006b92e9;
  }
  func_0x00991870(aiStack_20,param_2);
  iVar3 = func_0x006b9030(piVar1,aiStack_20);
  if (iVar3 == 0) {
    iVar3 = func_0x006b8ac0(param_2);
    if (iVar3 == 0) {
      *(undefined1 *)(unaff_EBX + 8) = 0;
      func_0x00408490();
      if (((*(int *)(param_1 + -0x24) != 0) && (*(int *)(param_1 + -0x28) != 0)) &&
         (iVar3 = GetCurrentThreadId(), *(int *)(param_1 + -0x28) == iVar3)) {
        *(int *)(param_1 + -0x24) = *(int *)(param_1 + -0x24) + -1;
        return 0;
      }
      *(undefined4 *)(param_1 + -0x28) = 0;
      if (*(char *)(param_1 + -0x3c) == '\0') {
        (**(code **)(*piVar1 + 0x1c))();
        return 0;
      }
      LeaveCriticalSection(param_1 + -0x20);
      return 0;
    }
    func_0x00408490();
    if (((*(int *)(param_1 + -0x24) != 0) && (*(int *)(param_1 + -0x28) != 0)) &&
       (iVar5 = GetCurrentThreadId(), *(int *)(param_1 + -0x28) == iVar5)) {
      *(int *)(param_1 + -0x24) = *(int *)(param_1 + -0x24) + -1;
      return iVar3;
    }
    goto LAB_006b92e9;
  }
  if (aiStack_20[0] == 0) {
LAB_006b9378:
    func_0x0099d890();
  }
  else {
    iVar5 = InterlockedDecrement(aiStack_20[0]);
    if (iVar5 == 0) {
      func_0x0097caf0(aiStack_20[0]);
      aiStack_20[0] = 0;
      goto LAB_006b9378;
    }
  }
  if (((*(int *)(param_1 + -0x24) != 0) && (*(int *)(param_1 + -0x28) != 0)) &&
     (iVar5 = GetCurrentThreadId(), *(int *)(param_1 + -0x28) == iVar5)) {
    *(int *)(param_1 + -0x24) = *(int *)(param_1 + -0x24) + -1;
    return iVar3;
  }
LAB_006b92e9:
  *(undefined4 *)(param_1 + -0x28) = 0;
  if (*(char *)(param_1 + -0x3c) == '\0') {
    (**(code **)(*piVar1 + 0x1c))();
    return iVar3;
  }
  LeaveCriticalSection(param_1 + -0x20);
  return iVar3;
}


