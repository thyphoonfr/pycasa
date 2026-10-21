// Address: 005e2000
// Function: FUN_005e2000
// Target requested: 0x005e264e

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_005e2000(int *param_1)

{
  byte bVar1;
  uint *puVar2;
  char cVar3;
  undefined1 uVar4;
  undefined1 uVar5;
  uint *in_EAX;
  int iVar6;
  uint *puVar7;
  undefined4 uVar8;
  uint *puVar9;
  char *pcVar10;
  code *pcVar11;
  bool bVar12;
  undefined4 uVar13;
  uint uVar14;
  int *piVar15;
  int *piVar16;
  uint *puStack_f4;
  undefined4 uStack_f0;
  uint uStack_ec;
  uint *puStack_e8;
  undefined4 uStack_e4;
  uint uStack_e0;
  uint *puStack_dc;
  undefined4 uStack_d8;
  uint uStack_d4;
  uint *puStack_d0;
  undefined *puStack_cc;
  byte *pbStack_c8;
  uint *puStack_c4;
  undefined4 uStack_c0;
  uint *puStack_bc;
  uint *puStack_b8;
  int *piStack_b4;
  byte *pbStack_b0;
  byte *pbStack_ac;
  undefined4 uStack_a8;
  undefined4 uStack_a4;
  undefined4 uStack_a0;
  undefined4 uStack_9c;
  uint *puStack_98;
  undefined4 uStack_94;
  uint auStack_80 [2];
  undefined1 auStack_78 [8];
  uint auStack_70 [27];
  
  if (in_EAX == (uint *)0x0) {
    return 4;
  }
  uStack_a0 = 0xffffffff;
  uStack_a4 = 1;
  uStack_9c = 0xffffffff;
  puStack_98 = (uint *)0xffffffff;
  uStack_94 = 0xffffffff;
  uStack_a8 = 0;
  pbStack_ac = (byte *)0x1;
  pbStack_b0 = (byte *)0x1;
  piStack_b4 = param_1;
  puStack_b8 = (uint *)0x5e204c;
  func_0x00a54b70();
  puStack_b8 = auStack_70;
  uStack_c0 = (undefined1 *)0x5e2057;
  puStack_bc = in_EAX;
  func_0x009de880();
  uStack_c0 = auStack_78;
  puStack_c4 = (uint *)&stack0xffffff78;
  pbStack_c8 = (byte *)0x5e206a;
  (**(code **)(*in_EAX + 0x20))();
  pbStack_c8 = (byte *)0x5e2083;
  iVar6 = (**(code **)(*param_1 + 0x24))();
  puStack_cc = *(undefined **)(iVar6 + 0x6c);
  pbStack_c8 = (byte *)&uStack_a0;
  puStack_d0 = (uint *)0x5e2092;
  ClientToScreen();
  pbStack_c8 = (byte *)0x5e209b;
  func_0x00733480();
  puVar2 = puStack_98;
  pcVar11 = CheckMenuItem_exref;
  pbStack_ac = *(byte **)(param_1[0xb0] + 0xd8);
  pbStack_c8 = (byte *)((-(uint)(pbStack_ac != (byte *)0x0) & 0xfffffff8) + 8);
  puStack_cc = (undefined *)0x9c8b;
  puStack_d0 = puStack_98;
  uStack_d4 = 0x5e20c8;
  CheckMenuItem();
  pbStack_c8 = (byte *)((-(uint)(pbStack_ac != (byte *)0x1) & 0xfffffff8) + 8);
  puStack_cc = (undefined *)0x9cbd;
  puStack_d0 = puVar2;
  uStack_d4 = 0x5e20e2;
  CheckMenuItem();
  pbStack_c8 = (byte *)((pbStack_ac != (byte *)0x2) - 1 & 8);
  puStack_cc = (undefined *)0x9c8c;
  puStack_d0 = puVar2;
  uStack_d4 = 0x5e20fb;
  CheckMenuItem();
  pbStack_c8 = (byte *)((pbStack_ac != (byte *)0x5) - 1 & 8);
  puStack_cc = (undefined *)0x9dc8;
  puStack_d0 = puVar2;
  uStack_d4 = 0x5e2114;
  CheckMenuItem();
  pbStack_c8 = (byte *)(-(uint)(*(char *)(param_1[0xb0] + 0x165) != '\0') & 8);
  puStack_cc = (undefined *)0xa0cf;
  puStack_d0 = puVar2;
  uStack_d4 = 0x5e2130;
  CheckMenuItem();
  pbStack_c8 = (byte *)((-(uint)(*(int *)(param_1[0xb0] + 0xdc) != 0) & 0xfffffff8) + 8);
  puStack_cc = (undefined *)0x9e18;
  puStack_d0 = puVar2;
  uStack_d4 = 0x5e214f;
  CheckMenuItem();
  pbStack_c8 = (byte *)((-(uint)(*(int *)(param_1[0xb0] + 0xdc) != 1) & 0xfffffff8) + 8);
  puStack_cc = (undefined *)0x9e19;
  puStack_d0 = puVar2;
  uStack_d4 = 0x5e2171;
  CheckMenuItem();
  pbStack_c8 = (byte *)((*(int *)(param_1[0xb0] + 0xdc) != 2) - 1 & 8);
  puStack_cc = (undefined *)0x9e38;
  puStack_d0 = puVar2;
  uStack_d4 = 0x5e2192;
  CheckMenuItem();
  pbStack_c8 = *(byte **)(param_1[0xb0] + 0x2e0);
  pbStack_b0 = pbStack_c8;
  if ((pbStack_c8 != (byte *)0x0) && (*pbStack_c8 < 0x80)) {
    puStack_cc = (undefined *)0x5e21b8;
    InterlockedIncrement();
  }
  pbStack_c8 = *(byte **)(param_1[0xb0] + 0x2f0);
  pbStack_ac = pbStack_c8;
  if ((pbStack_c8 != (byte *)0x0) && (*pbStack_c8 < 0x80)) {
    puStack_cc = (undefined *)0x5e21de;
    InterlockedIncrement();
  }
  pbStack_c8 = &UNK_00c8fd00;
  puStack_cc = &UNK_00c7eafc;
  puStack_d0 = auStack_80;
  uStack_a8 = 0;
  uStack_d4 = 0x5e2200;
  func_0x00407a20();
  if (puStack_bc == (uint *)0x0) {
    puVar7 = (uint *)0x0;
  }
  else {
    puVar7 = puStack_bc + 1;
  }
  if (puStack_b8 == (uint *)0x0) {
LAB_005e225e:
    if ((puVar7 == (uint *)0x0) || ((byte)*puVar7 == 0)) goto LAB_005e22c7;
LAB_005e2267:
    uStack_c0._0_2_ = (ushort)(byte)uStack_c0;
  }
  else {
    puVar9 = puStack_b8 + 1;
    if ((puVar9 == (uint *)0x0) || (puVar7 == (uint *)0x0)) {
      if (((*puStack_b8 & 0xffffff00) == 0) || ((byte)*puVar9 == 0)) goto LAB_005e225e;
      bVar12 = puVar9 == puVar7;
    }
    else {
      do {
        bVar1 = (byte)*puVar7;
        bVar12 = bVar1 < (byte)*puVar9;
        if (bVar1 != (byte)*puVar9) {
LAB_005e2244:
          bVar12 = 1 - bVar12 == (uint)(bVar12 != 0);
          goto LAB_005e22bc;
        }
        if (bVar1 == 0) break;
        bVar1 = *(byte *)((int)puVar7 + 1);
        bVar12 = bVar1 < *(byte *)((int)puVar9 + 1);
        if (bVar1 != *(byte *)((int)puVar9 + 1)) goto LAB_005e2244;
        puVar7 = (uint *)((int)puVar7 + 2);
        puVar9 = (uint *)((int)puVar9 + 2);
      } while (bVar1 != 0);
      bVar12 = true;
    }
LAB_005e22bc:
    if (!bVar12) goto LAB_005e2267;
LAB_005e22c7:
    if (puStack_bc == (uint *)0x0) goto LAB_005e2267;
    puVar7 = puStack_bc + 1;
    if (puVar7 == (uint *)0x0) {
      if (((*puStack_bc & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
        bVar12 = false;
        goto LAB_005e2306;
      }
LAB_005e230d:
      if (puVar7 == (uint *)0x0) {
        if (((*puStack_bc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005e2267;
        bVar12 = false;
      }
      else {
        iVar6 = 8;
        bVar12 = true;
        pcVar10 = "watched";
        do {
          pcVar11 = CheckMenuItem_exref;
          if (iVar6 == 0) break;
          iVar6 = iVar6 + -1;
          bVar12 = *pcVar10 == (char)*puVar7;
          pcVar10 = pcVar10 + 1;
          puVar7 = (uint *)((int)puVar7 + 1);
        } while (bVar12);
      }
      if (!bVar12) goto LAB_005e2267;
    }
    else {
      iVar6 = 4;
      bVar12 = true;
      pcVar10 = "all";
      puVar9 = puVar7;
      do {
        pcVar11 = CheckMenuItem_exref;
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar12 = *pcVar10 == (char)*puVar9;
        pcVar10 = pcVar10 + 1;
        puVar9 = (uint *)((int)puVar9 + 1);
      } while (bVar12);
LAB_005e2306:
      if (!bVar12) goto LAB_005e230d;
    }
    uStack_c0._0_2_ = CONCAT11(1,(byte)uStack_c0);
  }
  uStack_d4 = 0x5e2275;
  cVar3 = func_0x004019b0();
  uStack_d4 = -(uint)(cVar3 != '\0') & 8;
  uStack_d8 = 0x9db8;
  puStack_dc = puVar2;
  uStack_e0 = 0x5e2285;
  (*pcVar11)();
  if (puStack_c4 == (uint *)0x0) {
LAB_005e236b:
    bVar12 = false;
  }
  else if (puStack_c4 + 1 == (uint *)0x0) {
    if (((*puStack_c4 & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005e236b;
    bVar12 = false;
  }
  else {
    iVar6 = 8;
    bVar12 = true;
    pcVar10 = "desktop";
    puVar7 = puStack_c4 + 1;
    do {
      pcVar11 = CheckMenuItem_exref;
      if (iVar6 == 0) break;
      iVar6 = iVar6 + -1;
      bVar12 = *pcVar10 == (char)*puVar7;
      pcVar10 = pcVar10 + 1;
      puVar7 = (uint *)((int)puVar7 + 1);
    } while (bVar12);
  }
  uStack_e0 = -(uint)bVar12 & 8;
  uStack_e4 = 0x9dba;
  puStack_e8 = puVar2;
  uStack_ec = 0x5e2389;
  (*pcVar11)();
  if (puStack_d0 == (uint *)0x0) {
LAB_005e23c0:
    bVar12 = false;
  }
  else if (puStack_d0 + 1 == (uint *)0x0) {
    if (((*puStack_d0 & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005e23c0;
    bVar12 = false;
  }
  else {
    iVar6 = 7;
    bVar12 = true;
    pcVar10 = "mypics";
    puVar7 = puStack_d0 + 1;
    do {
      pcVar11 = CheckMenuItem_exref;
      if (iVar6 == 0) break;
      iVar6 = iVar6 + -1;
      bVar12 = *pcVar10 == (char)*puVar7;
      pcVar10 = pcVar10 + 1;
      puVar7 = (uint *)((int)puVar7 + 1);
    } while (bVar12);
  }
  uStack_ec = -(uint)bVar12 & 8;
  uStack_f0 = (int *)0x9e3a;
  puStack_f4 = puVar2;
  (*pcVar11)();
  if (puStack_dc != (uint *)0x0) {
    if (puStack_dc + 1 != (uint *)0x0) {
      iVar6 = 7;
      bVar12 = true;
      pcVar10 = "mydocs";
      puVar7 = puStack_dc + 1;
      do {
        pcVar11 = CheckMenuItem_exref;
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar12 = *pcVar10 == (char)*puVar7;
        pcVar10 = pcVar10 + 1;
        puVar7 = (uint *)((int)puVar7 + 1);
      } while (bVar12);
      goto LAB_005e2423;
    }
    if (((*puStack_dc & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
      bVar12 = false;
      goto LAB_005e2423;
    }
  }
  bVar12 = false;
LAB_005e2423:
  piVar15 = (int *)0x9db7;
  puVar7 = puVar2;
  (*pcVar11)(puVar2,0x9db7,-bVar12 & 8);
  uVar5 = SUB41(puVar7,0);
  uVar13 = 0x9db9;
  (*pcVar11)(puVar2,0x9db9,-(uStack_f0._1_1_ != '\0') & 8);
  iVar6 = param_1[0xaf];
  uStack_f0 = (int *)(iVar6 + 0xf8);
  uStack_ec = GetCurrentThreadId();
  if ((*(uint *)(iVar6 + 0x118) == 0) || (*(uint *)(iVar6 + 0x118) != uStack_ec)) {
    if (*(char *)(iVar6 + 0x104) == '\0') {
      (**(code **)(*(int *)(iVar6 + 0xf8) + 0x18))();
    }
    else {
      EnterCriticalSection(iVar6 + 0x120);
    }
    *(undefined4 *)(iVar6 + 0x11c) = 0;
    *(uint *)(iVar6 + 0x118) = uStack_ec;
  }
  else {
    *(int *)(iVar6 + 0x11c) = *(int *)(iVar6 + 0x11c) + 1;
  }
  uVar8 = func_0x009966a0(&uStack_ec);
  uVar4 = func_0x004f7e40(uVar8);
  uVar14 = (uint)CONCAT11(uVar4,uVar5);
  func_0x00401000();
  uVar8 = func_0x00996230(&uStack_f0);
  func_0x004f7e40(uVar8);
  func_0x00401000();
  uVar8 = func_0x00996b90(&puStack_f4);
  uVar5 = func_0x004f7e40(uVar8);
  uVar13 = CONCAT13(uVar5,(int3)uVar13);
  func_0x00401000();
  piVar16 = piVar15;
  if (((piVar15[9] == 0) || (piVar15[8] == 0)) ||
     (iVar6 = GetCurrentThreadId(), piVar15[8] != iVar6)) {
    piVar15[8] = 0;
    if ((char)piVar15[3] == '\0') {
      (**(code **)(*piVar15 + 0x1c))();
    }
    else {
      LeaveCriticalSection(piVar15 + 10);
    }
  }
  else {
    piVar15[9] = piVar15[9] + -1;
  }
  EnableMenuItem(puVar2,0x9e3a,(char)((uint)uVar13 >> 8) == '\0');
  EnableMenuItem(puVar2,0x9dba,(char)((uint)uVar13 >> 0x10) == '\0');
  EnableMenuItem(puVar2,0x9dba,(char)((uint)uVar13 >> 0x18) == '\0');
  EnableMenuItem(puVar2,0x9cd7,*(char *)(param_1[0xb0] + 0x9d) != '\0');
  EnableMenuItem(puVar2,8,*(char *)(param_1[0xb0] + 0x9d) == '\0' | 0x400);
  func_0x00401000();
  puStack_cc = (undefined *)0x0;
  func_0x00401000();
  puStack_d0 = (uint *)0x0;
  func_0x00401000();
  func_0x00401000();
  func_0x00407a20(&pbStack_ac,&UNK_00c7eafc,&UNK_00c8fd14);
  cVar3 = func_0x004019b0();
  CheckMenuItem(puVar2,0x9cd7,-(cVar3 != '\0') & 8);
  uVar13 = _DAT_00d67850;
  param_1[0xd29] = param_1[0xd29] + 1;
  TrackPopupMenu(puVar2,2,uVar14,piVar16,0,uVar13,0);
  func_0x00a6b060();
  param_1[0xd29] = param_1[0xd29] + -1;
  func_0x00401000();
  pbStack_b0 = (byte *)0x0;
  func_0x00401000();
  piStack_b4 = (int *)0x0;
  if (((char)puStack_f4 != '\0') && (puVar2 != (uint *)0x0)) {
    DestroyMenu(puVar2);
  }
  return 0;
}


