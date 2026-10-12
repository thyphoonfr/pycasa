// Address: 009975d0
// Function: FUN_009975d0
// Target requested: 0x009975D0

undefined4 FUN_009975d0(undefined4 param_1)

{
  char cVar1;
  int *in_EAX;
  int iVar2;
  char *pcVar3;
  char *pcVar4;
  uint uVar5;
  uint uStack_4;
  
  iVar2 = GetCurrentThreadId();
  if ((in_EAX[8] == 0) || (in_EAX[8] != iVar2)) {
    if ((char)in_EAX[3] == '\0') {
      (**(code **)(*in_EAX + 0x18))();
    }
    else {
      EnterCriticalSection(in_EAX + 10);
    }
    in_EAX[9] = 0;
    in_EAX[8] = iVar2;
  }
  else {
    in_EAX[9] = in_EAX[9] + 1;
  }
  uStack_4 = (uint)in_EAX[0x13] >> 1;
  iVar2 = func_0x00c07a30(&uStack_4,4,1,param_1);
  if (iVar2 != 1) {
    if (((in_EAX[9] != 0) && (in_EAX[8] != 0)) && (iVar2 = GetCurrentThreadId(), in_EAX[8] == iVar2)
       ) {
      in_EAX[9] = in_EAX[9] + -1;
      return 2;
    }
    in_EAX[8] = 0;
    if ((char)in_EAX[3] == '\0') {
      (**(code **)(*in_EAX + 0x1c))();
      return 2;
    }
    LeaveCriticalSection(in_EAX + 10);
    return 2;
  }
  uVar5 = 0;
  if ((in_EAX[0x13] & 0xfffffffeU) != 0) {
    do {
      pcVar4 = *(char **)(in_EAX[0x12] + uVar5 * 4);
      if (pcVar4 == (char *)0x0) {
LAB_009976f9:
        func_0x00c0aea6(0,param_1);
      }
      else {
        pcVar3 = pcVar4;
        do {
          cVar1 = *pcVar3;
          pcVar3 = pcVar3 + 1;
        } while (cVar1 != '\0');
        pcVar3 = pcVar3 + (1 - (int)(pcVar4 + 1));
        if (pcVar3 == (char *)0x0) goto LAB_009976f9;
        pcVar4 = (char *)func_0x00c07a30(pcVar4,1,pcVar3,param_1);
        if (pcVar4 != pcVar3) {
          if (((in_EAX[9] != 0) && (in_EAX[8] != 0)) &&
             (iVar2 = GetCurrentThreadId(), in_EAX[8] == iVar2)) {
            in_EAX[9] = in_EAX[9] + -1;
            return 2;
          }
          in_EAX[8] = 0;
          if ((char)in_EAX[3] == '\0') {
            (**(code **)(*in_EAX + 0x1c))();
            return 2;
          }
          LeaveCriticalSection(in_EAX + 10);
          return 2;
        }
      }
      uVar5 = uVar5 + 1;
    } while (uVar5 < (uint)in_EAX[0x13] >> 1);
  }
  if (((in_EAX[9] != 0) && (in_EAX[8] != 0)) && (iVar2 = GetCurrentThreadId(), in_EAX[8] == iVar2))
  {
    in_EAX[9] = in_EAX[9] + -1;
    return 0;
  }
  in_EAX[8] = 0;
  if ((char)in_EAX[3] == '\0') {
    (**(code **)(*in_EAX + 0x1c))();
    return 0;
  }
  LeaveCriticalSection(in_EAX + 10);
  return 0;
}


