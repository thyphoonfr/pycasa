// Address: 006b8710
// Function: FUN_006b8710
// Target requested: 0x006B8710

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_006b8710(int *param_1,undefined4 param_2,byte *param_3)

{
  int *piVar1;
  char cVar2;
  int iVar3;
  byte *pbVar4;
  uint *in_stack_00000214;
  int in_stack_00000a34;
  uint *in_stack_00000c3c;
  
  piVar1 = param_1;
  func_0x00bf6b80();
  iVar3 = GetCurrentThreadId();
  if ((param_1[8] == 0) || (param_1[8] != iVar3)) {
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + 10);
    }
    param_1[8] = iVar3;
    param_1[9] = 0;
  }
  else {
    param_1[9] = param_1[9] + 1;
  }
  if (param_1[0x15] != 0) {
    func_0x0097caf0(param_1[0x15]);
  }
  param_1[0x16] = param_1[0x16] & 1;
  param_1[0x15] = 0;
  if (param_1[0x17] != 0) {
    func_0x0097caf0(param_1[0x17]);
  }
  param_1[0x18] = param_1[0x18] & 1;
  param_1[0x17] = 0;
  if (param_1[0x19] != 0) {
    func_0x0097caf0(param_1[0x19]);
  }
  param_1[0x1a] = param_1[0x1a] & 1;
  param_1[0x19] = 0;
  iVar3 = param_1[0x1f];
  if (iVar3 != 0) {
    func_0x00401110(0x14,&SUB_0099db30);
    func_0x0097caf0(iVar3 + -4);
  }
  param_1[0x20] = param_1[0x20] & 1;
  param_1[0x1f] = 0;
  param_1 = (int *)0x0;
  param_2 = 0;
  do {
    func_0x0040ea90(&UNK_00ca8448,param_2);
    FUN_006b5bc0(piVar1 + 0x22,&stack0x00000000);
    func_0x00408b50();
    if (((in_stack_00000c3c == (uint *)0x0) || ((*in_stack_00000c3c & 0xffffff00) == 0)) ||
       ((char)in_stack_00000c3c[1] == '\0')) {
      func_0x00980ec0(0);
    }
    func_0x009a3db0();
    func_0x009a37b0();
    cVar2 = func_0x00992ed0();
    if (cVar2 == '\0') {
      param_1 = (int *)((int)param_1 + 1);
      if (3 < (int)param_1) {
        func_0x00408c00();
        func_0x00401000();
        func_0x00401000();
        break;
      }
    }
    else {
      param_1 = (int *)0x0;
      if (in_stack_00000a34 == 0) {
        func_0x00991f00(0,0);
      }
      else {
        func_0x00991f00(in_stack_00000a34 + 4,0);
      }
    }
    func_0x00408c00();
    func_0x00401000();
    func_0x00401000();
    param_2 = param_2 + 1;
  } while (param_2 < 1000);
  func_0x00408b50();
  if (((in_stack_00000214 == (uint *)0x0) || ((*in_stack_00000214 & 0xffffff00) == 0)) ||
     ((char)in_stack_00000214[1] == '\0')) {
    func_0x00980ec0(0);
  }
  func_0x009a3db0();
  func_0x009a37b0();
  if (param_3 == (byte *)0x0) {
    pbVar4 = (byte *)0x0;
  }
  else {
    pbVar4 = param_3 + 4;
  }
  func_0x00991f00(pbVar4,0);
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  if ((param_3 != (byte *)0x0) && (*param_3 < 0x80)) {
    cVar2 = InterlockedDecrement(param_3);
    if (cVar2 == '\x7f') {
      if (*param_3 < 0x80) {
        cVar2 = InterlockedIncrement(param_3);
      }
      else {
        cVar2 = -1;
      }
    }
    if (cVar2 == '\0') {
      func_0x0097caf0(param_3);
    }
  }
  func_0x006b5cc0();
  piVar1[0x13] = piVar1[0x13] + 1;
  *(undefined1 *)(piVar1 + 0x14) = 1;
  if (((piVar1[9] == 0) || (piVar1[8] == 0)) || (iVar3 = GetCurrentThreadId(), piVar1[8] != iVar3))
  {
    piVar1[8] = 0;
    if ((char)piVar1[3] == '\0') {
      (**(code **)(*piVar1 + 0x1c))();
    }
    else {
      LeaveCriticalSection(piVar1 + 10);
    }
  }
  else {
    piVar1[9] = piVar1[9] + -1;
  }
  func_0x00bef10a();
  return;
}


