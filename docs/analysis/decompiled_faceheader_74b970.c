// Address: 0074ad40
// Function: FUN_0074ad40
// Target requested: 0074b970

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int FUN_0074ad40(int *param_1,undefined1 *param_2)

{
  char *pcVar1;
  int *piVar2;
  char cVar3;
  int iVar4;
  int iVar5;
  undefined4 uVar6;
  int *extraout_ECX;
  undefined4 *puVar7;
  int *piVar8;
  undefined1 *puVar9;
  char cVar10;
  undefined *puStack_1a4;
  undefined4 *puStack_1a0;
  undefined *puStack_19c;
  int *piStack_198;
  int *piStack_194;
  int *piStack_190;
  undefined *puStack_18c;
  undefined1 *puStack_188;
  undefined *puStack_184;
  undefined *puStack_180;
  int *piStack_17c;
  byte **ppbStack_178;
  undefined *puStack_174;
  undefined4 uStack_164;
  byte *pbStack_160;
  int iStack_15c;
  int iStack_158;
  int iStack_154;
  int iStack_150;
  undefined4 uStack_14c;
  undefined4 uStack_148;
  undefined4 uStack_144;
  undefined4 uStack_140;
  undefined4 uStack_13c;
  undefined4 auStack_134 [2];
  undefined auStack_12c [4];
  undefined4 uStack_128;
  undefined4 uStack_124;
  undefined1 auStack_120 [4];
  int aiStack_11c [2];
  undefined auStack_114 [16];
  undefined4 uStack_104;
  undefined4 uStack_100;
  undefined4 uStack_fc;
  undefined4 uStack_f8;
  undefined4 uStack_f4;
  undefined2 uStack_f0;
  undefined2 uStack_ee;
  undefined4 uStack_ec;
  undefined4 uStack_e8;
  undefined4 uStack_e4;
  undefined4 uStack_e0;
  undefined1 auStack_c4 [192];
  
  uStack_140 = 1;
  uStack_13c = 1;
  uStack_148 = 0;
  uStack_144 = 0;
  puStack_174 = (undefined *)0x74ad74;
  func_0x00512220();
  puStack_174 = &UNK_00cb1074;
  iStack_15c = 0;
  ppbStack_178 = (byte **)0x74ad89;
  func_0x00985ff0();
  piVar8 = param_1 + 0x99;
  if ((byte *)param_1[0x99] != pbStack_160) {
    ppbStack_178 = (byte **)0x74ada2;
    func_0x00401000();
    *piVar8 = (int)pbStack_160;
    if (pbStack_160 != (byte *)0x0) {
      if (*pbStack_160 < 0x80) {
        ppbStack_178 = (byte **)pbStack_160;
        piStack_17c = (int *)0x74adbe;
        cVar3 = InterlockedIncrement();
        if (cVar3 != -1) goto LAB_0074add1;
      }
      ppbStack_178 = (byte **)0x74add1;
      func_0x00985a60();
    }
  }
LAB_0074add1:
  ppbStack_178 = (byte **)0x74adda;
  func_0x00401000();
  if (param_1[0xa6] == 3) {
    ppbStack_178 = (byte **)&UNK_00cb1080;
    pbStack_160 = (byte *)0x0;
    piStack_17c = (int *)0x74adfe;
    func_0x00985ff0();
    if ((byte *)*piVar8 != uStack_164) {
      piStack_17c = (int *)0x74ae0d;
      func_0x00401000();
      *piVar8 = (int)uStack_164;
      if (uStack_164 != (byte *)0x0) {
        if (*uStack_164 < 0x80) {
          puStack_180 = (undefined *)0x74ae29;
          cVar3 = InterlockedIncrement();
          if (cVar3 != -1) goto LAB_0074ae3c;
        }
        piStack_17c = (int *)0x74ae3c;
        func_0x00985a60();
      }
    }
LAB_0074ae3c:
    piStack_17c = (int *)0x74ae45;
    func_0x00401000();
  }
  ppbStack_178 = (byte **)param_1[0xa8];
  piStack_17c = (int *)param_2;
  puStack_180 = &UNK_00cb1090;
  puStack_184 = (undefined *)0x74ae60;
  func_0x0040eab0();
  puStack_188 = param_2;
  if (param_1[0xa9] == 0) {
    return 4;
  }
  do {
    if (puStack_188 == (undefined1 *)0x0) {
      puStack_188 = (undefined1 *)0x0;
      break;
    }
    pcVar1 = puStack_188 + 0x213;
    puStack_188 = *(undefined1 **)(puStack_188 + 0x244);
  } while (*pcVar1 == '\0');
  ppbStack_178 = (byte **)0x0;
  piStack_17c = (int *)0xd3d81c;
  puStack_180 = (undefined *)0xd3d7e4;
  puStack_184 = (undefined *)0x0;
  puStack_18c = (undefined *)0x74aea9;
  iStack_154 = func_0x00c07db2();
  uStack_164._3_1_ = '\0';
  if ((param_1[0xa6] == 2) && (iStack_154 != 0)) {
    piStack_17c = (int *)param_1[0xa8];
    puStack_180 = *(undefined **)(*(int *)(iStack_154 + 0x2c0) + 0xc4);
    ppbStack_178 = (byte **)0x0;
    puStack_184 = (undefined *)0x74aee1;
    cVar3 = func_0x00448a10();
    if (cVar3 != '\0') {
      ppbStack_178 = (byte **)&UNK_00cb10a4;
      uStack_164._3_1_ = '\x01';
      pbStack_160 = (byte *)0x0;
      piStack_17c = (int *)0x74af05;
      func_0x00985ff0();
      piStack_17c = (int *)0x74af12;
      FUN_005c2100();
      piStack_17c = (int *)0x74af17;
      func_0x00401000();
    }
  }
  ppbStack_178 = (byte **)param_1[0xa8];
  piStack_17c = (int *)param_2;
  puStack_180 = &UNK_00cb10bc;
  pbStack_160 = (byte *)0x0;
  puStack_184 = (undefined *)0x74af38;
  func_0x0040eab0();
  piVar8 = (int *)0x0;
  ppbStack_178 = (byte **)0x74af58;
  iVar4 = func_0x009c2fc0();
  if (iVar4 != 0) {
    if (_DAT_00d67914 == 0) {
      puStack_188 = (undefined1 *)0x0;
    }
    else {
      ppbStack_178 = (byte **)0x74af75;
      puStack_188 = (undefined1 *)func_0x009c2fc0();
    }
    ppbStack_178 = (byte **)0x0;
    piStack_17c = (int *)0xd3db90;
    puStack_180 = (undefined *)0xd3b8a0;
    puStack_184 = (undefined *)0x0;
    puStack_18c = (undefined *)0x74af8d;
    piVar8 = (int *)func_0x00c07db2();
  }
  if ((char)param_1[0xa7] == '\0') {
    if (param_1[0xac] != 0) {
      ppbStack_178 = (byte **)0x74b00c;
      (**(code **)(*(int *)(param_1[0xac] + 4) + 8))();
      param_1[0xac] = 0;
    }
  }
  else {
    ppbStack_178 = (byte **)0x290;
    piStack_17c = (int *)0x74afa5;
    ppbStack_178 = (byte **)func_0x0097c5d0();
    if (ppbStack_178 == (byte **)0x0) {
      iVar4 = 0;
    }
    else {
      piStack_17c = (int *)0x74afb2;
      iVar4 = FUN_0072e520();
    }
    iVar5 = param_1[0xac];
    if (iVar4 != iVar5) {
      if (iVar5 != 0) {
        ppbStack_178 = (byte **)0x74afd1;
        (**(code **)(*(int *)(iVar5 + 4) + 8))();
      }
      param_1[0xac] = iVar4;
      if (iVar4 != 0) {
        ppbStack_178 = (byte **)0x74afe6;
        (**(code **)(*(int *)(iVar4 + 4) + 4))();
      }
    }
    if (iStack_154 != 0) {
      *(undefined1 *)(iStack_154 + 0x174) = 1;
    }
  }
  if (piVar8 == (int *)0x0) {
    if (uStack_164._3_1_ == '\0') {
      ppbStack_178 = (byte **)0x520;
      piStack_17c = (int *)0x74b08b;
      iVar4 = func_0x0097c5d0();
      if (iVar4 == 0) goto LAB_0074b09d;
      ppbStack_178 = (byte **)0x74b099;
      piVar8 = (int *)func_0x0077fd80();
    }
    else if (iStack_154 == 0) {
LAB_0074b09d:
      piVar8 = (int *)0x0;
    }
    else {
      ppbStack_178 = (byte **)0x540;
      piStack_17c = (int *)0x74b063;
      iVar4 = func_0x0097c5d0();
      if (iVar4 == 0) {
        piVar8 = (int *)0x0;
      }
      else {
        ppbStack_178 = (byte **)0x74b077;
        piVar8 = (int *)func_0x00789820();
      }
    }
    piVar2 = (int *)param_1[0xad];
    if (piVar8 != piVar2) {
      if (piVar2 != (int *)0x0) {
        ppbStack_178 = (byte **)0x74b0b4;
        (**(code **)(*piVar2 + 8))();
      }
      param_1[0xad] = (int)piVar8;
      if (piVar8 != (int *)0x0) {
        ppbStack_178 = (byte **)0x74b0c7;
        (**(code **)(*piVar8 + 4))();
      }
    }
    if (*(char *)((int)param_1 + 0x29d) == '\0') {
      ppbStack_178 = (byte **)0x6;
      piStack_17c = (int *)0x74b0e2;
      (**(code **)(*(int *)param_1[0xad] + 0xb0))();
    }
    piStack_17c = (int *)param_1[0xad];
    ppbStack_178 = &pbStack_160;
    puStack_180 = (undefined *)0x74b0f3;
    func_0x009ccdf0();
    *(int *)(param_1[0xad] + 0x2c8) = param_1[0xa9];
    ppbStack_178 = (byte **)0x74b118;
    func_0x009e4140();
  }
  else {
    piVar2 = (int *)param_1[0xad];
    if (piVar8 != piVar2) {
      if (piVar2 != (int *)0x0) {
        ppbStack_178 = (byte **)0x74b033;
        (**(code **)(*piVar2 + 8))();
      }
      param_1[0xad] = (int)piVar8;
      ppbStack_178 = (byte **)0x74b042;
      (**(code **)(*piVar8 + 4))();
    }
    ppbStack_178 = (byte **)0x74b049;
    func_0x0071c270();
  }
  if ((char)param_1[0xa7] == '\0') {
    ppbStack_178 = (byte **)0x278;
    piStack_17c = (int *)0x74b12f;
    iStack_150 = func_0x0097c5d0();
    piVar8 = (int *)0x0;
    if (iStack_150 != 0) {
      uStack_144 = 1;
      uStack_140 = 1;
      ppbStack_178 = (byte **)&UNK_00cb10d0;
      uStack_14c = 0;
      uStack_148 = 0;
      iStack_15c = 0;
      piStack_17c = (int *)0x74b16a;
      func_0x00985ff0();
      iVar4 = *(int *)(_DAT_00d67908 + 0x20);
      if (iVar4 != 0) {
        piStack_17c = *(int **)(_DAT_00d67908 + 0x18);
        puStack_180 = (undefined *)0x74b183;
        iVar5 = func_0x00409df0();
        for (puVar7 = *(undefined4 **)(iVar4 + iVar5 * 4); puVar7 != (undefined4 *)0x0;
            puVar7 = (undefined4 *)*puVar7) {
          piStack_17c = (int *)0x74b19c;
          cVar3 = func_0x006f9890();
          if (cVar3 != '\0') {
            puVar7 = puVar7 + 1;
            goto LAB_0074b1a8;
          }
        }
      }
      puVar7 = (undefined4 *)0x0;
LAB_0074b1a8:
      piStack_17c = (int *)0x74b1b1;
      func_0x00401000();
      if (puVar7 == (undefined4 *)0x0) {
        piStack_17c = (int *)0x0;
        puStack_180 = (undefined *)0x74b1d3;
        func_0x009b9ff0();
      }
      else {
        iStack_15c = puVar7[1];
      }
      piStack_17c = (int *)iStack_15c;
      puStack_180 = (undefined *)0x74b1e5;
      piVar8 = (int *)func_0x0052d9b0();
    }
    piVar2 = (int *)param_1[0xaa];
    if (piVar8 != piVar2) {
      if (piVar2 != (int *)0x0) {
        ppbStack_178 = (byte **)0x74b1fc;
        (**(code **)(*piVar2 + 8))();
      }
      param_1[0xaa] = (int)piVar8;
      if (piVar8 != (int *)0x0) {
        ppbStack_178 = (byte **)0x74b20f;
        (**(code **)(*piVar8 + 4))();
      }
    }
  }
  piStack_17c = (int *)param_1[0xa8];
  ppbStack_178 = (byte **)param_2;
  puStack_180 = &UNK_00cb1234;
  iStack_158 = 0;
  puStack_184 = (undefined *)0x74b230;
  func_0x0040eab0();
  piStack_17c = param_1;
  puStack_180 = (undefined *)0x74b23c;
  ppbStack_178 = (byte **)&iStack_158;
  func_0x009ccdf0();
  if (uStack_164._3_1_ == '\0') {
    ppbStack_178 = (byte **)0xd35850;
    piStack_17c = param_1;
    puStack_180 = (undefined *)0x74b251;
    func_0x009e4080();
  }
  if (param_1[0xaa] != 0) {
    ppbStack_178 = (byte **)0x74b266;
    iVar4 = func_0x009df290();
    if (iVar4 != 0) goto LAB_0074b26c;
  }
  if ((char)param_1[0xa7] == '\0') {
    ppbStack_178 = (byte **)0x74b329;
    iVar4 = func_0x009df290();
    if (iVar4 != 0) {
LAB_0074b26c:
      ppbStack_178 = (byte **)0x74b275;
      func_0x00401000();
      ppbStack_178 = (byte **)0x74b27e;
      func_0x00401000();
      return iVar4;
    }
  }
  else {
    ppbStack_178 = (byte **)0x74b2af;
    func_0x009df290();
    ppbStack_178 = (byte **)param_1[0xac];
    piStack_17c = (int *)0x74b2c1;
    func_0x00513330();
    piStack_17c = (int *)0x0;
    puStack_180 = (undefined *)0x0;
    puStack_184 = (undefined *)0x0;
    puStack_188 = (undefined1 *)0x0;
    puStack_18c = (undefined *)0x74b2e7;
    puStack_18c = (undefined *)func_0x00409ea0();
    piStack_190 = (int *)0x74b2ed;
    func_0x009df010();
    piStack_190 = (int *)0x0;
    piStack_194 = (int *)0x0;
    piStack_198 = (int *)0x0;
    puStack_19c = (undefined *)0x0;
    puStack_1a0 = (undefined4 *)0x74b313;
    puStack_1a0 = (undefined4 *)func_0x00409ea0();
    puStack_1a4 = (undefined *)0x74b319;
    func_0x009df060();
  }
  ppbStack_178 = (byte **)0x74b33d;
  func_0x009df290();
  ppbStack_178 = (byte **)0x74b346;
  (**(code **)(*param_1 + 0x6c))();
  if (param_1[0xa6] == 2) {
    iVar4 = param_1[0xad];
    *(undefined1 *)(iVar4 + 0x3c4) = 0;
    *(char *)(iVar4 + 0x3c8) = uStack_164._3_1_;
    if (uStack_164._3_1_ == '\0') {
      if (_DAT_00d67914 != 0) {
        ppbStack_178 = (byte **)0x74b3ce;
        iVar4 = func_0x009c2fc0();
        if (iVar4 != 0) {
          ppbStack_178 = (byte **)0x74b3dd;
          iVar5 = func_0x005121d0();
          if (iVar5 != 0) {
            piStack_17c = (int *)0x74b3ed;
            ppbStack_178 = (byte **)iVar4;
            func_0x005121d0();
            piStack_17c = (int *)0x74b3f4;
            func_0x009df680();
          }
        }
      }
    }
    else {
      if (iStack_154 == 0) {
        iVar4 = 0;
      }
      else {
        iVar4 = iStack_154 + 0x260;
      }
      *(int *)(param_1[0xad] + 0x354) = iVar4;
      iVar4 = param_1[0xad];
      if (iVar4 == 0) {
        iVar5 = 0;
      }
      else {
        iVar5 = iVar4 + 0x3bc;
      }
      *(int *)(iVar4 + 0x350) = iVar5;
      ppbStack_178 = (byte **)0x74b3ac;
      func_0x0074cae0();
      ppbStack_178 = (byte **)param_1;
      piStack_17c = (int *)0x74b3b2;
      func_0x0074c8f0();
    }
  }
  else if (param_1[0xa6] == 3) {
    iVar4 = param_1[0xad];
    *(undefined1 *)(iVar4 + 0x3c4) = 1;
    *(undefined1 *)(iVar4 + 0x3c8) = 0;
    ppbStack_178 = (byte **)0x74b417;
    func_0x00787d70();
    iVar4 = param_1[0xad];
    if (iVar4 == 0) {
      iVar5 = 0;
    }
    else {
      iVar5 = iVar4 + 0x3b8;
    }
    *(int *)(iVar4 + 0x354) = iVar5;
    iVar4 = param_1[0xad];
    if (iVar4 == 0) {
      uRam00000350 = 0;
    }
    else {
      *(int *)(iVar4 + 0x350) = iVar4 + 0x3bc;
    }
  }
  else {
    if (iStack_154 == 0) {
      iVar4 = 0;
    }
    else {
      iVar4 = iStack_154 + 0x260;
    }
    *(int *)(param_1[0xad] + 0x354) = iVar4;
    if (iStack_154 == 0) {
      iVar4 = 0;
    }
    else {
      iVar4 = iStack_154 + 0x26c;
    }
    *(int *)(param_1[0xad] + 0x350) = iVar4;
  }
  iVar4 = param_1[0xad];
  iVar5 = param_1[0xa8];
  if (*(int *)(iVar4 + 0x3c0) != iVar5) {
    ppbStack_178 = (byte **)0x74b4a3;
    func_0x00786370();
    *(int *)(iVar4 + 0x3c0) = iVar5;
    ppbStack_178 = (byte **)0x74b4b0;
    func_0x00783540();
  }
  *(undefined1 *)(param_1[0xad] + 0x2d9) = 1;
  switch(param_1[0xa6]) {
  case 0:
    if (param_1[0x9a] == 0) {
      ppbStack_178 = (byte **)&UNK_00c7f979;
    }
    else {
      ppbStack_178 = (byte **)(param_1[0x9a] + 4);
    }
    piStack_17c = (int *)&UNK_00cb10f8;
    puStack_180 = &UNK_0074b4f6;
    func_0x0040eab0();
    if (iStack_158 == 0) {
      ppbStack_178 = (byte **)0x0;
    }
    else {
      ppbStack_178 = (byte **)(iStack_158 + 4);
    }
    piStack_17c = (int *)&UNK_00cb1108;
    puStack_180 = &UNK_00cb111c;
    puStack_184 = &UNK_0074b523;
    func_0x009cd2c0();
    ppbStack_178 = (byte **)&UNK_0074b52d;
    func_0x0057df70();
    ppbStack_178 = (byte **)param_1[0xaf];
    piStack_17c = (int *)&UNK_0074b53b;
    func_0x00a63130();
    break;
  case 1:
    if (param_1[0x9a] == 0) {
      ppbStack_178 = (byte **)&UNK_00c7f979;
    }
    else {
      ppbStack_178 = (byte **)(param_1[0x9a] + 4);
    }
    piStack_17c = (int *)&UNK_00cb1140;
    puStack_180 = &UNK_0074b563;
    func_0x0040eab0();
    if (iStack_158 == 0) {
      ppbStack_178 = (byte **)0x0;
    }
    else {
      ppbStack_178 = (byte **)(iStack_158 + 4);
    }
    piStack_17c = (int *)&UNK_00cb1150;
    puStack_180 = &UNK_00cb1150;
    goto code_r0x0074b585;
  case 2:
    if (param_1[0x9a] == 0) {
      ppbStack_178 = (byte **)&UNK_00c7f979;
    }
    else {
      ppbStack_178 = (byte **)(param_1[0x9a] + 4);
    }
    piStack_17c = (int *)&UNK_00cb1140;
    puStack_180 = &UNK_0074b5c2;
    func_0x0040eab0();
    if (uStack_164._3_1_ == '\0') {
      if (iStack_158 == 0) {
        ppbStack_178 = (byte **)0x0;
      }
      else {
        ppbStack_178 = (byte **)(iStack_158 + 4);
      }
      piStack_17c = (int *)&UNK_00cb1178;
      puStack_180 = &UNK_00cb1178;
    }
    else {
      if (iStack_158 == 0) {
        ppbStack_178 = (byte **)0x0;
      }
      else {
        ppbStack_178 = (byte **)(iStack_158 + 4);
      }
      piStack_17c = (int *)&UNK_00cb1160;
      puStack_180 = &UNK_00cb1160;
    }
code_r0x0074b585:
    puStack_184 = &UNK_0074b58a;
    func_0x009cd2c0();
    ppbStack_178 = (byte **)&UNK_0074b59a;
    func_0x0057df70();
    break;
  case 3:
    ppbStack_178 = (byte **)0x0;
    piStack_17c = (int *)0xd3d81c;
    puStack_180 = (undefined *)0xd3d7e4;
    puStack_184 = (undefined *)0x0;
    puStack_188 = &UNK_0074b629;
    puStack_188 = (undefined1 *)func_0x009df260();
    puStack_18c = &UNK_0074b62f;
    aiStack_11c[0] = func_0x00c07db2();
    if (aiStack_11c[0] != 0) {
      uStack_104 = 0;
      uStack_f0 = 1;
      uStack_ee = 0;
      uStack_ec = 0;
      uStack_e8 = 0;
      uStack_e4 = 0xffffffff;
      uStack_e0 = 0;
      uStack_100 = 0;
      uStack_fc = 0;
      uStack_f8 = 0;
      uStack_f4 = 0;
      ppbStack_178 = (byte **)&UNK_0074b692;
      func_0x009a8a30();
      ppbStack_178 = (byte **)(*(int *)(aiStack_11c[0] + 700) + 0x2428);
      piStack_17c = (int *)&UNK_0074b6b1;
      func_0x004114e0();
      piStack_17c = (int *)&UNK_00cb1190;
      puStack_180 = auStack_12c;
      puStack_184 = &UNK_0074b6c2;
      func_0x00a697b0();
      puStack_184 = &UNK_0074b6d4;
      piVar8 = (int *)func_0x009cd0e0();
      puStack_184 = &UNK_0074b6e1;
      func_0x00401000();
      auStack_134[0] = 0;
      if (piVar8 != (int *)0x0) {
        puStack_184 = auStack_c4;
        puStack_188 = &UNK_0074b700;
        piVar8 = (int *)(**(code **)(*piVar8 + 0x28))();
        iStack_150 = piVar8[3] - piVar8[1];
        iStack_15c = 0;
        iStack_158 = 0;
        iStack_154 = piVar8[2] - *piVar8;
        puStack_188 = (undefined1 *)0x1;
        puStack_18c = auStack_114;
        piStack_194 = &iStack_15c;
        piStack_198 = (int *)&UNK_0074b739;
        piStack_190 = piStack_194;
        piStack_194 = (int *)func_0x00a3f490();
        piStack_198 = (int *)&UNK_0074b742;
        func_0x00a405a0();
        piStack_198 = (int *)&UNK_0074b747;
        func_0x00425160();
        piStack_198 = (int *)0x1;
        puStack_19c = &UNK_0074b74e;
        puStack_19c = (undefined *)func_0x00a67be0();
        puStack_1a0 = (undefined4 *)&UNK_0074b758;
        func_0x009a8ca0();
      }
      puStack_184 = (undefined *)0xf4;
      puStack_188 = &UNK_0074b764;
      iVar4 = func_0x0097c5d0();
      if (iVar4 == 0) {
        iVar4 = 0;
      }
      else {
        puStack_184 = (undefined *)param_1[0xa8];
        puStack_188 = (undefined1 *)param_1[0xad];
        puStack_18c = &UNK_0074b784;
        iVar4 = func_0x00749430();
      }
      param_1[0xb7] = iVar4;
      puStack_184 = &UNK_00c96f80;
      puStack_188 = auStack_120;
      puStack_18c = &UNK_0074b79f;
      func_0x00a697b0();
      puStack_18c = &UNK_0074b7b1;
      iVar4 = func_0x009cd110();
      puStack_18c = &UNK_0074b7c0;
      func_0x00401000();
      uStack_128 = 0;
      if (iVar4 != 0) {
        puStack_18c = &UNK_0074b7dd;
        (**(code **)(*(int *)param_1[0xb7] + 4))();
        puStack_18c = &UNK_0074b7eb;
        func_0x005121b0();
        puStack_18c = &UNK_00cb119c;
        piStack_190 = &uStack_144;
        piStack_194 = (int *)&UNK_0074b804;
        piStack_194 = (int *)func_0x00a697b0();
        puStack_19c = &UNK_00cb11a8;
        puStack_1a0 = auStack_134;
        puStack_1a4 = &UNK_0074b817;
        piStack_198 = extraout_ECX;
        puStack_1a0 = (undefined4 *)func_0x00a697b0();
        puStack_1a4 = &UNK_0074b82e;
        func_0x007492d0();
        puStack_1a4 = &UNK_0074b837;
        func_0x00401000();
        uStack_144 = 0;
        puStack_1a4 = &UNK_0074b846;
        func_0x00401000();
        uStack_144 = 0;
        *(int *)(iVar4 + 0x3a8) = param_1[0xb7] + 0xc4;
      }
      puStack_18c = &UNK_00c96f74;
      piStack_190 = aiStack_11c;
      piStack_194 = (int *)&UNK_0074b871;
      func_0x00a697b0();
      piStack_194 = (int *)&UNK_0074b883;
      iVar4 = func_0x009cd110();
      piStack_194 = (int *)&UNK_0074b88e;
      func_0x00401000();
      uStack_124 = 0;
      if (iVar4 != 0) {
        piStack_194 = (int *)&UNK_0074b8a7;
        (**(code **)(*(int *)param_1[0xb7] + 4))();
        piStack_194 = (int *)&UNK_0074b8b5;
        func_0x005121b0();
        *(int *)(iVar4 + 0x3a8) = param_1[0xb7] + 0xc4;
      }
      piStack_194 = (int *)&UNK_00c96fa8;
      piStack_198 = &iStack_158;
      puStack_19c = &UNK_0074b8d8;
      func_0x00a697b0();
      puStack_19c = &UNK_0074b8ea;
      iVar4 = func_0x009cd110();
      puStack_19c = &UNK_0074b8f5;
      func_0x00401000();
      pbStack_160 = (byte *)0x0;
      if (iVar4 != 0) {
        puStack_19c = &UNK_0074b90e;
        (**(code **)(*(int *)param_1[0xb7] + 4))();
        puStack_19c = &UNK_0074b91c;
        func_0x005121b0();
        *(int *)(iVar4 + 0x3a8) = param_1[0xb7] + 0xc4;
      }
      puStack_19c = &UNK_00c96fc8;
      puStack_1a0 = auStack_134;
      puStack_1a4 = &UNK_0074b93e;
      func_0x00a697b0();
      puStack_1a4 = &UNK_0074b950;
      iVar4 = func_0x009cd110();
      puStack_1a4 = &UNK_0074b95b;
      func_0x00401000();
      uStack_13c = 0;
      if (iVar4 != 0) {
        puStack_1a4 = (undefined *)0x74b974;
        (**(code **)(*(int *)param_1[0xb7] + 4))();
        puStack_1a4 = (undefined *)0x74b985;
        func_0x005121b0();
      }
      puStack_1a4 = &UNK_00c96f9c;
      func_0x00a697b0(&uStack_14c);
      piVar8 = (int *)func_0x009cd110();
      piStack_190 = piVar8;
      func_0x00401000();
      iStack_154 = 0;
      if (piVar8 != (int *)0x0) {
        (**(code **)(*(int *)param_1[0xb7] + 4))();
        func_0x00a697b0(&uStack_140,&UNK_00c96f9c);
        FUN_005c2100();
        func_0x00401000();
        piVar8 = piStack_198;
        uStack_148 = 0;
        func_0x005121b0();
        piVar8[0xea] = param_1[0xb7] + 0xc4;
        cVar3 = *(char *)(param_1[0xad] + 0x3ce);
        if (*(char *)((int)piVar8 + 0x359) != cVar3) {
          piVar8[2] = piVar8[2] | 7;
          *(char *)((int)piVar8 + 0x359) = cVar3;
        }
        func_0x00a638a0();
      }
      func_0x00a697b0(&stack0xfffffe94,&UNK_00cb11a8);
      iVar4 = func_0x009cd080();
      func_0x00401000();
      puStack_174 = (undefined *)0x0;
      if (iVar4 != 0) {
        (**(code **)(*(int *)param_1[0xb7] + 4))();
        func_0x00a6b9c0();
      }
      puVar9 = &stack0xfffffe90;
      func_0x00a697b0(puVar9,&UNK_00c96f6c);
      cVar3 = (char)((uint)puVar9 >> 0x18);
      piVar8 = (int *)func_0x009cd110();
      func_0x00401000();
      ppbStack_178 = (byte **)0x0;
      if (piVar8 != (int *)0x0) {
        (**(code **)(*piVar8 + 0x68))();
      }
      puVar9 = &stack0xfffffe90;
      func_0x00a697b0(puVar9,&UNK_00c96ef4);
      cVar10 = (char)((uint)puVar9 >> 0x18);
      piVar8 = (int *)func_0x009cd110();
      func_0x00401000();
      ppbStack_178 = (byte **)0x0;
      if (piVar8 != (int *)0x0) {
        (**(code **)(*(int *)param_1[0xb7] + 4))();
        func_0x005121b0();
        (**(code **)(*piVar8 + 0x68))();
      }
      func_0x00a697b0(&stack0xfffffe90,&UNK_00c96f00);
      iVar4 = func_0x009cd110();
      func_0x00401000();
      ppbStack_178 = (byte **)0x0;
      if (iVar4 != 0) {
        if (*(char *)(iVar4 + 0x359) != cVar3) {
          *(uint *)(iVar4 + 8) = *(uint *)(iVar4 + 8) | 7;
          *(char *)(iVar4 + 0x359) = cVar3;
        }
        func_0x00a638a0();
      }
      func_0x00a697b0(&puStack_1a4,&UNK_00c96f0c);
      iVar4 = func_0x009cd110();
      func_0x00401000();
      if (iVar4 != 0) {
        if ((bool)*(char *)(iVar4 + 0x359) != (cVar10 == '\0')) {
          *(uint *)(iVar4 + 8) = *(uint *)(iVar4 + 8) | 7;
          *(bool *)(iVar4 + 0x359) = cVar10 == '\0';
        }
        func_0x00a638a0();
      }
      iVar4 = param_1[0xad];
      uVar6 = func_0x009ae560(&UNK_00cb11ec,1);
      func_0x00717810(iVar4,0,uVar6);
      iVar4 = *(int *)(param_1[0xad] + 700);
      if (iVar4 != 0) {
        func_0x0057df70();
        (**(code **)(*(int *)(iVar4 + 4) + 0x68))();
      }
      func_0x009a8bc0();
    }
  }
  if (param_1[0xaf] != 0) {
    ppbStack_178 = (byte **)0x74bc78;
    func_0x009df290();
  }
  if (iStack_154 != 0) {
    ppbStack_178 = (byte **)param_1;
    piStack_17c = (int *)0x74bc85;
    func_0x0074aae0();
  }
  ppbStack_178 = (byte **)0x74bc8e;
  func_0x00401000();
  ppbStack_178 = (byte **)0x74bc97;
  func_0x00401000();
  return 0;
}


