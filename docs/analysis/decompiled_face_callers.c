// =========================================================
// Function: FUN_0042a23d @ 0042a23d

undefined1 FUN_0042a23d(void)

{
  int unaff_EBX;
  int *unaff_EDI;
  bool in_ZF;
  undefined1 in_stack_00000044;
  
  if (in_ZF) {
    unaff_EDI[9] = unaff_EDI[9] + 1;
  }
  else {
    if ((char)unaff_EDI[3] == '\0') {
      (**(code **)(*unaff_EDI + 0x18))();
    }
    else {
      EnterCriticalSection();
    }
    unaff_EDI[9] = 0;
    unaff_EDI[8] = unaff_EBX;
  }
  func_0x0041edb0();
  FUN_009b93f0();
  return in_stack_00000044;
}



// =========================================================
// Function: FUN_0042a570 @ 0042a570

undefined4 FUN_0042a570(int param_1,int *param_2)

{
  char cVar1;
  int *in_EAX;
  int iVar2;
  uint *puVar3;
  int *unaff_EBP;
  char *pcVar4;
  bool bVar5;
  int iStack_30;
  uint *puStack_2c;
  int iStack_28;
  int *piStack_24;
  undefined *puStack_20;
  
  if (*(int *)(param_1 + 8) == 0) {
    piStack_24 = (int *)0x0;
  }
  else {
    piStack_24 = (int *)(*(int *)(param_1 + 8) + 4);
  }
  puStack_20 = &UNK_00c80ac4;
  iStack_28 = param_1;
  puStack_2c = (uint *)0x42a59b;
  FUN_0099ac80();
  puStack_2c = *(uint **)(param_1 + 0x10);
  if (((puStack_2c != (uint *)0x0) && ((*puStack_2c & 0xffffff00) != 0)) &&
     ((char)puStack_2c[1] != '\0')) {
    if (((puStack_2c == (uint *)0x0) || ((*puStack_2c & 0xffffff00) == 0)) ||
       ((char)puStack_2c[1] == '\0')) {
      iVar2 = 0;
    }
    else {
      puStack_2c = puStack_2c + 1;
      iStack_30 = 0x42a5cf;
      iVar2 = func_0x00bf6a2d();
    }
    *param_2 = iVar2;
  }
  if (*(int *)(param_1 + 8) == 0) {
    iStack_30 = 0;
  }
  else {
    iStack_30 = *(int *)(param_1 + 8) + 4;
  }
  puStack_2c = (uint *)&UNK_00c80acc;
  FUN_0099ac80(param_1);
  puVar3 = *(uint **)(param_1 + 0x10);
  if (((puVar3 != (uint *)0x0) && ((*puVar3 & 0xffffff00) != 0)) && ((char)puVar3[1] != '\0')) {
    if (((puVar3 == (uint *)0x0) || ((*puVar3 & 0xffffff00) == 0)) || ((char)puVar3[1] == '\0')) {
      iVar2 = 0;
    }
    else {
      iVar2 = func_0x00bf6a2d(puVar3 + 1);
    }
    *in_EAX = iVar2;
  }
  if (*param_2 == 0) {
    return 0;
  }
  if (*in_EAX == 0) {
    return 0;
  }
  if (*(int *)(param_1 + 8) == 0) {
    iVar2 = 0;
  }
  else {
    iVar2 = *(int *)(param_1 + 8) + 4;
  }
  FUN_0099ac80(param_1,iVar2,&UNK_00c812f8);
  puVar3 = *(uint **)(param_1 + 0x10);
  if (((puVar3 != (uint *)0x0) && ((*puVar3 & 0xffffff00) != 0)) &&
     ((((byte)puVar3[1] != 0 && ((puVar3 != (uint *)0x0 && ((*puVar3 & 0xffffff00) != 0)))) &&
      ((byte)puVar3[1] != 0)))) {
    if ((puVar3 != (uint *)0x0) && ((byte)*puVar3 < 0x80)) {
      InterlockedIncrement(puVar3);
    }
    cVar1 = func_0x00987030(0);
    if (cVar1 == '\0') {
      func_0x009b90f0();
    }
    else {
      if ((((puVar3 != (uint *)0x0) && (puVar3 = puVar3 + 1, puVar3 != (uint *)0x0)) &&
          ((byte)*puVar3 != 0)) &&
         (iVar2 = func_0x00c07eef(puVar3,&UNK_00cd9554,&iStack_30), iVar2 == 1)) {
        FUN_009b9190(iStack_30,puStack_2c);
      }
      FUN_009b93f0();
    }
    func_0x00401000();
  }
  *unaff_EBP = 0;
  if (*(int *)(param_1 + 8) == 0) {
    iVar2 = 0;
  }
  else {
    iVar2 = *(int *)(param_1 + 8) + 4;
  }
  FUN_0099ac80(param_1,iVar2,&UNK_00c80ad4);
  puVar3 = *(uint **)(param_1 + 0x10);
  if (((puVar3 == (uint *)0x0) || ((*puVar3 & 0xffffff00) == 0)) || ((char)puVar3[1] == '\0'))
  goto LAB_0042a7cb;
  if (puVar3 != (uint *)0x0) {
    if (puVar3 == (uint *)0xfffffffc) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_0042a7ae;
      bVar5 = false;
    }
    else {
      if (puVar3 == (uint *)0x0) {
        puVar3 = (uint *)0x0;
      }
      else {
        puVar3 = puVar3 + 1;
      }
      iVar2 = 0xb;
      bVar5 = true;
      pcVar4 = "rotate(-1)";
      do {
        if (iVar2 == 0) break;
        iVar2 = iVar2 + -1;
        bVar5 = *pcVar4 == (char)*puVar3;
        pcVar4 = pcVar4 + 1;
        puVar3 = (uint *)((int)puVar3 + 1);
      } while (bVar5);
    }
    if (bVar5) goto LAB_0042a7cb;
  }
LAB_0042a7ae:
  if (*(int *)(param_1 + 0x10) == 0) {
    iVar2 = 0;
  }
  else {
    iVar2 = *(int *)(param_1 + 0x10) + 4;
  }
  func_0x00c07eef(iVar2,&UNK_00c81474,unaff_EBP);
LAB_0042a7cb:
  if (((piStack_24[2] <= *piStack_24) || (piStack_24[3] <= piStack_24[1])) && (*unaff_EBP == 0)) {
    return 0;
  }
  return 1;
}



// Could not create function at 00430832

// =========================================================
// Function: FUN_004467b2 @ 004467b2

undefined4 __thiscall FUN_004467b2(uint param_1)

{
  uint in_EAX;
  int iVar1;
  int *unaff_EBX;
  uint *unaff_EBP;
  int unaff_ESI;
  int iStack00000018;
  int *piStack0000001c;
  int in_stack_00000024;
  
  unaff_EBP[1] = param_1 & 0xffff;
  *unaff_EBP = param_1 >> 0x10;
  unaff_EBP[2] = in_EAX >> 0x10;
  unaff_EBP[3] = in_EAX & 0xffff;
  iStack00000018 = unaff_ESI + 0x13d8;
  piStack0000001c = (int *)(unaff_ESI + 0x13b0);
  iVar1 = GetCurrentThreadId();
  if ((*(int *)(unaff_ESI + 0x13d0) == 0) || (*(int *)(unaff_ESI + 0x13d0) != iVar1)) {
    if (*(char *)(unaff_ESI + 0x13bc) == '\0') {
      (**(code **)(*(int *)(unaff_ESI + 0x13b0) + 0x18))();
    }
    else {
      EnterCriticalSection(unaff_ESI + 0x13d8);
    }
    *(undefined4 *)(unaff_ESI + 0x13d4) = 0;
    *(int *)(unaff_ESI + 0x13d0) = iVar1;
  }
  else {
    *(int *)(unaff_ESI + 0x13d4) = *(int *)(unaff_ESI + 0x13d4) + 1;
  }
  func_0x0041edb0();
  iStack00000018 = in_stack_00000024 + 0x1438;
  piStack0000001c = (int *)(in_stack_00000024 + 0x1410);
  iVar1 = GetCurrentThreadId();
  if ((*(int *)(in_stack_00000024 + 0x1430) == 0) || (*(int *)(in_stack_00000024 + 0x1430) != iVar1)
     ) {
    if (*(char *)(in_stack_00000024 + 0x141c) == '\0') {
      (**(code **)(*(int *)(in_stack_00000024 + 0x1410) + 0x18))();
    }
    else {
      EnterCriticalSection(in_stack_00000024 + 0x1438);
    }
    *(undefined4 *)(in_stack_00000024 + 0x1434) = 0;
    *(int *)(in_stack_00000024 + 0x1430) = iVar1;
  }
  else {
    *(int *)(in_stack_00000024 + 0x1434) = *(int *)(in_stack_00000024 + 0x1434) + 1;
  }
  func_0x0041edb0();
  FUN_009b93f0();
  if (((unaff_EBX[9] != 0) && (unaff_EBX[8] != 0)) &&
     (iVar1 = GetCurrentThreadId(), unaff_EBX[8] == iVar1)) {
    unaff_EBX[9] = unaff_EBX[9] + -1;
    return 0;
  }
  unaff_EBX[8] = 0;
  if ((char)unaff_EBX[3] == '\0') {
    (**(code **)(*unaff_EBX + 0x1c))();
    return 0;
  }
  LeaveCriticalSection(unaff_EBX + 10);
  return 0;
}



// =========================================================
// Function: FUN_004482a1 @ 004482a1

undefined4 FUN_004482a1(undefined4 param_1,int param_2)

