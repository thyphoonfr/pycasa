// Address: 006d17f0
// Function: FUN_006d17f0
// Target requested: 0x006D17F0

int __fastcall FUN_006d17f0(int *param_1)

{
  int in_EAX;
  int iVar1;
  int iVar2;
  int *piStack_4;
  
  piStack_4 = param_1;
  iVar1 = GetCurrentThreadId();
  if ((param_1[8] == 0) || (param_1[8] != iVar1)) {
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + 10);
    }
    param_1[9] = 0;
    param_1[8] = iVar1;
  }
  else {
    param_1[9] = param_1[9] + 1;
  }
  piStack_4 = (int *)param_1[0xc5];
  iVar1 = func_0x00c07a30(&piStack_4,4,1,*(undefined4 *)(in_EAX + 4));
  if (iVar1 != 1) {
    if (((param_1[9] != 0) && (param_1[8] != 0)) &&
       (iVar1 = GetCurrentThreadId(), param_1[8] == iVar1)) {
      param_1[9] = param_1[9] + -1;
      return 2;
    }
    param_1[8] = 0;
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x1c))();
      return 2;
    }
    LeaveCriticalSection(param_1 + 10);
    return 2;
  }
  switch(param_1[0xc5]) {
  case 0x13320000:
    iVar1 = func_0x009977a0(*(undefined4 *)(in_EAX + 4));
    break;
  case 0x13320001:
    iVar1 = func_0x00997f40(*(undefined4 *)(in_EAX + 4));
    break;
  case 0x13320002:
    iVar1 = func_0x009981e0(*(undefined4 *)(in_EAX + 4));
    break;
  case 0x13320003:
    iVar1 = func_0x00998090(*(undefined4 *)(in_EAX + 4));
    break;
  case 0x13320004:
    iVar1 = func_0x009981e0(*(undefined4 *)(in_EAX + 4));
    break;
  case 0x13320005:
    iVar1 = func_0x00998330(*(undefined4 *)(in_EAX + 4));
    break;
  case 0x13320006:
    iVar1 = func_0x009975d0(*(undefined4 *)(in_EAX + 4));
    break;
  case 0x13320007:
    iVar1 = func_0x00997f40(*(undefined4 *)(in_EAX + 4));
    break;
  default:
    if (((param_1[9] != 0) && (param_1[8] != 0)) &&
       (iVar1 = GetCurrentThreadId(), param_1[8] == iVar1)) {
      param_1[9] = param_1[9] + -1;
      return 1;
    }
    param_1[8] = 0;
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x1c))();
      return 1;
    }
    LeaveCriticalSection(param_1 + 10);
    return 1;
  }
  if (iVar1 == 0) {
    if (((param_1[9] != 0) && (param_1[8] != 0)) &&
       (iVar1 = GetCurrentThreadId(), param_1[8] == iVar1)) {
      param_1[9] = param_1[9] + -1;
      return 0;
    }
    param_1[8] = 0;
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x1c))();
      return 0;
    }
    LeaveCriticalSection(param_1 + 10);
    return 0;
  }
  if (((param_1[9] != 0) && (param_1[8] != 0)) &&
     (iVar2 = GetCurrentThreadId(), param_1[8] == iVar2)) {
    param_1[9] = param_1[9] + -1;
    return iVar1;
  }
  param_1[8] = 0;
  if ((char)param_1[3] == '\0') {
    (**(code **)(*param_1 + 0x1c))();
    return iVar1;
  }
  LeaveCriticalSection(param_1 + 10);
  return iVar1;
}


