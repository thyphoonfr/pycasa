// Address: 005ab210
// Function: FUN_005ab210
// Target requested: 0x005AB210

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __thiscall
FUN_005ab210(undefined4 param_1,undefined4 param_2,undefined4 param_3,undefined4 param_4)

{
  int *piVar1;
  int iVar2;
  undefined4 uVar3;
  undefined4 unaff_ESI;
  
  piVar1 = _DAT_00d6769c;
  if (_DAT_00d6769c == (int *)0x0) {
    uVar3 = func_0x0099b5b0(param_2,param_3,param_4);
    return uVar3;
  }
  iVar2 = GetCurrentThreadId();
  if ((piVar1[8] == 0) || (piVar1[8] != iVar2)) {
    if ((char)piVar1[3] == '\0') {
      (**(code **)(*piVar1 + 0x18))();
    }
    else {
      EnterCriticalSection(piVar1 + 10);
    }
    piVar1[9] = 0;
    piVar1[8] = iVar2;
  }
  else {
    piVar1[9] = piVar1[9] + 1;
  }
  uVar3 = func_0x005aa260(param_1,param_3,param_4);
  if (piVar1 == (int *)0x0) {
    LeaveCriticalSection(unaff_ESI);
    return uVar3;
  }
  if ((piVar1[9] != 0) && (piVar1[8] != 0)) {
    iVar2 = GetCurrentThreadId();
    if (piVar1[8] == iVar2) {
      piVar1[9] = piVar1[9] + -1;
      return uVar3;
    }
  }
  piVar1[8] = 0;
  if ((char)piVar1[3] != '\0') {
    LeaveCriticalSection(piVar1 + 10);
    return uVar3;
  }
  (**(code **)(*piVar1 + 0x1c))();
  return uVar3;
}