{
  uint uVar1;
  uint uVar2;
  char cVar3;
  int iVar4;
  int iVar5;
  uint *puVar6;
  int iVar7;
  int unaff_EBX;
  uint uVar8;
  uint *unaff_EBP;
  int *unaff_ESI;
  int *piVar9;
  undefined4 *puVar10;
  bool in_ZF;
  int in_stack_00000020;
  int in_stack_00000024;
  int in_stack_00000028;
  int in_stack_0000002c;
  int in_stack_00000030;
  int *in_stack_00000034;
  undefined4 in_stack_00000038;
  undefined4 in_stack_0000003c;
  int in_stack_00000040;
  int in_stack_00000044;
  int in_stack_00000048;
  uint in_stack_0000004c;
  uint in_stack_00000050;
  undefined4 in_stack_00000054;
  
  if (in_ZF) {
    unaff_ESI[9] = unaff_ESI[9] + 1;
  }
  else {
    if ((char)unaff_ESI[3] == '\0') {
      (**(code **)(*unaff_ESI + 0x18))();
    }
    else {
      EnterCriticalSection();
    }
    unaff_ESI[9] = 0;
    unaff_ESI[8] = unaff_EBX;
  }
  iVar5 = unaff_ESI[0x16];
  if ((iVar5 == 0) || (*(uint *)(iVar5 + 0x4c) >> 1 <= in_stack_0000004c)) {
    in_stack_00000024 = unaff_ESI[0x19];
    uVar8 = unaff_ESI[0x18];
  }
  else {
    uVar8 = *(uint *)(*(int *)(iVar5 + 0x48) + in_stack_0000004c * 8);
    in_stack_00000024 = *(int *)(*(int *)(iVar5 + 0x48) + 4 + in_stack_0000004c * 8);
  }
  func_0x0041edb0();
  iVar5 = in_stack_00000048;
  if (uVar8 != 0 || in_stack_00000024 != 0) {
    piVar9 = (int *)(in_stack_00000048 + 0x13b0);
    iVar7 = in_stack_00000048 + 0x13d8;
    in_stack_0000004c = 0;
    in_stack_00000054 = 0;
    in_stack_00000030 = iVar7;
    in_stack_00000034 = piVar9;
    iVar4 = GetCurrentThreadId();
    if ((*(int *)(iVar5 + 0x13d0) == 0) || (*(int *)(iVar5 + 0x13d0) != iVar4)) {
      if (*(char *)(iVar5 + 0x13bc) == '\0') {
        (**(code **)(*piVar9 + 0x18))();
      }
      else {
        EnterCriticalSection(iVar7);
      }
      *(undefined4 *)(iVar5 + 0x13d4) = 0;
      *(int *)(iVar5 + 0x13d0) = iVar4;
    }
    else {
      *(int *)(iVar5 + 0x13d4) = *(int *)(iVar5 + 0x13d4) + 1;
    }
    iVar7 = *(int *)(iVar5 + 0x1408);
    if ((iVar7 == 0) || (*(uint *)(iVar7 + 0x4c) >> 1 <= in_stack_00000050)) {
      puVar6 = (uint *)(iVar5 + 0x140c);
    }
    else {
      puVar6 = (uint *)(*(int *)(iVar7 + 0x48) + in_stack_00000050 * 4);
    }
    uVar1 = *puVar6;
    func_0x0041edb0();
    iVar7 = in_stack_00000048;
    piVar9 = (int *)(in_stack_00000048 + 0x1410);
    iVar5 = in_stack_00000048 + 0x1438;
    in_stack_00000030 = iVar5;
    in_stack_00000034 = piVar9;
    iVar4 = GetCurrentThreadId();
    if ((*(int *)(iVar7 + 0x1430) == 0) || (*(int *)(iVar7 + 0x1430) != iVar4)) {
      if (*(char *)(iVar7 + 0x141c) == '\0') {
        (**(code **)(*piVar9 + 0x18))();
      }
      else {
        EnterCriticalSection(iVar5);
      }
      *(undefined4 *)(iVar7 + 0x1434) = 0;
      *(int *)(iVar7 + 0x1430) = iVar4;
    }
    else {
      *(int *)(iVar7 + 0x1434) = *(int *)(iVar7 + 0x1434) + 1;
    }
    uVar2 = in_stack_00000050;
    iVar5 = *(int *)(iVar7 + 0x1468);
    if ((iVar5 == 0) || (*(uint *)(iVar5 + 0x4c) >> 1 <= in_stack_00000050)) {
      puVar10 = (undefined4 *)(iVar7 + 0x146c);
    }
    else {
      puVar10 = (undefined4 *)(*(int *)(iVar5 + 0x48) + in_stack_00000050 * 4);
    }
    in_stack_00000050 = *puVar10;
    func_0x0041edb0();
    in_stack_00000030 = 0;
    in_stack_00000034 = (int *)0x0;
    in_stack_00000038 = 0;
    in_stack_0000003c = 0;
    cVar3 = func_0x0042a440(uVar2,&stack0x0000004c,&stack0x00000054,&stack0x00000018);
    if (cVar3 == '\0') {
      in_stack_00000044 = in_stack_00000040;
    }
    unaff_EBP[1] = uVar1 & 0xffff;
    *unaff_EBP = uVar1 >> 0x10;
    unaff_EBP[2] = uVar8 >> 0x10;
    unaff_EBP[3] = uVar8 & 0xffff;
    FUN_009b93f0();
    if ((in_stack_00000020 < in_stack_00000028) && (in_stack_00000024 < in_stack_0000002c)) {
      *unaff_EBP = *unaff_EBP + -in_stack_00000020;
      unaff_EBP[2] = unaff_EBP[2] + -in_stack_00000020;
      unaff_EBP[1] = unaff_EBP[1] + -in_stack_00000024;
      unaff_EBP[3] = unaff_EBP[3] + -in_stack_00000024;
    }
    if (param_2 != 0) {
      iVar5 = in_stack_00000044;
      iVar7 = in_stack_00000040;
      if ((in_stack_00000020 < in_stack_00000028) && (in_stack_00000024 < in_stack_0000002c)) {
        iVar5 = in_stack_00000028 - in_stack_00000020;
        iVar7 = in_stack_0000002c - in_stack_00000024;
      }
      in_stack_00000020 = 0;
      in_stack_00000024 = 0;
      in_stack_00000028 = iVar5;
      in_stack_0000002c = iVar7;
      puVar6 = (uint *)func_0x009b4c80(&stack0x00000020,param_2);
      *unaff_EBP = *puVar6;
      unaff_EBP[1] = puVar6[1];
      unaff_EBP[2] = puVar6[2];
      unaff_EBP[3] = puVar6[3];
    }
    if (((int)*unaff_EBP < (int)unaff_EBP[2]) && ((int)unaff_EBP[1] < (int)unaff_EBP[3])) {
      return 0;
    }
  }
  *unaff_EBP = 0;
  unaff_EBP[1] = 0;
  unaff_EBP[2] = 0;
  unaff_EBP[3] = 0;
  return 0xffffffff;
}



// =========================================================
// Function: FUN_00464273 @ 00464273

undefined4
FUN_00464273(uint *param_1,int param_2,int param_3,uint param_4,int param_5,int param_6,int param_7,
            int param_8,char *param_9,undefined4 *param_10,int param_11,int param_12,uint param_13,
            int param_14,int param_15,int param_16,int param_17,char *param_18)

{
  char *pcVar1;
  uint *puVar2;
  char cVar3;
  char *in_EAX;
  int iVar4;
  int *piVar5;
  int iVar6;
  undefined4 uVar7;
  char *unaff_EBX;
  int *unaff_EBP;
  bool in_ZF;
  bool bVar8;
  longlong lVar9;
  int *piStack_34;
  undefined *puStack_30;
  undefined *puStack_2c;
  int *piStack_28;
  undefined4 **ppuStack_24;
  undefined4 *in_stack_ffffffe0;
  int *piStack_1c;
  undefined4 *puStack_18;
  undefined4 *puStack_14;
  char *pcStack_c;
  undefined4 *puStack_8;
  
  if ((!in_ZF) && (*in_EAX != (char)unaff_EBX)) {
    puStack_8 = (undefined4 *)&UNK_00cd9554;
    pcStack_c = in_EAX;
    iVar4 = func_0x00c07eef();
    if (iVar4 == 1) {
      puStack_8 = param_10;
      pcStack_c = (char *)0x4642a4;
      FUN_009b9190();
    }
  }
  FUN_009b93f0();
  param_6 = -1;
  param_7 = -1;
  param_8 = -1;
  param_9 = (char *)0xffffffff;
  puStack_8 = (undefined4 *)0x4642f2;
  cVar3 = func_0x00987030();
  if (cVar3 == '\0') {
    puStack_8 = (undefined4 *)0x46435d;
    func_0x009b90f0();
  }
  else {
    if ((((char *)unaff_EBP[0xb] != unaff_EBX) &&
        (pcVar1 = (char *)unaff_EBP[0xb] + 4, pcVar1 != unaff_EBX)) && (*pcVar1 != (char)unaff_EBX))
    {
      puStack_8 = &param_9;
      pcStack_c = "rect64(%I64x)";
      puStack_14 = (undefined4 *)0x464317;
      iVar4 = func_0x00c07eef();
      if (iVar4 == 1) {
        puStack_8 = param_10;
        pcStack_c = param_9;
        FUN_009b9190();
      }
    }
    puStack_8 = (undefined4 *)0x464347;
    FUN_009b93f0();
  }
  iVar4 = param_15;
  if (param_18 != (char *)0x0) {
    if ((param_14 < param_16) && (param_15 < param_17)) {
      if (((uint)param_18 & 1) == 0) {
        param_11 = param_16 - param_14;
        param_12 = param_17 - param_15;
      }
      else {
        param_11 = param_17 - param_15;
        param_12 = param_16 - param_14;
      }
    }
    else {
      if ((param_7 <= param_5) || (param_8 <= param_6)) goto LAB_0046442c;
      if (((uint)param_18 & 1) == 0) {
        param_11 = unaff_EBP[7] - unaff_EBP[5];
        param_12 = unaff_EBP[8] - unaff_EBP[6];
      }
      else {
        param_11 = unaff_EBP[8] - unaff_EBP[6];
        param_12 = unaff_EBP[7] - unaff_EBP[5];
      }
    }
    param_10 = (undefined4 *)0x0;
    param_9 = (char *)0x0;
    puStack_8 = (undefined4 *)-(int)param_18;
    pcStack_c = (char *)&param_9;
    piVar5 = (int *)func_0x009b4c80();
    param_6 = piVar5[1];
    param_5 = *piVar5;
    param_8 = piVar5[3];
    param_7 = piVar5[2];
  }
LAB_0046442c:
  puStack_8 = (undefined4 *)0x464435;
  func_0x004147d0();
  puStack_8 = (undefined4 *)&stack0x0000005c;
  pcStack_c = param_18;
  puStack_14 = (undefined4 *)0x464449;
  func_0x00463cd0();
  puVar2 = (uint *)unaff_EBP[0xc];
  if (((puVar2 != (uint *)0x0) && ((*puVar2 & 0xffffff00) != 0)) && ((char)puVar2[1] != '\0')) {
    puStack_14 = (undefined4 *)0x46446d;
    func_0x0040eae0();
    puStack_14 = (undefined4 *)0x46447b;
    puStack_14 = (undefined4 *)func_0x0049fbe0();
    if (puStack_14 == (undefined4 *)0x0) {
      puStack_18 = (undefined4 *)&stack0x00000050;
      in_stack_ffffffe0 = &param_1;
      ppuStack_24 = (undefined4 **)0x464490;
      piStack_1c = unaff_EBP + 0xc;
      func_0x009089a0();
      if (((param_1 != (uint *)0x0) && ((*param_1 & 0xffffff00) != 0)) && ((char)param_1[1] != '\0')
         ) {
        puStack_14 = (undefined4 *)0x4644b4;
        FUN_005c2100();
      }
      puStack_14 = (undefined4 *)0x4644bd;
      func_0x00401000();
    }
  }
  if ((param_2 < (int)param_4) && (param_3 < param_5)) {
    puStack_14 = (undefined4 *)0x1;
    puStack_18 = (undefined4 *)&UNK_00c814ac;
    piStack_1c = (int *)0x464506;
    iVar6 = func_0x009866e0();
    if (iVar6 != -1) {
      param_1 = (uint *)(unaff_EBP[8] - unaff_EBP[6]);
      param_6 = unaff_EBP[7] - unaff_EBP[5];
      puStack_14 = &param_2;
      puStack_18 = &param_11;
      piStack_1c = (int *)&param_1;
      in_stack_ffffffe0 = &param_6;
      ppuStack_24 = (undefined4 **)(unaff_EBP + 9);
      piStack_28 = (int *)0x46453e;
      func_0x0042c670();
    }
    param_2 = param_2 + param_11;
    param_4 = param_4 + param_11;
    param_3 = param_3 + iVar4;
    param_5 = param_5 + iVar4;
    puStack_14 = (undefined4 *)(unaff_EBP[7] - unaff_EBP[5]);
  }
  else {
    param_2 = param_11;
    puStack_14 = (undefined4 *)(unaff_EBP[7] - unaff_EBP[5]);
    param_3 = iVar4;
    param_4 = param_13;
    param_5 = param_14;
  }
  puStack_18 = (undefined4 *)0x46456b;
  FUN_009b9290();
  puVar2 = param_1;
  param_9 = param_9 + param_14;
  if (((int)param_1 < param_3) && (param_2 < (int)param_4)) {
    puStack_18 = (undefined4 *)0x0;
    piStack_1c = (int *)0x3d;
    ppuStack_24 = (undefined4 **)0x4645a5;
    func_0x00985990();
    ppuStack_24 = (undefined4 **)0x4645b1;
    FUN_005c2100();
    ppuStack_24 = (undefined4 **)0x4645b8;
    func_0x00401000();
    ppuStack_24 = (undefined4 **)0x4645c2;
    func_0x00985a60();
    if (unaff_EBP[0xb] == 0) {
      puStack_30 = (undefined *)0x0;
    }
    else {
      puStack_30 = (undefined *)(unaff_EBP[0xb] + 4);
    }
    piStack_28 = (int *)((uint)param_1 & 0xffff);
    ppuStack_24 = (undefined4 **)((int)puVar2 << 0x10 | (uint)unaff_EBX & 0xffff);
    puStack_2c = &UNK_00cd9554;
    piStack_34 = (int *)0x464612;
    func_0x00c08243();
    ppuStack_24 = &puStack_8;
    piStack_28 = unaff_EBP + 9;
    puStack_2c = (undefined *)0x464623;
    func_0x00463590();
    in_stack_ffffffe0 = (undefined4 *)register0x00000010;
  }
  else {
    puStack_18 = (undefined4 *)0x464630;
    FUN_005c2100();
  }
  if (param_4 == 0) {
    puStack_2c = (undefined *)0x4646ac;
    FUN_005c2100();
  }
  else {
    if ((int)param_4 < 0) {
      param_4 = 0;
    }
    param_4 = param_4 & 0x80000003;
    bVar8 = false;
    if ((int)param_4 < 0) {
      param_4 = (param_4 - 1 | 0xfffffffc) + 1;
      bVar8 = (int)param_4 < 0;
    }
    if (bVar8) {
      param_4 = param_4 + 4 + (-param_4 - 1 & 0xfffffffc);
    }
    if (3 < (int)param_4) {
      param_4 = param_4 + (param_4 - 4 >> 2) * -4 + -4;
    }
    if (param_4 == 0) {
      puStack_2c = (undefined *)0x464699;
      func_0x00401000();
      unaff_EBP[10] = 0;
    }
    else {
      puStack_30 = &UNK_00c81474;
      piStack_34 = (int *)0x46468c;
      puStack_2c = (undefined *)param_4;
      func_0x0040eab0();
    }
  }
  puStack_2c = (undefined *)0x1;
  puStack_30 = &UNK_00c81978;
  piStack_34 = (int *)0x4646bc;
  iVar4 = func_0x009866e0();
  if (iVar4 != -1) {
    piStack_34 = (int *)0x1;
    iVar4 = func_0x009866e0(&UNK_00c81978);
    if (iVar4 == -1) {
      piStack_34 = (int *)0x1;
      iVar4 = func_0x009866e0(&UNK_00c81984);
      if (iVar4 == -1) goto LAB_004647fc;
    }
    lVar9 = 0;
    if (*unaff_EBP == 0) {
      iVar4 = 0;
    }
    else {
      iVar4 = *unaff_EBP + 4;
      lVar9 = 0;
    }
    do {
      piStack_34 = (int *)&UNK_00c81978;
      iVar4 = func_0x00c07f40(iVar4);
      if (iVar4 == 0) break;
      piStack_34 = (int *)(iVar4 + 0xb);
      piStack_1c = (int *)0x0;
      piVar5 = piStack_34;
      if (piStack_34 != (int *)0x0) {
        do {
          iVar6 = *piVar5;
          piVar5 = (int *)((int)piVar5 + 1);
        } while ((char)iVar6 != '\0');
        func_0x00985ff0();
      }
      piStack_34 = (int *)0x464750;
      lVar9 = func_0x0049fb50();
      iVar4 = iVar4 + 0xc;
      piStack_34 = (int *)0x464762;
      func_0x00401000();
    } while (iVar4 != 0);
    if (lVar9 != 0) {
      piStack_34 = (int *)&UNK_00c813e4;
      piStack_1c = (int *)0x0;
      func_0x00985ff0();
      uVar7 = func_0x009ae560(&UNK_00c8199c,(int)lVar9,puStack_8);
      func_0x00463840(unaff_EBP + 9,&piStack_1c,uVar7);
      func_0x00401000();
      piStack_34 = (int *)0x0;
      func_0x00985ff0(&UNK_00c819d8);
      uVar7 = func_0x009ae560(&UNK_00c819c0,(int)lVar9,in_stack_ffffffe0);
      func_0x00463840(unaff_EBP + 9,&piStack_34,uVar7);
      func_0x00401000();
    }
  }
LAB_004647fc:
  piStack_34 = unaff_EBP + 9;
  func_0x00408760();
  FUN_005c2100();
  func_0x00401000();
  func_0x00a4e6f0(&pcStack_c,unaff_EBP + 3,unaff_EBP + 0xc);
  FUN_005c2100();
  func_0x00401000();
  *(byte *)(unaff_EBP + 0xd) = *(byte *)(unaff_EBP + 0xd) | *(byte *)(unaff_EBP + 4);
  cVar3 = func_0x00987030(0);
  if ((((cVar3 == '\0') && (cVar3 = func_0x00987030(0), cVar3 == '\0')) &&
      (cVar3 = func_0x00987030(0), cVar3 == '\0')) &&
     (cVar3 = func_0x00987150(&UNK_00c8194c,0), cVar3 == '\0')) {
    return 1000000;
  }
  return 0xf4242;
}



