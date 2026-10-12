// Address: 0072e520
// Function: FUN_0072e520
// Target requested: 0x0072E520

undefined4 * FUN_0072e520(undefined4 *param_1)

{
  int *piVar1;
  int iVar2;
  int *piVar3;
  int iVar4;
  undefined4 uVar5;
  
  *param_1 = &UNK_00c946fc;
  func_0x009dd800();
  *param_1 = &UNK_00cad9dc;
  param_1[1] = &UNK_00cad9fc;
  param_1[0x9e] = 0;
  param_1[0x9f] = 0;
  *(undefined8 *)(param_1 + 0x9c) = 0;
  *(undefined1 *)(param_1 + 0x9a) = 0;
  *(undefined1 *)(param_1 + 0xa0) = 0;
  param_1[0xa1] = 0;
  param_1[0xa2] = 0;
  iVar2 = func_0x0097c5d0(0x298);
  if (iVar2 == 0) {
    piVar3 = (int *)0x0;
  }
  else {
    piVar3 = (int *)func_0x009ce470(iVar2,param_1);
  }
  piVar1 = (int *)param_1[0xa2];
  if (piVar3 != piVar1) {
    if (piVar1 != (int *)0x0) {
      (**(code **)(*piVar1 + 8))();
    }
    param_1[0xa2] = piVar3;
    if (piVar3 != (int *)0x0) {
      (**(code **)(*piVar3 + 4))();
    }
  }
  func_0x009df290();
  *(undefined4 *)(param_1[0xa2] + 0x264) = 0x28;
  iVar2 = *(int *)(param_1[0xa2] + 0x27c);
  iVar4 = func_0x0097c5d0(0x264);
  if (iVar4 != 0) {
    func_0x009dd800();
  }
  func_0x00512220();
  uVar5 = func_0x00409ea0(0,0,0,0);
  func_0x009df010(uVar5);
  uVar5 = func_0x00409ea0(0x3f800000,0x3f800000,(float)-iVar2,0);
  func_0x009df010(uVar5);
  uVar5 = func_0x00409ea0(0,0,0,0);
  func_0x009df060(uVar5);
  uVar5 = func_0x00409ea0(0x3f800000,0x3f800000,0,0);
  func_0x009df060(uVar5);
  func_0x009df290();
  piVar3 = (int *)func_0x0097c5d0(0x2e0);
  if (piVar3 == (int *)0x0) {
    piVar3 = (int *)0x0;
  }
  else {
    func_0x0072e050();
    *piVar3 = (int)&UNK_00cad944;
    piVar3[0xb4] = 0;
    piVar3[0xb5] = 0;
    piVar3[0xb6] = 0;
    piVar3[0xb7] = 0;
  }
  piVar1 = (int *)param_1[0xa1];
  if (piVar3 != piVar1) {
    if (piVar1 != (int *)0x0) {
      (**(code **)(*piVar1 + 8))();
    }
    param_1[0xa1] = piVar3;
    if (piVar3 != (int *)0x0) {
      (**(code **)(*piVar3 + 4))();
    }
  }
  func_0x009df290();
  *(undefined1 *)(param_1[0xa1] + 0x264) = 1;
  func_0x00512220();
  return param_1;
}


