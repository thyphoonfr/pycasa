// Address: 005e26a0
// Function: FUN_005e26a0
// Target requested: 0x005e2e83

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_005e26a0(int *param_1,undefined1 *param_2)

{
  undefined4 *puVar1;
  undefined1 uVar2;
  char cVar3;
  int *piVar4;
  int iVar5;
  undefined4 uVar6;
  int iVar7;
  char *pcVar8;
  char *pcVar9;
  byte *pbVar10;
  uint uVar11;
  uint *puVar12;
  undefined *puVar13;
  bool bVar14;
  char cVar16;
  undefined1 *puVar15;
  char cStack_367;
  char cStack_366;
  undefined1 *puStack_364;
  int iStack_360;
  uint *puStack_35c;
  int iStack_358;
  undefined4 *puStack_354;
  undefined1 *puStack_350;
  undefined1 *puStack_34c;
  int iStack_348;
  undefined4 uStack_344;
  undefined4 uStack_340;
  undefined *puStack_33c;
  int *piStack_338;
  undefined1 *puStack_334;
  undefined1 auStack_324 [4];
  undefined1 auStack_320 [4];
  undefined4 uStack_31c;
  int iStack_318;
  undefined1 auStack_308 [8];
  undefined4 uStack_300;
  int iStack_2f0;
  undefined4 uStack_2e8;
  undefined4 uStack_2e4;
  int iStack_2d0;
  int iStack_2cc;
  undefined4 auStack_2c8 [15];
  int *piStack_28c;
  int *piStack_280;
  undefined1 uStack_25c;
  undefined4 uStack_228;
  undefined4 uStack_224;
  undefined4 uStack_220;
  undefined1 auStack_210 [8];
  undefined1 auStack_208 [4];
  undefined *puStack_204;
  undefined1 auStack_1f8 [24];
  undefined4 uStack_1e0;
  undefined4 uStack_1dc;
  int iStack_170;
  undefined1 auStack_12c [136];
  undefined4 *puStack_a4;
  undefined4 uStack_a0;
  
  piStack_338 = (int *)param_1[0x3a8];
  puStack_334 = param_2;
  puStack_33c = &UNK_00c972cc;
  uStack_300 = 0;
  uStack_340 = (byte *)0x5e26d3;
  func_0x0040eab0();
  if (_DAT_00d67914 == 0) {
LAB_005e26f9:
    puStack_334 = (undefined1 *)0x5e2702;
    func_0x00401000();
    return 0xffffffff;
  }
  puStack_334 = (undefined1 *)0x5e26f3;
  piVar4 = (int *)func_0x009c2fc0();
  if (piVar4 == (int *)0x0) goto LAB_005e26f9;
  puStack_334 = auStack_208;
  puStack_33c = (undefined *)0x5e271c;
  piStack_338 = piVar4;
  func_0x009de880();
  puStack_33c = auStack_210;
  uStack_340 = (byte *)&uStack_1e0;
  uStack_344 = (undefined4 *)0x5e2735;
  (**(code **)(*piVar4 + 0x20))();
  uStack_2e8 = uStack_1e0;
  uStack_2e4 = uStack_1dc;
  uStack_344 = (undefined4 *)0x5e2754;
  iVar5 = (**(code **)(*param_1 + 0x24))();
  iStack_348 = *(int *)(iVar5 + 0x6c);
  uStack_344 = &uStack_2e8;
  puStack_34c = (undefined1 *)0x5e2763;
  ClientToScreen();
  uStack_344 = (undefined4 *)auStack_308;
  iStack_348 = 0x5e276d;
  func_0x00734ec0();
  uStack_344 = (undefined4 *)0x5e2775;
  piVar4 = (int *)func_0x00926c20();
  uStack_344 = (undefined4 *)&stack0xfffffcd4;
  iStack_348 = 0x5e2783;
  (**(code **)(*piVar4 + 4))();
  puStack_34c = param_2;
  puStack_350 = (undefined1 *)0x5e279a;
  uVar2 = (**(code **)(*(int *)(param_1[0xb0] + 0x4c) + 4))();
  puVar1 = (undefined4 *)uStack_340;
  uStack_340._3_1_ = SUB41(puVar1,3);
  uStack_340._0_3_ = (uint3)CONCAT11(uVar2,(undefined1)uStack_340);
  puStack_350 = (undefined1 *)0x5e27ac;
  func_0x004133e0();
  puStack_350 = param_2;
  puStack_354 = (undefined4 *)0x5e27bc;
  func_0x004b0190();
  puStack_354 = (undefined4 *)0x5e27c4;
  iVar5 = GetCurrentThreadId();
  if ((iStack_2d0 == 0) || (iStack_2d0 != iVar5)) {
    if ((char)uStack_2e4 == '\0') {
      puStack_354 = (undefined4 *)0x5e2805;
      (**(code **)(iStack_2f0 + 0x18))();
    }
    else {
      puStack_354 = auStack_2c8;
      iStack_358 = 0x5e27f6;
      EnterCriticalSection();
    }
    iStack_2cc = 0;
    iStack_2d0 = iVar5;
  }
  else {
    iStack_2cc = iStack_2cc + 1;
  }
  uStack_340 = (byte *)0x0;
  while (piStack_28c != (int *)0x0) {
    uStack_344 = (undefined4 *)CONCAT13(uStack_25c,(undefined3)uStack_344);
    uStack_25c = 1;
    puStack_354 = (undefined4 *)0x5e283b;
    iVar5 = GetCurrentThreadId();
    if ((iStack_2d0 == 0) || (iStack_2d0 != iVar5)) {
      if ((char)uStack_2e4 == '\0') {
        puStack_354 = (undefined4 *)0x5e287a;
        (**(code **)(iStack_2f0 + 0x18))();
      }
      else {
        puStack_354 = auStack_2c8;
        iStack_358 = 0x5e286b;
        EnterCriticalSection();
      }
      iStack_2cc = 0;
      iStack_2d0 = iVar5;
    }
    else {
      iStack_2cc = iStack_2cc + 1;
    }
    uVar11 = piStack_28c[1];
    if ((iStack_2cc == 0) || (iStack_2d0 == 0)) {
LAB_005e28b8:
      iStack_2d0 = 0;
      if ((char)uStack_2e4 == '\0') {
        puStack_354 = (undefined4 *)0x5e28e3;
        (**(code **)(iStack_2f0 + 0x1c))();
      }
      else {
        puStack_354 = auStack_2c8;
        iStack_358 = 0x5e28d4;
        LeaveCriticalSection();
      }
    }
    else {
      puStack_354 = (undefined4 *)0x5e28a5;
      iVar5 = GetCurrentThreadId();
      if (iStack_2d0 != iVar5) goto LAB_005e28b8;
      iStack_2cc = iStack_2cc + -1;
    }
    uStack_25c = uStack_344._3_1_;
    if ((byte *)(uVar11 >> 1) <= uStack_340) break;
    uStack_25c = 1;
    uVar11 = 0xffffffff;
    puStack_354 = (undefined4 *)0x5e2905;
    iVar5 = GetCurrentThreadId();
    if ((iStack_2d0 == 0) || (iStack_2d0 != iVar5)) {
      if ((char)uStack_2e4 == '\0') {
        puStack_354 = (undefined4 *)0x5e2944;
        (**(code **)(iStack_2f0 + 0x18))();
      }
      else {
        puStack_354 = auStack_2c8;
        iStack_358 = 0x5e2935;
        EnterCriticalSection();
      }
      iStack_2cc = 0;
      iStack_2d0 = iVar5;
    }
    else {
      iStack_2cc = iStack_2cc + 1;
    }
    if ((piStack_28c != (int *)0x0) && (uStack_340 < (byte *)((uint)piStack_28c[1] >> 1))) {
      uVar11 = *(uint *)(*piStack_28c + (int)uStack_340 * 4);
    }
    if ((iStack_2cc == 0) || (iStack_2d0 == 0)) {
LAB_005e2998:
      iStack_2d0 = 0;
      if ((char)uStack_2e4 == '\0') {
        puStack_354 = (undefined4 *)0x5e29c7;
        (**(code **)(iStack_2f0 + 0x1c))();
      }
      else {
        puStack_354 = auStack_2c8;
        iStack_358 = 0x5e29b8;
        LeaveCriticalSection();
      }
    }
    else {
      puStack_354 = (undefined4 *)0x5e2985;
      iVar5 = GetCurrentThreadId();
      if (iStack_2d0 != iVar5) goto LAB_005e2998;
      iStack_2cc = iStack_2cc + -1;
    }
    uStack_25c = uStack_344._3_1_;
    if (((piStack_280 != (int *)0x0) && (uVar11 < (uint)piStack_280[1] >> 1)) &&
       (*(char *)(*piStack_280 + uVar11) != '\0')) {
      uStack_344._0_3_ = CONCAT12(1,(undefined2)uStack_344);
      break;
    }
    uStack_340 = uStack_340 + 1;
  }
  if ((iStack_2cc == 0) || (iStack_2d0 == 0)) {
LAB_005e2a29:
    iStack_2d0 = 0;
    if ((char)uStack_2e4 == '\0') {
      puStack_354 = (undefined4 *)0x5e2a54;
      (**(code **)(iStack_2f0 + 0x1c))();
    }
    else {
      puStack_354 = auStack_2c8;
      iStack_358 = 0x5e2a45;
      LeaveCriticalSection();
    }
  }
  else {
    puStack_354 = (undefined4 *)0x5e2a16;
    iVar5 = GetCurrentThreadId();
    if (iStack_2d0 != iVar5) goto LAB_005e2a29;
    iStack_2cc = iStack_2cc + -1;
  }
  if (uStack_344._1_1_ == '\0') {
    puStack_354 = (undefined4 *)&UNK_00c97308;
    iStack_358 = 0x5e2ac5;
    piVar4 = (int *)func_0x009ae560();
    if (*piVar4 == 0) {
      puStack_204 = &UNK_00c7f979;
    }
    else {
      puStack_204 = (undefined *)(*piVar4 + 4);
    }
  }
  else {
    puStack_354 = (undefined4 *)&UNK_00c972ec;
    iStack_358 = 0x5e2a6a;
    piVar4 = (int *)func_0x009ae560();
    if (*piVar4 == 0) {
      puStack_204 = &UNK_00c7f979;
    }
    else {
      puStack_204 = (undefined *)(*piVar4 + 4);
    }
  }
  puVar13 = (undefined *)iStack_318;
  puStack_354 = &uStack_228;
  uStack_220 = 0;
  uStack_224 = 0x30;
  uStack_228 = 0x30;
  iStack_358 = 0;
  puStack_35c = (uint *)0x9dfc;
  iStack_360 = iStack_318;
  puStack_364 = (undefined1 *)0x5e2b19;
  (*_DAT_00d69584)();
  puStack_364 = (undefined1 *)0x5e2b25;
  func_0x004a0410();
  puStack_364 = auStack_1f8;
  iVar5 = func_0x004b9940();
  if (iVar5 == 0) {
    cVar3 = func_0x00431290();
    if (cVar3 == '\0') {
      CheckMenuItem(puVar13,0x9e01,(-(uint)(iStack_170 != 0) & 0xfffffff8) + 8);
      CheckMenuItem(puVar13,0x9e02,(-(uint)(iStack_170 != 1) & 0xfffffff8) + 8);
      CheckMenuItem(puVar13,0x9e1a,(iStack_170 != 2) - 1U & 8);
      if (iStack_170 == 3) {
        EnableMenuItem(puVar13,0x9e1a,1);
      }
      CheckMenuItem(puVar13,0x9e1b,(iStack_170 != 3) - 1U & 8);
    }
  }
  else {
    cVar3 = func_0x00431290();
    if (cVar3 == '\0') {
      EnableMenuItem(puVar13,0x9e01,1);
      EnableMenuItem(puVar13,0x9e02,1);
      EnableMenuItem(puVar13,0x9e1a,1);
      EnableMenuItem(puVar13,0x9e1b,1);
    }
    EnableMenuItem(puVar13,0x9e03,1);
    EnableMenuItem(puVar13,0x9e08,1);
    EnableMenuItem(puVar13,0x9e04,1);
    EnableMenuItem(puVar13,0x9e06,1);
  }
  puStack_334 = (undefined1 *)0x0;
  puStack_350 = (undefined1 *)0x0;
  puStack_34c = (undefined1 *)0x0;
  iStack_358 = 4;
  puStack_33c = (undefined *)0x2;
  puVar15 = param_2;
  func_0x0044dfd0(param_1[0xaf],param_2,&puStack_334);
  cVar16 = (char)((uint)puVar15 >> 8);
  iStack_348 = func_0x004aa180(&uStack_340,&puStack_364,&iStack_348);
  cVar3 = func_0x00431290();
  cStack_367 = (char)((uint)param_2 >> 8);
  if (cVar3 == '\0') {
    puStack_354 = (undefined4 *)(uint)(cStack_367 == '\0');
    EnableMenuItem(puVar13,0x9e13,puStack_354);
    EnableMenuItem(puVar13,0x9e0a,puStack_354);
    EnableMenuItem(puVar13,0x9dfd,puStack_354);
  }
  puStack_354 = (undefined4 *)(uint)(cStack_367 == '\0');
  EnableMenuItem(puVar13,0x9e14,puStack_354);
  EnableMenuItem(puVar13,0x9dfe,puStack_354);
  cStack_366 = (char)((uint)param_2 >> 0x10);
  if ((cStack_367 == '\0') || (cStack_366 == '\0')) {
    bVar14 = false;
  }
  else {
    bVar14 = true;
  }
  EnableMenuItem(puVar13,0x9e0d,!bVar14);
  if (cStack_367 != '\0') {
    if (iStack_348 == 0) {
      CheckMenuItem(puVar13,0x9dfe,(-(uint)(iStack_358 != 0) & 0xfffffff8) + 8);
      CheckMenuItem(puVar13,0x9e14,(iStack_358 != 0x800) - 1U & 8);
      cVar3 = func_0x00431290();
      if (cVar3 == '\0') {
        CheckMenuItem(puVar13,0x9dfd,(iStack_358 != 0x640) - 1U & 8);
        CheckMenuItem(puVar13,0x9e0a,(iStack_358 != 0x400) - 1U & 8);
        CheckMenuItem(puVar13,0x9e13,(iStack_358 != 800) - 1U & 8);
      }
      if (cStack_366 != '\0') {
        if (puStack_35c == (uint *)0x0) {
LAB_005e2dfe:
          bVar14 = false;
        }
        else if (puStack_35c + 1 == (uint *)0x0) {
          if (((*puStack_35c & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005e2dfe;
          bVar14 = false;
        }
        else {
          iVar5 = 6;
          bVar14 = true;
          pbVar10 = &UNK_00c811d4;
          puVar12 = puStack_35c + 1;
          do {
            puVar13 = puStack_33c;
            if (iVar5 == 0) break;
            iVar5 = iVar5 + -1;
            bVar14 = *pbVar10 == (byte)*puVar12;
            pbVar10 = pbVar10 + 1;
            puVar12 = (uint *)((int)puVar12 + 1);
          } while (bVar14);
        }
        CheckMenuItem(puVar13,0x9e0d,-bVar14 & 8);
      }
    }
    else {
      EnableMenuItem(puVar13,0x9dfe,1);
      EnableMenuItem(puVar13,0x9e14,1);
      cVar3 = func_0x00431290();
      if (cVar3 == '\0') {
        EnableMenuItem(puVar13,0x9dfd,1);
        EnableMenuItem(puVar13,0x9e0a,1);
        EnableMenuItem(puVar13,0x9e13,1);
      }
    }
  }
  uVar6 = _DAT_00d67850;
  param_1[0xd29] = param_1[0xd29] + 1;
  uVar6 = TrackPopupMenu(puStack_33c,0x10a,uStack_31c,iStack_318,0,uVar6,0);
  func_0x00a6b060();
  iVar5 = iStack_360;
  param_1[0xd29] = param_1[0xd29] + -1;
  switch(uVar6) {
  case 0x9dfc:
    func_0x005e0750(param_1,param_2);
    func_0x0097a090();
    if (cVar16 == '\0') {
      bVar14 = 0xfffffffe < uRam00d35a18;
      uRam00d35a18 = uRam00d35a18 + 1;
      iRam00d35a1c = iRam00d35a1c + (uint)bVar14;
    }
    else {
      bVar14 = 0xfffffffe < uRam00d35a38;
      uRam00d35a38 = uRam00d35a38 + 1;
      iRam00d35a3c = iRam00d35a3c + (uint)bVar14;
    }
    break;
  case 0x9dfd:
    piVar4 = (int *)func_0x004aa300(auStack_320,&puStack_35c);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    func_0x00444ee0(param_1[0xaf],param_2,iVar7,iVar5);
    func_0x00401000();
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35a98;
    uRam00d35a98 = uRam00d35a98 + 1;
    iRam00d35a9c = iRam00d35a9c + (uint)bVar14;
    break;
  case 0x9dfe:
    piVar4 = (int *)func_0x004aa300(&stack0xfffffcd8,&puStack_35c);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    func_0x00444ee0(param_1[0xaf],param_2,iVar7,iVar5);
    func_0x00401000();
    piStack_338 = (int *)0x0;
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35a58;
    uRam00d35a58 = uRam00d35a58 + 1;
    iRam00d35a5c = iRam00d35a5c + (uint)bVar14;
    break;
  default:
    goto LAB_005e3451;
  case 0x9e01:
    func_0x005a0e90(param_2,0);
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35b38;
    uRam00d35b38 = uRam00d35b38 + 1;
    iRam00d35b3c = iRam00d35b3c + (uint)bVar14;
    break;
  case 0x9e02:
    func_0x005a0e90(param_2,1);
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35b58;
    uRam00d35b58 = uRam00d35b58 + 1;
    iRam00d35b5c = iRam00d35b5c + (uint)bVar14;
    break;
  case 0x9e03:
    func_0x005e0ef0(param_1,param_2);
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35bb8;
    uRam00d35bb8 = uRam00d35bb8 + 1;
    iRam00d35bbc = iRam00d35bbc + (uint)bVar14;
    break;
  case 0x9e04:
    func_0x005a0100(param_2);
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35bd8;
    uRam00d35bd8 = uRam00d35bd8 + 1;
    iRam00d35bdc = iRam00d35bdc + (uint)bVar14;
    break;
  case 0x9e06:
    piVar4 = (int *)func_0x009ae560(&UNK_00c97334);
    iVar5 = 0;
    if (*piVar4 == 0) {
      puStack_354 = (undefined4 *)0x0;
    }
    else {
      puStack_354 = (undefined4 *)(*piVar4 + 4);
    }
    iVar7 = (**(code **)(*param_1 + 0x24))();
    uVar6 = *(undefined4 *)(iVar7 + 0x6c);
    piVar4 = (int *)func_0x009ae560(&UNK_00c9735c);
    if (*piVar4 != 0) {
      iVar5 = *piVar4 + 4;
    }
    piVar4 = (int *)func_0x009ae560(&UNK_00c973e0);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    cVar3 = func_0x009bac20(1,iVar7,iVar5,0,uVar6,puStack_354);
    if ((cVar3 != '\0') &&
       (iVar5 = (**(code **)(*(int *)(param_1[0xaf] + 0x48) + 0x8c))
                          (param_2,&puStack_354,iStack_360), iVar5 == 0)) {
      func_0x004a0410();
      puStack_a4 = puStack_354;
      uStack_a0 = puStack_350;
      func_0x005a0790(auStack_12c);
      func_0x004a0520();
    }
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35c38;
    uRam00d35c38 = uRam00d35c38 + 1;
    iRam00d35c3c = iRam00d35c3c + (uint)bVar14;
    break;
  case 0x9e08:
    if ((DAT_00d67849 == '\0') || (uVar11 = GetAsyncKeyState(0x11), (uVar11 >> 0xf & 1) == 0)) {
      func_0x005a0f60(param_1,param_2);
      func_0x0097a090();
      bVar14 = 0xfffffffe < uRam00d35bf8;
      uRam00d35bf8 = uRam00d35bf8 + 1;
      iRam00d35bfc = iRam00d35bfc + (uint)bVar14;
    }
    else {
      func_0x005a10c0();
      func_0x0097a090();
      bVar14 = 0xfffffffe < uRam00d35c18;
      uRam00d35c18 = uRam00d35c18 + 1;
      iRam00d35c1c = iRam00d35c1c + (uint)bVar14;
    }
    break;
  case 0x9e0a:
    piVar4 = (int *)func_0x004aa300(&stack0xfffffcd4,&puStack_35c);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    func_0x00444ee0(param_1[0xaf],param_2,iVar7,iVar5);
    func_0x00401000();
    puStack_33c = (undefined *)0x0;
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35ab8;
    uRam00d35ab8 = uRam00d35ab8 + 1;
    iRam00d35abc = iRam00d35abc + (uint)bVar14;
    break;
  case 0x9e0d:
    if (puStack_35c == (uint *)0x0) {
code_r0x005e3120:
      pcVar9 = "]star";
    }
    else {
      if (puStack_35c + 1 == (uint *)0x0) {
        if (((*puStack_35c & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto code_r0x005e3120;
        bVar14 = false;
      }
      else {
        iVar5 = 6;
        bVar14 = true;
        pbVar10 = &UNK_00c811d4;
        puVar12 = puStack_35c + 1;
        do {
          if (iVar5 == 0) break;
          iVar5 = iVar5 + -1;
          bVar14 = *pbVar10 == (byte)*puVar12;
          pbVar10 = pbVar10 + 1;
          puVar12 = (uint *)((int)puVar12 + 1);
        } while (bVar14);
      }
      pcVar9 = "";
      if (!bVar14) goto code_r0x005e3120;
    }
    puStack_354 = (undefined4 *)0x0;
    pcVar8 = pcVar9;
    if (pcVar9 != (char *)0x0) {
      do {
        cVar3 = *pcVar8;
        pcVar8 = pcVar8 + 1;
      } while (cVar3 != '\0');
      func_0x00985ff0(pcVar9);
    }
    iVar5 = iStack_360;
    piVar4 = (int *)func_0x004aa300(&stack0xfffffcd0,&puStack_354);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    func_0x00444ee0(param_1[0xaf],param_2,iVar7,iVar5);
    func_0x00401000();
    uStack_340 = (byte *)0x0;
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35af8;
    uRam00d35af8 = uRam00d35af8 + 1;
    iRam00d35afc = iRam00d35afc + (uint)bVar14;
    func_0x0097a100();
    func_0x00401000();
    goto LAB_005e3451;
  case 0x9e0f:
    piVar4 = (int *)func_0x004aa300(&iStack_348,&puStack_35c);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    func_0x00444ee0(param_1[0xaf],param_2,iVar7,iVar5);
    func_0x00401000();
    iStack_358 = 0;
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35b18;
    uRam00d35b18 = uRam00d35b18 + 1;
    iRam00d35b1c = iRam00d35b1c + (uint)bVar14;
    break;
  case 0x9e13:
    piVar4 = (int *)func_0x004aa300(auStack_324,&puStack_35c);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    func_0x00444ee0(param_1[0xaf],param_2,iVar7,iVar5);
    func_0x00401000();
    puStack_334 = (undefined1 *)0x0;
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35ad8;
    uRam00d35ad8 = uRam00d35ad8 + 1;
    iRam00d35adc = iRam00d35adc + (uint)bVar14;
    break;
  case 0x9e14:
    piVar4 = (int *)func_0x004aa300(&puStack_334,&puStack_35c);
    if (*piVar4 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar4 + 4;
    }
    func_0x00444ee0(param_1[0xaf],param_2,iVar7,iVar5);
    func_0x00401000();
    uStack_344 = (undefined4 *)0x0;
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35a78;
    uRam00d35a78 = uRam00d35a78 + 1;
    iRam00d35a7c = iRam00d35a7c + (uint)bVar14;
    break;
  case 0x9e1a:
    func_0x005a0e90(param_2,2);
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35b78;
    uRam00d35b78 = uRam00d35b78 + 1;
    iRam00d35b7c = iRam00d35b7c + (uint)bVar14;
    break;
  case 0x9e1b:
    func_0x005a0e90(param_2,3);
    func_0x0097a090();
    bVar14 = 0xfffffffe < uRam00d35b98;
    uRam00d35b98 = uRam00d35b98 + 1;
    iRam00d35b9c = iRam00d35b9c + (uint)bVar14;
  }
  func_0x0097a100();
LAB_005e3451:
  puVar12 = puStack_35c;
  if ((puStack_35c != (uint *)0x0) && ((byte)*puStack_35c < 0x80)) {
    cVar3 = InterlockedDecrement(puStack_35c);
    if (cVar3 == '\x7f') {
      if ((byte)*puVar12 < 0x80) {
        cVar3 = InterlockedIncrement(puVar12);
      }
      else {
        cVar3 = -1;
      }
    }
    if (cVar3 == '\0') {
      func_0x0097caf0(puVar12);
    }
  }
  pbVar10 = uStack_340;
  if ((uStack_340 != (byte *)0x0) && (*uStack_340 < 0x80)) {
    cVar3 = InterlockedDecrement(uStack_340);
    if (cVar3 == '\x7f') {
      if (*pbVar10 < 0x80) {
        cVar3 = InterlockedIncrement(pbVar10);
      }
      else {
        cVar3 = -1;
      }
    }
    if (cVar3 == '\0') {
      func_0x0097caf0(pbVar10);
    }
  }
  func_0x004a0520();
  func_0x00413490();
  if (iStack_360 != 0) {
    (**(code **)(*(int *)(iStack_360 + 4) + 8))();
  }
  if (((char)piStack_338 != '\0') && (puStack_33c != (undefined *)0x0)) {
    DestroyMenu(puStack_33c);
  }
  func_0x00401000();
  return 0;
}