// =========================================================
// Function: FUN_00464301 @ 00464301

undefined4
FUN_00464301(int param_1,uint *param_2,int param_3,int param_4,uint param_5,int param_6,int param_7,
            int param_8,int param_9,undefined4 *param_10,undefined4 *param_11,int param_12,
            int param_13,uint param_14,int param_15,int param_16,int param_17,int param_18,
            undefined4 *param_19)

{
  uint *puVar1;
  char cVar2;
  char *in_EAX;
  int iVar3;
  int *piVar4;
  int iVar5;
  undefined4 uVar6;
  char unaff_BL;
  int *unaff_EBP;
  bool in_ZF;
  bool bVar7;
  longlong lVar8;
  ushort unaff_retaddr;
  int *piStack_30;
  undefined *puStack_2c;
  undefined *puStack_28;
  int *piStack_24;
  undefined4 **ppuStack_20;
  undefined4 *puStack_1c;
  int *piStack_18;
  undefined4 *puStack_14;
  undefined4 *puStack_10;
  undefined4 *puStack_8;
  undefined4 *puStack_4;
  
  if ((!in_ZF) && (*in_EAX != unaff_BL)) {
    puStack_4 = &param_10;
    puStack_8 = (undefined4 *)&UNK_00cd9554;
    puStack_10 = (undefined4 *)0x464317;
    iVar3 = func_0x00c07eef();
    if (iVar3 == 1) {
      puStack_4 = param_11;
      puStack_8 = param_10;
      FUN_009b9190();
    }
  }
  puStack_4 = (undefined4 *)0x464347;
  FUN_009b93f0();
  iVar3 = param_16;
  if (param_19 != (undefined4 *)0x0) {
    if ((param_15 < param_17) && (param_16 < param_18)) {
      if (((uint)param_19 & 1) == 0) {
        param_12 = param_17 - param_15;
        param_13 = param_18 - param_16;
      }
      else {
        param_12 = param_18 - param_16;
        param_13 = param_17 - param_15;
      }
    }
    else {
      if ((param_8 <= param_6) || (param_9 <= param_7)) goto LAB_0046442c;
      if (((uint)param_19 & 1) == 0) {
        param_12 = unaff_EBP[7] - unaff_EBP[5];
        param_13 = unaff_EBP[8] - unaff_EBP[6];
      }
      else {
        param_12 = unaff_EBP[8] - unaff_EBP[6];
        param_13 = unaff_EBP[7] - unaff_EBP[5];
      }
    }
    param_11 = (undefined4 *)0x0;
    param_10 = (undefined4 *)0x0;
    puStack_4 = (undefined4 *)-(int)param_19;
    puStack_8 = &param_10;
    piVar4 = (int *)func_0x009b4c80();
    param_7 = piVar4[1];
    param_6 = *piVar4;
    param_9 = piVar4[3];
    param_8 = piVar4[2];
  }
LAB_0046442c:
  puStack_4 = (undefined4 *)0x464435;
  func_0x004147d0();
  puStack_4 = (undefined4 *)&stack0x00000060;
  puStack_8 = param_19;
  puStack_10 = (undefined4 *)0x464449;
  func_0x00463cd0();
  puVar1 = (uint *)unaff_EBP[0xc];
  if (((puVar1 != (uint *)0x0) && ((*puVar1 & 0xffffff00) != 0)) && ((char)puVar1[1] != '\0')) {
    puStack_10 = (undefined4 *)0x46446d;
    func_0x0040eae0();
    puStack_10 = (undefined4 *)0x46447b;
    puStack_10 = (undefined4 *)func_0x0049fbe0();
    if (puStack_10 == (undefined4 *)0x0) {
      puStack_14 = (undefined4 *)&stack0x00000054;
      puStack_1c = &param_2;
      ppuStack_20 = (undefined4 **)0x464490;
      piStack_18 = unaff_EBP + 0xc;
      func_0x009089a0();
      if (((param_2 != (uint *)0x0) && ((*param_2 & 0xffffff00) != 0)) && ((char)param_2[1] != '\0')
         ) {
        puStack_10 = (undefined4 *)0x4644b4;
        FUN_005c2100();
      }
      puStack_10 = (undefined4 *)0x4644bd;
      func_0x00401000();
    }
  }
  if ((param_3 < (int)param_5) && (param_4 < param_6)) {
    puStack_10 = (undefined4 *)0x1;
    puStack_14 = (undefined4 *)&UNK_00c814ac;
    piStack_18 = (int *)0x464506;
    iVar5 = func_0x009866e0();
    if (iVar5 != -1) {
      param_2 = (uint *)(unaff_EBP[8] - unaff_EBP[6]);
      param_7 = unaff_EBP[7] - unaff_EBP[5];
      puStack_10 = &param_3;
      puStack_14 = &param_12;
      piStack_18 = (int *)&param_2;
      puStack_1c = &param_7;
      ppuStack_20 = (undefined4 **)(unaff_EBP + 9);
      piStack_24 = (int *)0x46453e;
      func_0x0042c670();
    }
    param_3 = param_3 + param_12;
    param_5 = param_5 + param_12;
    param_4 = param_4 + iVar3;
    param_6 = param_6 + iVar3;
    puStack_10 = (undefined4 *)(unaff_EBP[7] - unaff_EBP[5]);
  }
  else {
    param_3 = param_12;
    puStack_10 = (undefined4 *)(unaff_EBP[7] - unaff_EBP[5]);
    param_4 = iVar3;
    param_5 = param_14;
    param_6 = param_15;
  }
  puStack_14 = (undefined4 *)0x46456b;
  FUN_009b9290();
  puVar1 = param_2;
  param_10 = (undefined4 *)((int)param_10 + param_15);
  if (((int)param_2 < param_4) && (param_3 < (int)param_5)) {
    puStack_14 = (undefined4 *)0x0;
    piStack_18 = (int *)0x3d;
    puStack_1c = &param_1;
    param_1 = 0;
    ppuStack_20 = (undefined4 **)0x4645a5;
    func_0x00985990();
    ppuStack_20 = (undefined4 **)0x4645b1;
    FUN_005c2100();
    ppuStack_20 = (undefined4 **)0x4645b8;
    func_0x00401000();
    ppuStack_20 = (undefined4 **)0x4645c2;
    func_0x00985a60();
    if (unaff_EBP[0xb] == 0) {
      puStack_2c = (undefined *)0x0;
    }
    else {
      puStack_2c = (undefined *)(unaff_EBP[0xb] + 4);
    }
    ppuStack_20 = (undefined4 **)((int)puVar1 << 0x10 | (uint)unaff_retaddr);
    piStack_24 = (int *)(param_1 << 0x10 | (uint)param_2 & 0xffff);
    puStack_28 = &UNK_00cd9554;
    piStack_30 = (int *)0x464612;
    func_0x00c08243();
    ppuStack_20 = &puStack_4;
    piStack_24 = unaff_EBP + 9;
    puStack_28 = (undefined *)0x464623;
    func_0x00463590();
  }
  else {
    puStack_14 = (undefined4 *)0x464630;
    FUN_005c2100();
  }
  if (param_5 == 0) {
    puStack_28 = (undefined *)0x4646ac;
    FUN_005c2100();
  }
  else {
    if ((int)param_5 < 0) {
      param_5 = 0;
    }
    param_5 = param_5 & 0x80000003;
    bVar7 = false;
    if ((int)param_5 < 0) {
      param_5 = (param_5 - 1 | 0xfffffffc) + 1;
      bVar7 = (int)param_5 < 0;
    }
    if (bVar7) {
      param_5 = param_5 + 4 + (-param_5 - 1 & 0xfffffffc);
    }
    if (3 < (int)param_5) {
      param_5 = param_5 + (param_5 - 4 >> 2) * -4 + -4;
    }
    if (param_5 == 0) {
      puStack_28 = (undefined *)0x464699;
      func_0x00401000();
      unaff_EBP[10] = 0;
    }
    else {
      puStack_2c = &UNK_00c81474;
      piStack_30 = (int *)0x46468c;
      puStack_28 = (undefined *)param_5;
      func_0x0040eab0();
    }
  }
  puStack_28 = (undefined *)0x1;
  puStack_2c = &UNK_00c81978;
  piStack_30 = (int *)0x4646bc;
  iVar3 = func_0x009866e0();
  if (iVar3 != -1) {
    piStack_30 = (int *)0x1;
    iVar3 = func_0x009866e0(&UNK_00c81978);
    if (iVar3 == -1) {
      piStack_30 = (int *)0x1;
      iVar3 = func_0x009866e0(&UNK_00c81984);
      if (iVar3 == -1) goto LAB_004647fc;
    }
    lVar8 = 0;
    if (*unaff_EBP == 0) {
      iVar3 = 0;
    }
    else {
      iVar3 = *unaff_EBP + 4;
      lVar8 = 0;
    }
    do {
      piStack_30 = (int *)&UNK_00c81978;
      iVar3 = func_0x00c07f40(iVar3);
      if (iVar3 == 0) break;
      piStack_30 = (int *)(iVar3 + 0xb);
      piStack_18 = (int *)0x0;
      piVar4 = piStack_30;
      if (piStack_30 != (int *)0x0) {
        do {
          iVar5 = *piVar4;
          piVar4 = (int *)((int)piVar4 + 1);
        } while ((char)iVar5 != '\0');
        func_0x00985ff0();
      }
      piStack_30 = (int *)0x464750;
      lVar8 = func_0x0049fb50();
      iVar3 = iVar3 + 0xc;
      piStack_30 = (int *)0x464762;
      func_0x00401000();
    } while (iVar3 != 0);
    if (lVar8 != 0) {
      piStack_30 = (int *)&UNK_00c813e4;
      piStack_18 = (int *)0x0;
      func_0x00985ff0();
      uVar6 = func_0x009ae560(&UNK_00c8199c,(int)lVar8,puStack_4);
      func_0x00463840(unaff_EBP + 9,&piStack_18,uVar6);
      func_0x00401000();
      piStack_30 = (int *)0x0;
      func_0x00985ff0(&UNK_00c819d8);
      uVar6 = func_0x009ae560(&UNK_00c819c0,(int)lVar8,puStack_1c);
      func_0x00463840(unaff_EBP + 9,&piStack_30,uVar6);
      func_0x00401000();
    }
  }
LAB_004647fc:
  piStack_30 = unaff_EBP + 9;
  func_0x00408760();
  FUN_005c2100();
  func_0x00401000();
  func_0x00a4e6f0(&puStack_8,unaff_EBP + 3,unaff_EBP + 0xc);
  FUN_005c2100();
  func_0x00401000();
  *(byte *)(unaff_EBP + 0xd) = *(byte *)(unaff_EBP + 0xd) | *(byte *)(unaff_EBP + 4);
  cVar2 = func_0x00987030(0);
  if ((((cVar2 == '\0') && (cVar2 = func_0x00987030(0), cVar2 == '\0')) &&
      (cVar2 = func_0x00987030(0), cVar2 == '\0')) &&
     (cVar2 = func_0x00987150(&UNK_00c8194c,0), cVar2 == '\0')) {
    return 1000000;
  }
  return 0xf4242;
}



