// Address: 0072e330
// Function: FUN_0072e330
// Target requested: 0x0072E330

undefined4 __fastcall FUN_0072e330(int *param_1)

{
  float fVar1;
  int iVar2;
  undefined4 uVar3;
  int *piVar4;
  int iStack_30;
  int iStack_2c;
  int iStack_28;
  int iStack_24;
  undefined1 auStack_20 [4];
  int iStack_1c;
  int iStack_14;
  
  if (*(char *)((int)param_1 + 0x213) == '\0') {
    piVar4 = (int *)param_1[0x91];
  }
  else {
    piVar4 = (int *)0x0;
  }
  (**(code **)(*piVar4 + 0x30))(&iStack_28,0);
  if ((((iStack_30 != param_1[0xb4]) || (iStack_28 != param_1[0xb6])) ||
      (iStack_2c != param_1[0xb5])) || (iStack_24 != param_1[0xb7])) {
    param_1[2] = param_1[2] | 1;
    param_1[0xb4] = iStack_30;
    param_1[0xb5] = iStack_2c;
    param_1[0xb6] = iStack_28;
    param_1[0xb7] = iStack_24;
  }
  if (0.0 < (float)param_1[0x54]) {
    param_1[0xac] = 0;
    param_1[0xad] = 0;
    if (param_1[0xae] != 0) {
      func_0x0097caf0(param_1[0xae]);
    }
    param_1[0xaf] = param_1[0xaf] & 1;
    param_1[0xae] = 0;
    param_1[0xac] = 0;
    param_1[0xad] = 0;
    func_0x009debd0(param_1[0x53],0);
    func_0x009e02a0();
    return 0;
  }
  if ((((*(byte *)(param_1 + 2) & 1) != 0) && ((param_1[0x67] & 0xfffffffeU) != 0)) &&
     (piVar4 = *(int **)param_1[0x66], piVar4 != (int *)0x0)) {
    iVar2 = func_0x00c29990();
    param_1[0x54] = (int)(float)iVar2;
    func_0x009e02a0();
    (**(code **)(*piVar4 + 0x30))(auStack_20,0);
    if (iStack_14 - iStack_1c < iStack_24 - iStack_2c) {
      func_0x005a6250();
      param_1[0xac] = 0;
      param_1[0xad] = 0;
      func_0x009debd0(param_1[0x53],0);
      return 0;
    }
    if (iStack_14 < iStack_24) {
      func_0x005a6250();
      fVar1 = (float)param_1[0x54] - (float)(iStack_14 - iStack_24);
      *(double *)(param_1 + 0xac) = (double)fVar1;
      func_0x009debd0(param_1[0x53],fVar1);
      uVar3 = (**(code **)(*param_1 + 0x38))();
      return uVar3;
    }
  }
  uVar3 = func_0x009e02a0();
  return uVar3;
}