// Could not create function at 00470629

// =========================================================
// Function: FUN_0047db16 @ 0047db16

/* WARNING: Removing unreachable block (ram,0x0047e38a) */
/* WARNING: Removing unreachable block (ram,0x0047e129) */
/* WARNING: Removing unreachable block (ram,0x0047e258) */
/* WARNING: Removing unreachable block (ram,0x0047de88) */
/* WARNING: Removing unreachable block (ram,0x0047dfbd) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __fastcall FUN_0047db16(int param_1,uint param_2)

{
  int iVar1;
  int iVar2;
  int iVar3;
  float fVar4;
  char cVar5;
  int in_EAX;
  int iVar6;
  uint uVar7;
  uint uVar8;
  int iVar9;
  uint uVar10;
  int *unaff_EBX;
  int *unaff_EBP;
  uint unaff_ESI;
  undefined4 *puVar11;
  uint uVar12;
  int *piVar13;
  undefined4 *puVar14;
  undefined4 *puVar15;
  bool bVar16;
  uint in_stack_00000010;
  int *in_stack_00000014;
  uint in_stack_00000018;
  int in_stack_00000048;
  uint in_stack_0000004c;
  int in_stack_00000050;
  uint uStack00000054;
  int in_stack_00000058;
  uint in_stack_0000005c;
  undefined4 in_stack_00000094;
  
  do {
    param_1 = param_1 + -1;
    iVar6 = 0;
  } while (param_1 != 0);
  do {
    *(int *)(unaff_ESI + 4 + in_EAX) = iVar6;
    uStack00000054 = param_2;
LAB_0047db20:
    do {
      do {
        if (((unaff_EBP[9] == 0) || (unaff_EBP[8] == 0)) ||
           (iVar6 = GetCurrentThreadId(), unaff_EBP[8] != iVar6)) {
          unaff_EBP[8] = 0;
          if ((char)unaff_EBP[3] == '\0') {
            (**(code **)(*unaff_EBP + 0x1c))();
          }
          else {
            LeaveCriticalSection(unaff_EBP + 10);
          }
        }
        else {
          unaff_EBP[9] = unaff_EBP[9] + -1;
        }
        in_stack_00000010 = in_stack_00000010 + 1;
        if (in_stack_00000018 <= in_stack_00000010) {
          in_stack_00000010 = 0;
          if (in_stack_00000018 != 0) goto LAB_0047db90;
          goto LAB_0047e42e;
        }
        uVar8 = *(uint *)(in_stack_00000058 + in_stack_00000010 * 4);
        iVar6 = GetCurrentThreadId();
        if ((unaff_EBX[8] == 0) || (unaff_EBX[8] != iVar6)) {
          if ((char)unaff_EBX[3] == '\0') {
            (**(code **)(*unaff_EBX + 0x18))();
          }
          else {
            EnterCriticalSection(unaff_EBX + 10);
          }
          unaff_EBX[9] = 0;
          unaff_EBX[8] = iVar6;
        }
        else {
          unaff_EBX[9] = unaff_EBX[9] + 1;
        }
        iVar6 = unaff_EBX[0x16];
        if ((iVar6 == 0) || (*(uint *)(iVar6 + 0x4c) >> 1 <= uVar8)) {
          piVar13 = unaff_EBX + 0x17;
        }
        else {
          piVar13 = (int *)(*(int *)(iVar6 + 0x48) + uVar8 * 4);
        }
        if ((in_stack_0000004c & 1) == 0) {
          uVar7 = in_stack_0000004c >> 1;
          if (uVar7 * 4 < 0x100000) {
            uVar10 = uVar7;
            unaff_EBP = in_stack_00000014;
            if ((uVar7 & uVar7 - 1) == 0) {
              if (uVar7 == 0) {
                uVar10 = 1;
              }
              else {
                uVar10 = uVar7 * 2;
              }
            }
          }
          else {
            uVar10 = (uVar7 & 0x7ffffc00) + 0x400;
          }
          if (uVar7 < uVar10) {
            if (uVar10 == 0) {
              if (in_stack_00000048 != 0) {
                func_0x0097caf0(in_stack_00000048);
                in_stack_00000048 = 0;
              }
              goto LAB_0047d9d6;
            }
            in_stack_00000048 = func_0x0097c810(in_stack_00000048,uVar10 * 4);
          }
          if (in_stack_00000048 != 0) {
            in_stack_0000004c = (in_stack_0000004c & 0xfffffffe) + 2;
            *(int *)(uVar7 * 4 + in_stack_00000048) = *piVar13;
          }
        }
LAB_0047d9d6:
        if (((unaff_EBX[9] == 0) || (unaff_EBX[8] == 0)) ||
           (iVar6 = GetCurrentThreadId(), unaff_EBX[8] != iVar6)) {
          unaff_EBX[8] = 0;
          if ((char)unaff_EBX[3] == '\0') {
            (**(code **)(*unaff_EBX + 0x1c))();
          }
          else {
            LeaveCriticalSection(unaff_EBX + 10);
          }
        }
        else {
          unaff_EBX[9] = unaff_EBX[9] + -1;
        }
        iVar6 = GetCurrentThreadId();
        if ((unaff_EBP[8] == 0) || (unaff_EBP[8] != iVar6)) {
          if ((char)unaff_EBP[3] == '\0') {
            (**(code **)(*unaff_EBP + 0x18))();
          }
          else {
            EnterCriticalSection(unaff_EBP + 10);
          }
          unaff_EBP[9] = 0;
          unaff_EBP[8] = iVar6;
        }
        else {
          unaff_EBP[9] = unaff_EBP[9] + 1;
        }
        iVar6 = unaff_EBP[0x16];
        if ((iVar6 == 0) || (*(uint *)(iVar6 + 0x4c) >> 1 <= uVar8)) {
          piVar13 = unaff_EBP + 0x18;
        }
        else {
          piVar13 = (int *)(*(int *)(iVar6 + 0x48) + uVar8 * 8);
        }
      } while ((uStack00000054 & 1) != 0);
      uVar8 = uStack00000054 >> 1;
      unaff_ESI = uVar8 * 8;
      if (unaff_ESI < 0x100000) {
        uVar7 = uVar8;
        unaff_EBP = in_stack_00000014;
        if ((uVar8 & uVar8 - 1) == 0) {
          if (uVar8 == 0) {
            uVar7 = 1;
          }
          else {
            uVar7 = uVar8 * 2;
          }
        }
      }
      else {
        uVar7 = (uVar8 & 0x7ffffc00) + 0x400;
      }
      if (uVar8 < uVar7) {
        if (uVar7 == 0) {
          if (in_stack_00000050 != 0) {
            func_0x0097caf0(in_stack_00000050);
            in_stack_00000050 = 0;
          }
          goto LAB_0047db20;
        }
        in_stack_00000050 = func_0x0097c810(in_stack_00000050,uVar7 * 8);
      }
    } while (in_stack_00000050 == 0);
    *(int *)(unaff_ESI + in_stack_00000050) = *piVar13;
    iVar6 = piVar13[1];
    param_2 = (uStack00000054 & 0xfffffffe) + 2;
    in_EAX = in_stack_00000050;
  } while( true );
LAB_0047db90:
  iVar6 = *(int *)(in_stack_00000048 + in_stack_00000010 * 4);
  iVar1 = *(int *)(in_stack_00000050 + in_stack_00000010 * 8);
  iVar2 = *(int *)(in_stack_00000050 + 4 + in_stack_00000010 * 8);
  FUN_009b93f0();
  in_stack_00000014 = (int *)(in_stack_00000010 + 1);
  if (in_stack_00000014 < in_stack_00000018) {
LAB_0047dc00:
    iVar9 = *(int *)(in_stack_00000050 + 4 + (int)in_stack_00000014 * 8);
    iVar3 = *(int *)(in_stack_00000050 + (int)in_stack_00000014 * 8);
    puVar15 = (undefined4 *)(in_stack_00000050 + (int)in_stack_00000014 * 8);
    FUN_009b93f0();
    if (((iVar1 != iVar3) || (iVar2 != iVar9)) && (cVar5 = func_0x0047d680(), cVar5 == '\0'))
    goto LAB_0047e049;
    if (iVar6 != 0) {
      iVar9 = *(int *)(in_stack_00000048 + (int)in_stack_00000014 * 4);
      puVar11 = (undefined4 *)(in_stack_00000048 + (int)in_stack_00000014 * 4);
      if ((iVar9 == 0) || (iVar6 == iVar9)) {
        func_0x00506ac0(in_stack_00000094,
                        *(undefined4 *)(in_stack_00000058 + (int)in_stack_00000014 * 4));
        if (((in_stack_0000005c & 1) == 0) && (in_stack_00000018 != 0)) {
          uVar8 = in_stack_00000018 - 1;
          for (uVar7 = (uint)in_stack_00000014; uVar7 < uVar8; uVar7 = uVar7 + 1) {
            *(undefined4 *)(in_stack_00000058 + uVar7 * 4) =
                 *(undefined4 *)(in_stack_00000058 + 4 + uVar7 * 4);
          }
          if (uVar8 < 0x20000000) {
            if (uVar8 != in_stack_00000018) {
              if (uVar8 * 4 < 0x100000) {
                uVar7 = 1;
                if (uVar8 != 0) {
                  do {
                    uVar7 = uVar7 * 2;
                  } while (uVar7 <= uVar8);
                }
              }
              else {
                uVar7 = (uVar8 & 0xfffffc00) + 0x400;
              }
              if (in_stack_00000018 * 4 < 0x100000) {
                if (1 < in_stack_00000018) {
                  fVar4 = (float)(int)in_stack_00000018;
                  if ((int)in_stack_00000018 < 0) {
                    fVar4 = fVar4 + _DAT_00cf39e4;
                  }
                  uVar10 = 1 << ((char)((uint)fVar4 >> 0x17) + 0x81U & 0x1f);
                  bVar16 = uVar10 < in_stack_00000018;
                  in_stack_00000018 = uVar10;
                  if (bVar16) {
                    in_stack_00000018 = uVar10 * 2;
                  }
                }
              }
              else {
                in_stack_00000018 = (in_stack_00000018 & 0x7ffffc00) + 0x400;
              }
              if (in_stack_00000018 == uVar7) {
LAB_0047ddd3:
                in_stack_0000005c = uVar8 * 2;
              }
              else {
                if (uVar7 == 0) {
                  if (in_stack_00000058 != 0) {
                    func_0x0097caf0(in_stack_00000058);
                    in_stack_00000058 = 0;
                    in_stack_0000005c = 0;
                    goto LAB_0047ddda;
                  }
                }
                else {
                  in_stack_00000058 = func_0x0097c810(in_stack_00000058,uVar7 * 4);
                  if (in_stack_00000058 != 0) goto LAB_0047ddd3;
                }
                in_stack_00000058 = 0;
                in_stack_0000005c = 0;
              }
            }
          }
          else {
            if (in_stack_00000058 != 0) {
              func_0x0097caf0(in_stack_00000058);
            }
            in_stack_00000058 = 0;
            in_stack_0000005c = 0;
          }
        }
LAB_0047ddda:
        if (((in_stack_0000004c & 1) == 0) && (uVar8 = in_stack_0000004c >> 1, uVar8 != 0)) {
          uVar7 = uVar8 - 1;
          if (in_stack_00000014 < uVar7) {
            puVar14 = puVar11;
            for (iVar9 = uVar7 - (int)in_stack_00000014; puVar11 = puVar11 + 1, iVar9 != 0;
                iVar9 = iVar9 + -1) {
              *puVar14 = *puVar11;
              puVar14 = puVar14 + 1;
            }
          }
          if (uVar7 < 0x20000000) {
            if (uVar7 != uVar8) {
              if (uVar7 * 4 < 0x100000) {
                uVar10 = 1;
                if (uVar7 != 0) {
                  do {
                    uVar10 = uVar10 * 2;
                  } while (uVar10 <= uVar7);
                }
              }
              else {
                uVar10 = (uVar7 & 0xfffffc00) + 0x400;
              }
              if (uVar8 * 4 < 0x100000) {
                if ((1 < uVar8) &&
                   (uVar12 = 1 << ((char)((uint)(float)uVar8 >> 0x17) + 0x81U & 0x1f),
                   bVar16 = uVar12 < uVar8, uVar8 = uVar12, bVar16)) {
                  uVar8 = uVar12 * 2;
                }
              }
              else {
                uVar8 = (uVar8 & 0x7ffffc00) + 0x400;
              }
              if (uVar8 == uVar10) {
LAB_0047df02:
                in_stack_0000004c = uVar7 * 2;
              }
              else {
                if (uVar10 == 0) {
                  if (in_stack_00000048 != 0) {
                    func_0x0097caf0(in_stack_00000048);
                    in_stack_00000048 = 0;
                    in_stack_0000004c = 0;
                    goto LAB_0047df09;
                  }
                }
                else {
                  in_stack_00000048 = func_0x0097c810(in_stack_00000048,uVar10 * 4);
                  if (in_stack_00000048 != 0) goto LAB_0047df02;
                }
                in_stack_00000048 = 0;
                in_stack_0000004c = 0;
              }
            }
          }
          else {
            if (in_stack_00000048 != 0) {
              func_0x0097caf0(in_stack_00000048);
            }
            in_stack_00000048 = 0;
            in_stack_0000004c = 0;
          }
        }
LAB_0047df09:
        if (((uStack00000054 & 1) == 0) && (uVar8 = uStack00000054 >> 1, uVar8 != 0)) {
          uVar7 = uVar8 - 1;
          if (in_stack_00000014 < uVar7) {
            puVar11 = puVar15 + 2;
            for (uVar10 = (uVar7 - (int)in_stack_00000014) * 2 & 0x3ffffffe; uVar10 != 0;
                uVar10 = uVar10 - 1) {
              *puVar15 = *puVar11;
              puVar11 = puVar11 + 1;
              puVar15 = puVar15 + 1;
            }
          }
          if (uVar7 < 0x10000000) {
            if (uVar7 != uVar8) {
              if (uVar7 * 8 < 0x100000) {
                uVar10 = 1;
                if (uVar7 != 0) {
                  do {
                    uVar10 = uVar10 * 2;
                  } while (uVar10 <= uVar7);
                }
              }
              else {
                uVar10 = (uVar7 & 0xfffffc00) + 0x400;
              }
              if (uVar8 * 8 < 0x100000) {
                if ((1 < uVar8) &&
                   (uVar12 = 1 << ((char)((uint)(float)uVar8 >> 0x17) + 0x81U & 0x1f),
                   bVar16 = uVar12 < uVar8, uVar8 = uVar12, bVar16)) {
                  uVar8 = uVar12 * 2;
                }
              }
              else {
                uVar8 = (uVar8 & 0x7ffffc00) + 0x400;
              }
              if (uVar8 == uVar10) {
LAB_0047e039:
                uStack00000054 = uVar7 * 2;
              }
              else {
                if (uVar10 == 0) {
                  if (in_stack_00000050 != 0) {
                    func_0x0097caf0(in_stack_00000050);
                    in_stack_00000050 = 0;
                    uStack00000054 = 0;
                    goto LAB_0047e040;
                  }
                }
                else {
                  in_stack_00000050 = func_0x0097c810(in_stack_00000050,uVar10 * 8);
                  if (in_stack_00000050 != 0) goto LAB_0047e039;
                }
                in_stack_00000050 = 0;
                uStack00000054 = 0;
              }
            }
          }
          else {
            if (in_stack_00000050 != 0) {
              func_0x0097caf0(in_stack_00000050);
            }
            in_stack_00000050 = 0;
            uStack00000054 = 0;
          }
        }
LAB_0047e040:
        in_stack_00000014 = (int *)((int)in_stack_00000014 - 1);
      }
      goto LAB_0047e049;
    }
    func_0x00506ac0(in_stack_00000094,*(undefined4 *)(in_stack_00000058 + in_stack_00000010 * 4));
    if (((in_stack_0000005c & 1) == 0) && (uVar8 = in_stack_0000005c >> 1, uVar8 != 0)) {
      uVar7 = uVar8 - 1;
      for (uVar10 = in_stack_00000010; uVar10 < uVar7; uVar10 = uVar10 + 1) {
        *(undefined4 *)(in_stack_00000058 + uVar10 * 4) =
             *(undefined4 *)(in_stack_00000058 + 4 + uVar10 * 4);
      }
      if (uVar7 < 0x20000000) {
        if (uVar7 != uVar8) {
          if (uVar7 * 4 < 0x100000) {
            uVar10 = 1;
            if (uVar7 != 0) {
              do {
                uVar10 = uVar10 * 2;
              } while (uVar10 <= uVar7);
            }
          }
          else {
            uVar10 = (uVar7 & 0xfffffc00) + 0x400;
          }
          if (uVar8 * 4 < 0x100000) {
            if ((1 < uVar8) &&
               (uVar12 = 1 << ((char)((uint)(float)uVar8 >> 0x17) + 0x81U & 0x1f),
               bVar16 = uVar12 < uVar8, uVar8 = uVar12, bVar16)) {
              uVar8 = uVar12 * 2;
            }
          }
          else {
            uVar8 = (uVar8 & 0x7ffffc00) + 0x400;
          }
          if (uVar8 == uVar10) {
LAB_0047e1a4:
            in_stack_0000005c = uVar7 * 2;
          }
          else {
            if (uVar10 == 0) {
              if (in_stack_00000058 != 0) {
                func_0x0097caf0(in_stack_00000058);
                in_stack_00000058 = 0;
                in_stack_0000005c = 0;
                goto LAB_0047e1ab;
              }
            }
            else {
              in_stack_00000058 = func_0x0097c810(in_stack_00000058,uVar10 * 4);
              if (in_stack_00000058 != 0) goto LAB_0047e1a4;
            }
            in_stack_00000058 = 0;
            in_stack_0000005c = 0;
          }
        }
      }
      else {
        if (in_stack_00000058 != 0) {
          func_0x0097caf0(in_stack_00000058);
        }
        in_stack_00000058 = 0;
        in_stack_0000005c = 0;
      }
    }
LAB_0047e1ab:
    if (((in_stack_0000004c & 1) == 0) && (uVar8 = in_stack_0000004c >> 1, uVar8 != 0)) {
      uVar7 = uVar8 - 1;
      if (in_stack_00000010 < uVar7) {
        puVar15 = (undefined4 *)(in_stack_00000048 + in_stack_00000010 * 4);
        puVar11 = puVar15;
        for (iVar6 = uVar7 - in_stack_00000010; puVar15 = puVar15 + 1, iVar6 != 0;
            iVar6 = iVar6 + -1) {
          *puVar11 = *puVar15;
          puVar11 = puVar11 + 1;
        }
      }
      if (uVar7 < 0x20000000) {
        if (uVar7 != uVar8) {
          if (uVar7 * 4 < 0x100000) {
            uVar10 = 1;
            if (uVar7 != 0) {
              do {
                uVar10 = uVar10 * 2;
              } while (uVar10 <= uVar7);
            }
          }
          else {
            uVar10 = (uVar7 & 0xfffffc00) + 0x400;
          }
          if (uVar8 * 4 < 0x100000) {
            if ((1 < uVar8) &&
               (uVar12 = 1 << ((char)((uint)(float)uVar8 >> 0x17) + 0x81U & 0x1f),
               bVar16 = uVar12 < uVar8, uVar8 = uVar12, bVar16)) {
              uVar8 = uVar12 * 2;
            }
          }
          else {
            uVar8 = (uVar8 & 0x7ffffc00) + 0x400;
          }
          if (uVar8 == uVar10) {
LAB_0047e2ce:
            in_stack_0000004c = uVar7 * 2;
          }
          else {
            if (uVar10 == 0) {
              if (in_stack_00000048 != 0) {
                func_0x0097caf0(in_stack_00000048);
                in_stack_00000048 = 0;
                in_stack_0000004c = 0;
                goto LAB_0047e2d5;
              }
            }
            else {
              in_stack_00000048 = func_0x0097c810(in_stack_00000048,uVar10 * 4);
              if (in_stack_00000048 != 0) goto LAB_0047e2ce;
            }
            in_stack_00000048 = 0;
            in_stack_0000004c = 0;
          }
        }
      }
      else {
        if (in_stack_00000048 != 0) {
          func_0x0097caf0(in_stack_00000048);
        }
        in_stack_00000048 = 0;
        in_stack_0000004c = 0;
      }
    }
LAB_0047e2d5:
    if (((uStack00000054 & 1) == 0) && (uVar8 = uStack00000054 >> 1, uVar8 != 0)) {
      uVar7 = uVar8 - 1;
      if (in_stack_00000010 < uVar7) {
        puVar15 = (undefined4 *)(in_stack_00000050 + in_stack_00000010 * 8);
        puVar11 = puVar15 + 2;
        for (uVar10 = (uVar7 - in_stack_00000010) * 2 & 0x3ffffffe; uVar10 != 0; uVar10 = uVar10 - 1
            ) {
          *puVar15 = *puVar11;
          puVar11 = puVar11 + 1;
          puVar15 = puVar15 + 1;
        }
      }
      if (uVar7 < 0x10000000) {
        if (uVar7 != uVar8) {
          if (uVar7 * 8 < 0x100000) {
            uVar10 = 1;
            if (uVar7 != 0) {
              do {
                uVar10 = uVar10 * 2;
              } while (uVar10 <= uVar7);
            }
          }
          else {
            uVar10 = (uVar7 & 0xfffffc00) + 0x400;
          }
          if (uVar8 * 8 < 0x100000) {
            if ((1 < uVar8) &&
               (uVar12 = 1 << ((char)((uint)(float)uVar8 >> 0x17) + 0x81U & 0x1f),
               bVar16 = uVar12 < uVar8, uVar8 = uVar12, bVar16)) {
              uVar8 = uVar12 * 2;
            }
          }
          else {
            uVar8 = (uVar8 & 0x7ffffc00) + 0x400;
          }
          if (uVar8 == uVar10) {
LAB_0047e405:
            uStack00000054 = uVar7 * 2;
          }
          else {
            if (uVar10 == 0) {
              if (in_stack_00000050 != 0) {
                func_0x0097caf0(in_stack_00000050);
                in_stack_00000050 = 0;
                uStack00000054 = 0;
                goto LAB_0047e40c;
              }
            }
            else {
              in_stack_00000050 = func_0x0097c810(in_stack_00000050,uVar10 * 8);
              if (in_stack_00000050 != 0) goto LAB_0047e405;
            }
            in_stack_00000050 = 0;
            uStack00000054 = 0;
          }
        }
      }
      else {
        if (in_stack_00000050 != 0) {
          func_0x0097caf0(in_stack_00000050);
        }
        in_stack_00000050 = 0;
        uStack00000054 = 0;
      }
    }
LAB_0047e40c:
    in_stack_00000010 = in_stack_00000010 - 1;
  }
LAB_0047e411:
  in_stack_00000010 = in_stack_00000010 + 1;
  in_stack_00000018 = in_stack_0000005c >> 1;
  if (in_stack_00000018 <= in_stack_00000010) {
LAB_0047e42e:
    if (in_stack_00000050 != 0) {
      func_0x0097caf0(in_stack_00000050);
    }
    if (in_stack_00000048 != 0) {
      func_0x0097caf0(in_stack_00000048);
    }
    if (in_stack_00000058 != 0) {
      func_0x0097caf0(in_stack_00000058);
    }
    return 0;
  }
  goto LAB_0047db90;
LAB_0047e049:
  in_stack_00000014 = (int *)((int)in_stack_00000014 + 1);
  in_stack_00000018 = in_stack_0000005c >> 1;
  if (in_stack_00000018 <= in_stack_00000014) goto LAB_0047e411;
  goto LAB_0047dc00;
}



// Could not create function at 0047dc1c

// =========================================================
// Function: FUN_0049c2b0 @ 0049c2b0

undefined4 FUN_0049c2b0(int *param_1)

{
  char *pcVar1;
  int iVar2;
  uint uVar3;
  uint *puVar4;
  uint unaff_ESI;
  uint *puVar5;
  int *unaff_EDI;
  uint uVar6;
  int *piVar7;
  undefined4 uVar8;
  int iStack_3c;
  int iStack_38;
  uint uStack_34;
  int iStack_30;
  int iStack_2c;
  int iStack_28;
  int iStack_24;
  undefined4 uStack_20;
  undefined4 uStack_1c;
  undefined4 uStack_18;
  undefined4 uStack_14;
  uint uStack_8;
  uint uStack_4;
  
  iVar2 = *param_1;
  if (iVar2 != 0) {
    func_0x00401110(0x14,&SUB_004290c0);
    func_0x00c07681(iVar2 + -4);
  }
  param_1[1] = param_1[1] & 1;
  *param_1 = 0;
  iStack_38 = param_1[4] - param_1[2];
  iStack_3c = param_1[5] - param_1[3];
  if ((iStack_38 == 0) || (iStack_3c == 0)) {
    return 0xffffffff;
  }
  iStack_2c = 0;
  iStack_28 = 0;
  uVar8 = 0x3b;
  piVar7 = &iStack_2c;
  func_0x009881d0(piVar7,0x3b,0);
  uStack_4 = uStack_34 >> 1;
  uStack_8 = 0;
  if (uStack_4 != 0) {
    do {
      iStack_24 = 0;
      uStack_20 = 0;
      uStack_1c = 0;
      uStack_18 = 0;
      uStack_14 = 0;
      iStack_3c = 0;
      func_0x009881d0(&stack0xffffffc0,0x2c,0);
      if ((unaff_ESI & 0xfffffffe) == 4) {
        if ((((*unaff_EDI == 0) || (pcVar1 = (char *)(*unaff_EDI + 4), pcVar1 == (char *)0x0)) ||
            (*pcVar1 == '\0')) ||
           ((iVar2 = func_0x00c07eef(pcVar1,&UNK_00cd9554,&iStack_3c), iVar2 != 1 ||
            (iVar2 = FUN_009b9190(iStack_3c,iStack_38), iVar2 != 0)))) {
          func_0x00401110(4,&SUB_005bd380);
          func_0x0097caf0(unaff_EDI + -1);
          uVar8 = 0;
        }
        else {
          iVar2 = FUN_009b93f0();
          if (((iVar2 == 0) && (iStack_30 < iStack_28)) &&
             ((iStack_2c < iStack_24 && (iVar2 = func_0x004136b0(&iStack_30), iVar2 == 0)))) {
            if ((param_1[1] & 1U) != 0) goto LAB_0049c605;
            uVar3 = (uint)param_1[1] >> 1;
            if (uVar3 * 0x14 < 0x100000) {
              uVar6 = uVar3;
              if ((uVar3 & uVar3 - 1) == 0) {
                if (uVar3 == 0) {
                  uVar6 = 1;
                }
                else {
                  uVar6 = uVar3 * 2;
                }
              }
            }
            else {
              uVar6 = (uVar3 & 0x7ffffc00) + 0x400;
            }
            if (uVar3 < uVar6) {
              puVar5 = (uint *)0x0;
              if (uVar6 == 0) {
LAB_0049c545:
                iVar2 = *param_1;
                if (iVar2 != 0) {
                  func_0x00401110(0x14,&SUB_004290c0);
                  func_0x00c07681(iVar2 + -4);
                }
                *param_1 = (int)puVar5;
              }
              else {
                uVar3 = -(uint)((int)((ulonglong)uVar6 * 0x14 >> 0x20) != 0) |
                        (uint)((ulonglong)uVar6 * 0x14);
                puVar4 = (uint *)func_0x00c0769f(-(uint)(0xfffffffb < uVar3) | uVar3 + 4);
                if (puVar4 != (uint *)0x0) {
                  puVar5 = puVar4 + 1;
                  *puVar4 = uVar6;
                  func_0x004010e0(0x14,&UNK_0052e1d0);
                  if (puVar5 != (uint *)0x0) {
                    if ((uint)param_1[1] >> 1 <= uVar6) {
                      uVar6 = (uint)param_1[1] >> 1;
                    }
                    if (uVar6 != 0) {
                      iVar2 = 0;
                      do {
                        func_0x00498ea0((int)puVar5 + iVar2);
                        iVar2 = iVar2 + 0x14;
                        uVar6 = uVar6 - 1;
                      } while (uVar6 != 0);
                    }
                    goto LAB_0049c545;
                  }
                }
                puVar5 = (uint *)0x0;
              }
            }
            else {
              puVar5 = (uint *)*param_1;
            }
            if (puVar5 == (uint *)0x0) {
LAB_0049c605:
              func_0x00401210();
              func_0x00401000();
              func_0x00401210();
              return 4;
            }
            func_0x00498ea0(*param_1 + ((uint)param_1[1] >> 1) * 0x14);
            uVar3 = (param_1[1] & 0xfffffffeU) + 2;
            param_1[1] = uVar3 ^ param_1[1] & 1U;
            if (*param_1 + -0x14 + (uVar3 >> 1) * 0x14 == 0) goto LAB_0049c605;
          }
          func_0x00401210();
        }
        func_0x00401000();
      }
      else {
        if (unaff_EDI != (int *)0x0) {
          func_0x00401110(4,&SUB_005bd380);
          func_0x0097caf0(unaff_EDI + -1);
        }
        unaff_EDI = (int *)0x0;
        func_0x00401000();
      }
      uStack_8 = uStack_8 + 1;
    } while (uStack_8 < uStack_4);
  }
  if (iStack_38 != 0) {
    iVar2 = iStack_38 + -4;
    func_0x00401110(4,&SUB_005bd380,piVar7,uVar8);
    func_0x0097caf0(iVar2);
  }
  return 0;
}



// =========================================================
// Function: FUN_0049d560 @ 0049d560

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_0049d560(int *param_1)

{
  char *pcVar1;
  int iVar2;
  uint uVar3;
  int iVar4;
  int iVar5;
  uint uVar6;
  undefined4 *puVar7;
  int *piVar8;
  undefined4 *puVar9;
  int *piVar10;
  int *piStack_48;
  uint uStack_44;
  int iStack_40;
  uint uStack_3c;
  undefined4 uStack_38;
  undefined4 uStack_34;
  int aiStack_30 [6];
  undefined8 uStack_18;
  uint uStack_8;
  int iStack_4;
  
  if (*param_1 != 0) {
    func_0x00c07681(*param_1);
  }
  param_1[1] = param_1[1] & 1;
  *param_1 = 0;
  uStack_44 = param_1[4] - param_1[2];
  piStack_48 = (int *)(param_1[5] - param_1[3]);
  if ((uStack_44 == 0) || (piStack_48 == (int *)0x0)) {
    return 0xffffffff;
  }
  uStack_34 = 0;
  aiStack_30[0] = 0;
  func_0x009881d0(&uStack_34,0x3b,0);
  uStack_8 = 0;
  if (uStack_3c >> 1 != 0) {
    do {
      uStack_18 = _DAT_00c7ccf8;
      aiStack_30[0] = 0;
      aiStack_30[1] = 0;
      aiStack_30[2] = 0;
      aiStack_30[3] = 0;
      aiStack_30[4] = 0;
      aiStack_30[5] = 0;
      piStack_48 = (int *)0x0;
      uStack_44 = 0;
      func_0x009881d0(&piStack_48,0x2c,0);
      piVar8 = piStack_48;
      if ((uStack_44 & 0xfffffffe) == 4) {
        if ((((*piStack_48 == 0) || (pcVar1 = (char *)(*piStack_48 + 4), pcVar1 == (char *)0x0)) ||
            (*pcVar1 == '\0')) ||
           ((iVar2 = func_0x00c07eef(pcVar1,&UNK_00cd9554,&uStack_38), iVar2 != 1 ||
            (iVar2 = FUN_009b9190(uStack_38,uStack_34), iVar2 != 0)))) {
          func_0x00401110(4,&SUB_005bd380);
          func_0x0097caf0(piVar8 + -1);
          piStack_48 = (int *)0x0;
        }
        else {
          iVar2 = FUN_009b93f0();
          if (((iVar2 == 0) && (aiStack_30[0] < aiStack_30[2])) &&
             ((aiStack_30[1] < aiStack_30[3] && (iVar2 = func_0x0092c450(aiStack_30), iVar2 == 0))))
          {
            if ((param_1[1] & 1U) != 0) goto LAB_0049d899;
            uVar3 = (uint)param_1[1] >> 1;
            if (uVar3 << 5 < 0x100000) {
              uVar6 = uVar3;
              if ((uVar3 & uVar3 - 1) == 0) {
                if (uVar3 == 0) {
                  uVar6 = 1;
                }
                else {
                  uVar6 = uVar3 * 2;
                }
              }
            }
            else {
              uVar6 = (uVar3 & 0x7ffffc00) + 0x400;
            }
            if (uVar3 < uVar6) {
              iVar2 = 0;
              if (uVar6 != 0) {
                iVar2 = func_0x00c0769f(-(uint)((int)((ulonglong)uVar6 * 0x20 >> 0x20) != 0) |
                                        (uint)((ulonglong)uVar6 * 0x20));
                if (iVar2 == 0) {
                  iVar2 = 0;
                  goto LAB_0049d809;
                }
                func_0x004010e0(0x20,&UNK_00413610);
                iStack_4 = iVar2;
                if ((uint)param_1[1] >> 1 <= uVar6) {
                  uVar6 = (uint)param_1[1] >> 1;
                }
                if (uVar6 != 0) {
                  iVar4 = 0;
                  do {
                    puVar7 = (undefined4 *)(*param_1 + iVar4);
                    puVar9 = (undefined4 *)(iVar4 + iVar2);
                    iVar4 = iVar4 + 0x20;
                    uVar6 = uVar6 - 1;
                    for (iVar5 = 8; iVar5 != 0; iVar5 = iVar5 + -1) {
                      *puVar9 = *puVar7;
                      puVar7 = puVar7 + 1;
                      puVar9 = puVar9 + 1;
                    }
                  } while (uVar6 != 0);
                }
              }
              if (*param_1 != 0) {
                func_0x00c07681(*param_1);
              }
              *param_1 = iVar2;
            }
            else {
              iVar2 = *param_1;
            }
LAB_0049d809:
            if (iVar2 == 0) {
LAB_0049d899:
              func_0x00401210();
              func_0x00401210();
              return 4;
            }
            piVar8 = aiStack_30;
            piVar10 = (int *)(((uint)param_1[1] >> 1) * 0x20 + *param_1);
            for (iVar2 = 8; iVar2 != 0; iVar2 = iVar2 + -1) {
              *piVar10 = *piVar8;
              piVar8 = piVar8 + 1;
              piVar10 = piVar10 + 1;
            }
            uVar3 = (param_1[1] & 0xfffffffeU) + 2;
            param_1[1] = uVar3 ^ param_1[1] & 1U;
            if ((uVar3 >> 1) * 0x20 + -0x20 + *param_1 == 0) goto LAB_0049d899;
          }
          func_0x00401210();
        }
      }
      else {
        if (piStack_48 != (int *)0x0) {
          piVar8 = piStack_48 + -1;
          func_0x00401110(4,&SUB_005bd380);
          func_0x0097caf0(piVar8);
        }
        piStack_48 = (int *)0x0;
      }
      uStack_8 = uStack_8 + 1;
    } while (uStack_8 < uStack_3c >> 1);
  }
  if (iStack_40 != 0) {
    func_0x00401110(4,&SUB_005bd380);
    func_0x0097caf0(iStack_40 + -4);
  }
  return 0;
}



// =========================================================
// Function: FUN_006adc25 @ 006adc25

undefined4 FUN_006adc25(int *param_1)

{
  undefined4 uVar1;
  char cVar2;
  int *piVar3;
  char *pcVar4;
  int iVar5;
  int iVar6;
  char unaff_BL;
  int unaff_EBP;
  char *pcVar7;
  uint uVar8;
  int *in_stack_00000018;
  int *in_stack_0000001c;
  undefined4 in_stack_00000020;
  int in_stack_0000002c;
  int *in_stack_00000030;
  undefined4 in_stack_00000038;
  undefined4 in_stack_0000003c;
  undefined4 in_stack_00000040;
  undefined4 in_stack_00000044;
  undefined4 in_stack_00000048;
  undefined4 in_stack_0000004c;
  undefined4 in_stack_00000050;
  undefined4 in_stack_00000054;
  undefined4 in_stack_00000058;
  int *in_stack_0000005c;
  int *in_stack_00000068;
  undefined4 in_stack_0000006c;
  int in_stack_00000074;
  undefined4 in_stack_00000078;
  
code_r0x006adc25:
  do {
    func_0x00401000();
    if (unaff_BL != '\0') {
      iVar5 = func_0x00c07db2(*(undefined4 *)(*(int *)(unaff_EBP + 0x10c) + in_stack_00000074 * 4),0
                              ,0xd3c588,0xd3c5a4);
      iVar6 = *(int *)(iVar5 + 0x40);
      in_stack_00000038 = *(undefined4 *)(iVar5 + 0x44);
      in_stack_0000003c = *(undefined4 *)(iVar5 + 0x48);
      in_stack_00000040 = *(undefined4 *)(iVar5 + 0x4c);
      if (*(char *)(unaff_EBP + 0x15) != '\0') {
        func_0x0042bb50(*(undefined4 *)(unaff_EBP + 0xc));
      }
      uVar1 = in_stack_00000078;
      func_0x006b3ee0(in_stack_00000078);
      cVar2 = func_0x006b3f90(uVar1);
      if (cVar2 == '\0') {
        in_stack_00000068 = (int *)0x0;
      }
      in_stack_00000038 = 0x3f800000;
      in_stack_0000003c = 0;
      in_stack_00000040 = 0;
      in_stack_00000044 = 0;
      in_stack_0000004c = 0;
      uVar8 = 0;
      in_stack_00000050 = 0;
      in_stack_00000054 = 0;
      in_stack_00000048 = 0x3f800000;
      in_stack_00000058 = 0x3f800000;
      in_stack_0000005c = (int *)CONCAT31(in_stack_0000005c._1_3_,1);
      func_0x0090fcc0(&stack0x00000038,0,0,in_stack_00000020,in_stack_0000001c,0,0,0,0);
      if ((*(uint *)(unaff_EBP + 0x110) & 0xfffffffe) != 0) {
        do {
          (**(code **)(**(int **)(*(int *)(unaff_EBP + 0x10c) + uVar8 * 4) + 0x84))
                    (&stack0x00000038);
          uVar8 = uVar8 + 1;
        } while (uVar8 < *(uint *)(unaff_EBP + 0x110) >> 1);
      }
      if (((int)in_stack_00000030 < 1) || (iVar6 <= in_stack_0000002c)) {
        if (*(char *)(unaff_EBP + 0x15) == '\0') {
          *(undefined4 *)(unaff_EBP + 0x240) = 0;
          *(undefined4 *)(unaff_EBP + 0x244) = 0;
          *(undefined4 *)(unaff_EBP + 0x248) = 0;
          *(undefined4 *)(unaff_EBP + 0x24c) = 0;
        }
      }
      else if (*(char *)(unaff_EBP + 0x15) == '\0') {
        *(undefined4 *)(unaff_EBP + 0x240) = 0;
        *(int *)(unaff_EBP + 0x244) = in_stack_0000002c;
        *(int **)(unaff_EBP + 0x248) = in_stack_00000030;
        *(int *)(unaff_EBP + 0x24c) = iVar6;
        FUN_009b93f0();
      }
      else {
        func_0x0042b820(*(undefined4 *)(unaff_EBP + 0xc),in_stack_0000006c);
      }
      func_0x006b4820();
      if (((in_stack_0000001c[9] == 0) || (in_stack_0000001c[8] == 0)) ||
         (iVar6 = GetCurrentThreadId(), in_stack_0000001c[8] != iVar6)) {
        in_stack_0000001c[8] = 0;
        if ((char)in_stack_0000001c[3] == '\0') {
          (**(code **)(*in_stack_0000001c + 0x1c))();
        }
        else {
          LeaveCriticalSection(in_stack_0000001c + 10);
        }
      }
      else {
        in_stack_0000001c[9] = in_stack_0000001c[9] + -1;
      }
      func_0x00401000();
      (**(code **)(*in_stack_0000005c + 8))();
      func_0x00401000();
      if (((param_1[9] != 0) && (param_1[8] != 0)) &&
         (iVar6 = GetCurrentThreadId(), param_1[8] == iVar6)) {
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
    in_stack_00000074 = in_stack_00000074 + -1;
    if (in_stack_00000074 < 0) {
      if (*(char *)(unaff_EBP + 0x15) == '\0') {
        *(undefined4 *)(unaff_EBP + 0x240) = 0;
        *(undefined4 *)(unaff_EBP + 0x244) = 0;
        *(undefined4 *)(unaff_EBP + 0x248) = 0;
        *(undefined4 *)(unaff_EBP + 0x24c) = 0;
      }
      else {
        func_0x0042bb50(*(undefined4 *)(unaff_EBP + 0xc));
      }
      if (((in_stack_00000030[9] == 0) || (in_stack_00000030[8] == 0)) ||
         (iVar6 = GetCurrentThreadId(), in_stack_00000030[8] != iVar6)) {
        in_stack_00000030[8] = 0;
        if ((char)in_stack_00000030[3] == '\0') {
          (**(code **)(*in_stack_00000030 + 0x1c))();
        }
        else {
          LeaveCriticalSection();
        }
      }
      else {
        in_stack_00000030[9] = in_stack_00000030[9] + -1;
      }
      if (*(char *)(unaff_EBP + 0x15) != '\0') {
        func_0x00476a60(*(undefined4 *)(unaff_EBP + 0xc));
      }
      func_0x006b4820();
      func_0x00401000();
      (**(code **)(*in_stack_00000068 + 8))();
      func_0x00401000();
      if (((in_stack_00000018[9] != 0) && (in_stack_00000018[8] != 0)) &&
         (iVar6 = GetCurrentThreadId(), in_stack_00000018[8] == iVar6)) {
        in_stack_00000018[9] = in_stack_00000018[9] + -1;
        return 0;
      }
      in_stack_00000018[8] = 0;
      if ((char)in_stack_00000018[3] != '\0') {
        LeaveCriticalSection(in_stack_00000018 + 10);
        return 0;
      }
      (**(code **)(*in_stack_00000018 + 0x1c))();
      return 0;
    }
    piVar3 = (int *)(**(code **)(**(int **)(*(int *)(unaff_EBP + 0x10c) + in_stack_00000074 * 4) +
                                0x10))();
    iVar6 = *piVar3;
    if (iVar6 == 0) {
LAB_006adc16:
      unaff_BL = '\0';
      goto code_r0x006adc25;
    }
    if (iVar6 == -4) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_006adc16;
      unaff_BL = '\0';
    }
    else {
      if (iVar6 == 0) {
        pcVar4 = (char *)0x0;
      }
      else {
        pcVar4 = (char *)(iVar6 + 4);
      }
      iVar6 = 7;
      unaff_BL = true;
      pcVar7 = "crop64";
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        unaff_BL = *pcVar7 == *pcVar4;
        pcVar7 = pcVar7 + 1;
        pcVar4 = pcVar4 + 1;
      } while ((bool)unaff_BL);
    }
  } while( true );
}



// =========================================================
// Function: FUN_006ae280 @ 006ae280

undefined4 FUN_006ae280(int *param_1,undefined4 *param_2)

{
  int *piVar1;
  char cVar2;
  int iVar3;
  uint uVar4;
  uint uVar5;
  undefined4 uVar6;
  uint uVar7;
  uint *unaff_EBX;
  int *piVar8;
  undefined4 unaff_EBP;
  char *pcVar9;
  uint *puVar10;
  uint *puVar11;
  bool bVar12;
  int *unaff_retaddr;
  undefined4 uStack_50;
  int *piStack_4c;
  undefined4 auStack_48 [2];
  int iStack_40;
  int *piStack_3c;
  int iStack_38;
  int iStack_34;
  undefined4 uStack_30;
  undefined4 uStack_2c;
  undefined4 uStack_28;
  undefined4 uStack_24;
  undefined4 uStack_20;
  int *piStack_1c;
  undefined1 uStack_18;
  undefined4 uStack_c;
  undefined4 uStack_8;
  int *piStack_4;
  
  piVar8 = param_1 + 0x1f;
  piStack_3c = piVar8;
  iVar3 = GetCurrentThreadId();
  if ((param_1[0x27] == 0) || (param_1[0x27] != iVar3)) {
    if ((char)param_1[0x22] == '\0') {
      (**(code **)(*piVar8 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + 0x29);
    }
    param_1[0x28] = 0;
    param_1[0x27] = iVar3;
  }
  else {
    param_1[0x28] = param_1[0x28] + 1;
  }
  auStack_48[0] = 0xffffffff;
  if (param_2 != (undefined4 *)0x0) {
    *param_2 = 0;
  }
  uVar4 = (uint)param_1[0x58] >> 1;
  if (uVar4 == 0) goto LAB_006ae863;
  piVar1 = *(int **)(param_1[0x57] + -4 + uVar4 * 4);
  if ((piVar1 != (int *)0x0) && ((**(code **)(*piVar1 + 4))(), piVar1 != (int *)0x0)) {
    (**(code **)(*piVar1 + 4))();
  }
  if ((param_1[0x44] & 1U) == 0) {
    uVar5 = (uint)param_1[0x44] >> 1;
    if (uVar5 * 4 < 0x100000) {
      uVar7 = uVar5;
      if ((uVar5 & uVar5 - 1) == 0) {
        if (uVar5 == 0) {
          uVar7 = 1;
        }
        else {
          uVar7 = uVar5 * 2;
        }
      }
    }
    else {
      uVar7 = (uVar5 & 0x7ffffc00) + 0x400;
    }
    if (uVar5 < uVar7) {
      if (uVar7 == 0) {
        if (param_1[0x43] != 0) {
          func_0x0097caf0(param_1[0x43]);
          param_1[0x43] = 0;
        }
      }
      else {
        iVar3 = func_0x0097c810(param_1[0x43],uVar7 * 4);
        param_1[0x43] = iVar3;
      }
    }
    if (param_1[0x43] != 0) {
      *(int **)(param_1[0x43] + ((uint)param_1[0x44] >> 1) * 4) = piVar1;
      param_1[0x44] = (param_1[0x44] & 0xfffffffeU) + 2 ^ param_1[0x44] & 1U;
    }
  }
  func_0x00906fc0(uVar4 - 1);
  if (*(char *)((int)param_1 + 0x15) == '\0') {
    (**(code **)(*(int *)param_1[7] + 0x10))(param_2,piVar8,1,1);
  }
  (**(code **)(*piVar1 + 0x10))(&uStack_50);
  func_0x007f4570();
  if (unaff_EBX == (uint *)0x0) {
LAB_006ae7a5:
    func_0x006b3ee0(piVar1,&stack0x00000000);
    func_0x008f7be0(uStack_8,uStack_50);
    uVar6 = InterlockedCompareExchange(param_1 + 0x1c,0,0);
    uVar6 = (**(code **)(*param_1 + 8))(uVar6);
    uStack_50 = func_0x006bcfd0(param_1[4],param_1 + 0x5a,uVar6);
  }
  else {
    puVar11 = unaff_EBX + 1;
    piVar8 = piStack_4;
    if (puVar11 == (uint *)0x0) {
      piVar8 = piVar1;
      if (((*unaff_EBX & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
        bVar12 = false;
        goto LAB_006ae454;
      }
LAB_006ae45f:
      if (puVar11 == (uint *)0x0) {
        if (((*unaff_EBX & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
          bVar12 = false;
          goto LAB_006ae496;
        }
      }
      else {
        bVar12 = true;
        iVar3 = 7;
        pcVar9 = "crop64";
        puVar10 = puVar11;
        do {
          piVar8 = piStack_4;
          if (iVar3 == 0) break;
          iVar3 = iVar3 + -1;
          bVar12 = *pcVar9 == (char)*puVar10;
          pcVar9 = pcVar9 + 1;
          puVar10 = (uint *)((int)puVar10 + 1);
        } while (bVar12);
LAB_006ae496:
        if (bVar12) {
          iVar3 = func_0x00c07db2(piVar8,0,0xd3c588,0xd3c5a4,0);
          iStack_40 = *(int *)(iVar3 + 0x40);
          piStack_3c = *(int **)(iVar3 + 0x44);
          iStack_38 = *(undefined4 *)(iVar3 + 0x48);
          iStack_34 = *(undefined4 *)(iVar3 + 0x4c);
          if (*(char *)((int)param_1 + 0x15) != '\0') {
            func_0x0042bb50(param_1[3],piVar1);
          }
          func_0x006b3ee0(piVar1,auStack_48);
          cVar2 = func_0x006b3f90(piVar1);
          if (cVar2 == '\0') {
            uStack_c = 0;
          }
          piStack_3c = (int *)0x3f800000;
          iStack_38 = 0;
          iStack_34 = 0;
          uStack_30 = 0;
          uStack_28 = 0;
          uVar4 = 0;
          uStack_24 = 0;
          uStack_20 = 0;
          uStack_2c = 0x3f800000;
          piStack_1c = (int *)0x3f800000;
          uStack_18 = 1;
          func_0x0090fcc0(&piStack_3c,0,0,unaff_EBX,unaff_EBP,0,0,0,0);
          if ((param_1[0x44] & 0xfffffffeU) != 0) {
            do {
              (**(code **)(**(int **)(param_1[0x43] + uVar4 * 4) + 0x84))(&uStack_30);
              uVar4 = uVar4 + 1;
            } while (uVar4 < (uint)param_1[0x44] >> 1);
          }
          if ((iStack_40 < iStack_38) && ((int)piStack_3c < iStack_34)) {
            if (*(char *)((int)param_1 + 0x15) == '\0') {
              param_1[0x90] = iStack_40;
              param_1[0x91] = (int)piStack_3c;
              param_1[0x92] = iStack_38;
              param_1[0x93] = iStack_34;
              FUN_009b93f0();
            }
            else {
              uStack_50 = func_0x0042b820(param_1[3],piVar1);
            }
          }
          else if (*(char *)((int)param_1 + 0x15) == '\0') {
            param_1[0x90] = 0;
            param_1[0x91] = 0;
            param_1[0x92] = 0;
            param_1[0x93] = 0;
          }
          goto LAB_006ae81b;
        }
      }
      if (puVar11 == (uint *)0x0) {
        if (((*unaff_EBX & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
          bVar12 = false;
          goto LAB_006ae681;
        }
LAB_006ae68c:
        if (puVar11 == (uint *)0x0) {
          if (((*unaff_EBX & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar12 = false;
            goto LAB_006ae6bb;
          }
        }
        else {
          bVar12 = true;
          iVar3 = 7;
          pcVar9 = "redeye";
          puVar10 = puVar11;
          do {
            piVar8 = piStack_4;
            if (iVar3 == 0) break;
            iVar3 = iVar3 + -1;
            bVar12 = *pcVar9 == (char)*puVar10;
            pcVar9 = pcVar9 + 1;
            puVar10 = (uint *)((int)puVar10 + 1);
          } while (bVar12);
LAB_006ae6bb:
          if (bVar12) goto LAB_006ae81b;
        }
        if (puVar11 == (uint *)0x0) {
          if (((*unaff_EBX & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar12 = false;
            goto LAB_006ae6f5;
          }
        }
        else {
          bVar12 = true;
          iVar3 = 8;
          pcVar9 = "retouch";
          puVar10 = puVar11;
          do {
            piVar8 = piStack_4;
            if (iVar3 == 0) break;
            iVar3 = iVar3 + -1;
            bVar12 = *pcVar9 == (char)*puVar10;
            pcVar9 = pcVar9 + 1;
            puVar10 = (uint *)((int)puVar10 + 1);
          } while (bVar12);
LAB_006ae6f5:
          if (bVar12) goto LAB_006ae81b;
        }
        if (puVar11 == (uint *)0x0) {
          if (((*unaff_EBX & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar12 = false;
            goto LAB_006ae72f;
          }
        }
        else {
          bVar12 = true;
          iVar3 = 7;
          pcVar9 = "picnik";
          puVar10 = puVar11;
          do {
            piVar8 = piStack_4;
            if (iVar3 == 0) break;
            iVar3 = iVar3 + -1;
            bVar12 = *pcVar9 == (char)*puVar10;
            pcVar9 = pcVar9 + 1;
            puVar10 = (uint *)((int)puVar10 + 1);
          } while (bVar12);
LAB_006ae72f:
          if (bVar12) goto LAB_006ae81b;
        }
        if (puVar11 == (uint *)0x0) {
          if (((*unaff_EBX & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar12 = false;
            piStack_4 = piVar8;
            goto LAB_006ae769;
          }
LAB_006ae774:
          if (puVar11 == (uint *)0x0) {
            if (((*unaff_EBX & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_006ae7a5;
            bVar12 = false;
          }
          else {
            iVar3 = 9;
            bVar12 = true;
            pcVar9 = "movieend";
            do {
              if (iVar3 == 0) break;
              iVar3 = iVar3 + -1;
              bVar12 = *pcVar9 == (char)*puVar11;
              pcVar9 = pcVar9 + 1;
              puVar11 = (uint *)((int)puVar11 + 1);
            } while (bVar12);
          }
          if (!bVar12) goto LAB_006ae7a5;
        }
        else {
          bVar12 = true;
          iVar3 = 0xb;
          pcVar9 = "moviestart";
          puVar10 = puVar11;
          do {
            if (iVar3 == 0) break;
            iVar3 = iVar3 + -1;
            bVar12 = *pcVar9 == (char)*puVar10;
            pcVar9 = pcVar9 + 1;
            puVar10 = (uint *)((int)puVar10 + 1);
          } while (bVar12);
LAB_006ae769:
          piVar8 = piStack_4;
          if (!bVar12) goto LAB_006ae774;
        }
        uStack_50 = 0;
      }
      else {
        bVar12 = true;
        iVar3 = 4;
        pcVar9 = "rot";
        puVar10 = puVar11;
        do {
          piVar8 = piStack_4;
          if (iVar3 == 0) break;
          iVar3 = iVar3 + -1;
          bVar12 = *pcVar9 == (char)*puVar10;
          pcVar9 = pcVar9 + 1;
          puVar10 = (uint *)((int)puVar10 + 1);
        } while (bVar12);
LAB_006ae681:
        if (!bVar12) goto LAB_006ae68c;
      }
      if (unaff_retaddr != (int *)0x0) {
        (**(code **)(*piVar8 + 4))();
        *unaff_retaddr = (int)piVar8;
      }
    }
    else {
      bVar12 = true;
      iVar3 = 5;
      pcVar9 = "save";
      puVar10 = puVar11;
      do {
        if (iVar3 == 0) break;
        iVar3 = iVar3 + -1;
        bVar12 = *pcVar9 == (char)*puVar10;
        pcVar9 = pcVar9 + 1;
        puVar10 = (uint *)((int)puVar10 + 1);
      } while (bVar12);
LAB_006ae454:
      if (!bVar12) goto LAB_006ae45f;
    }
  }
LAB_006ae81b:
  func_0x006b4820(param_1,piVar1);
  (**(code **)(*(int *)param_1[7] + 0x10))(piVar1,piStack_4c,1,1);
  func_0x00401000();
  (**(code **)(*piStack_1c + 8))();
  piVar8 = piStack_4c;
LAB_006ae863:
  uVar6 = auStack_48[0];
  if (((piVar8[9] != 0) && (piVar8[8] != 0)) && (iVar3 = GetCurrentThreadId(), piVar8[8] == iVar3))
  {
    piVar8[9] = piVar8[9] + -1;
    return uVar6;
  }
  piVar8[8] = 0;
  if ((char)piVar8[3] == '\0') {
    (**(code **)(*piVar8 + 0x1c))();
    return uVar6;
  }
  LeaveCriticalSection(piVar8 + 10);
  return uVar6;
}



