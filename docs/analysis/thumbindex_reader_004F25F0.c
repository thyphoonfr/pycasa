// Address: 004f25f0
// Function: FUN_004f25f0
// Target requested: 0x004F25F0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __thiscall FUN_004f25f0(int param_1,int param_2)

{
  uint uVar1;
  int iVar2;
  uint3 uVar3;
  char cVar4;
  int iVar5;
  uint uVar6;
  byte *pbVar7;
  int iVar8;
  int *piVar9;
  bool bVar10;
  code *pcVar11;
  float10 fVar12;
  float10 fVar13;
  undefined *puVar14;
  byte *pbStack_a88;
  undefined4 uStack_a84;
  uint uStack_a80;
  undefined4 uStack_a7c;
  int iStack_a78;
  int iStack_a74;
  byte *pbStack_a70;
  undefined4 uStack_a6c;
  undefined4 uStack_a68;
  int iStack_a64;
  int iStack_a60;
  undefined1 uStack_a5c;
  undefined1 uStack_a5b;
  undefined4 uStack_a54;
  int iStack_a4c;
  int iStack_a48;
  undefined4 uStack_a44;
  int iStack_a34;
  byte *pbStack_a30;
  byte *pbStack_828;
  byte *pbStack_620;
  byte *pbStack_418;
  byte *pbStack_210;
  uint uStack_4;
  
  uVar3 = (uint3)uStack_a84;
  uStack_4 = _DAT_00d24004 ^ (uint)&pbStack_a88;
  bVar10 = false;
  iStack_a64 = param_2;
  uStack_a6c = 0;
  uStack_a84 = (byte *)(uint)(uint3)uStack_a84;
  if (param_1 == 4) {
    param_1 = 3;
    uStack_a84 = (byte *)CONCAT13(1,uVar3);
  }
  else {
    if (param_1 == 0) {
LAB_004f266b:
      uStack_a84._0_3_ = CONCAT12(1,(ushort)uStack_a84);
    }
    else {
      bVar10 = true;
      uStack_a6c = 0;
      func_0x00407a20(&iStack_a4c,&UNK_00c7eafc,&UNK_00c8647c);
      iVar8 = func_0x004019b0();
      uStack_a84._0_3_ = (uint3)(ushort)uStack_a84;
      if (iVar8 == 0) goto LAB_004f266b;
    }
    if (bVar10) {
      func_0x00401000();
      uStack_a44 = 0;
      func_0x00401000();
    }
    if (uStack_a84._2_1_ != '\0') goto LAB_004f2d75;
  }
  pbStack_a70 = (byte *)0x0;
  if (param_1 == 1) {
    uStack_a80 = 0;
    func_0x00985ff0(&UNK_00c86490);
    func_0x005c2100();
    func_0x00401000();
  }
  else {
    if (param_1 == 2) {
      puVar14 = &UNK_00c864a8;
    }
    else {
      if (param_1 != 3) goto LAB_004f270f;
      puVar14 = &UNK_00c864bc;
    }
    uStack_a80 = 0;
    func_0x00985ff0(puVar14);
    func_0x005c2100();
    func_0x00401000();
  }
LAB_004f270f:
  func_0x004089e0(&pbStack_a70);
  func_0x00980ec0(1);
  if (iStack_a34 == 0) {
    iStack_a34 = 0;
  }
  else {
    iStack_a34 = iStack_a34 + 4;
  }
  iStack_a64 = 0;
  iStack_a60 = 0;
  uStack_a5b = 0;
  uStack_a5c = 0;
  uStack_a54 = 0;
  uStack_a68 = func_0x0099d0c0(&iStack_a64,iStack_a34,&UNK_00c7ebe4,0x2000);
  iVar8 = iStack_a74;
  if (pbStack_a70 != (byte *)0x0) {
    func_0x00c07782(pbStack_a70,&UNK_00c864d4);
    uVar6 = *(uint *)(param_2 + 0x3f4) >> 1;
    uStack_a80 = 0;
    if (uVar6 != 0) {
      do {
        piVar9 = (int *)(*(int *)(iStack_a78 + 0x3f0) + uStack_a80 * 4);
        if (*piVar9 == 0) {
          piVar9 = (int *)(iStack_a78 + 0x3f8);
        }
        else {
          piVar9 = (int *)*piVar9;
        }
        pbStack_a88 = (byte *)0x0;
        if ((((*(char *)((int)piVar9 + 0x1d) == '\0') || (iVar8 = piVar9[6], iVar8 == 1)) ||
            (iVar8 == 0x19)) || ((iVar8 == 0x3e9 || (iVar8 == 5)))) {
          if (*piVar9 != 0) {
            func_0x00401000();
            pbStack_a88 = (byte *)*piVar9;
            if ((pbStack_a88 != (byte *)0x0) &&
               ((0x7f < *pbStack_a88 || (cVar4 = InterlockedIncrement(pbStack_a88), cVar4 == -1))))
            {
              func_0x00985a60();
            }
          }
        }
        else {
          uVar1 = piVar9[8];
          if (uVar1 < uVar6) {
            if (*(int *)(*(int *)(iStack_a78 + 0x3f0) + uVar1 * 4) == 0) {
              iVar8 = iStack_a78 + 0x3f8;
            }
            else {
              iVar8 = *(int *)(*(int *)(iStack_a78 + 0x3f0) + uVar1 * 4);
            }
            if (*(int *)(iVar8 + 0x18) == 0) goto LAB_004f2887;
            func_0x00985ec0(iVar8,piVar9);
            if ((uStack_a84 != (byte *)0x0) && (*uStack_a84 < 0x80)) {
              InterlockedIncrement(uStack_a84);
            }
            func_0x00401000();
            uStack_a7c = 0;
          }
          else {
LAB_004f2887:
            pbVar7 = *(byte **)(iStack_a78 + 0x550);
            if ((pbVar7 != (byte *)0x0) && (*pbVar7 < 0x80)) {
              InterlockedIncrement(pbVar7);
            }
          }
          func_0x005c2100();
          func_0x00401000();
        }
        func_0x009958c0(&pbStack_a88,0,_DAT_00d4a61c);
        iVar2 = piVar9[7];
        cVar4 = *(char *)((int)piVar9 + 0x1d);
        iVar8 = piVar9[6];
        iVar5 = piVar9[5];
        fVar12 = (float10)func_0x0098b650();
        fVar13 = (float10)func_0x0098b650();
        if (pbStack_a88 == (byte *)0x0) {
          pbVar7 = (byte *)0x0;
        }
        else {
          pbVar7 = pbStack_a88 + 4;
        }
        func_0x00c07782(pbStack_a70,&UNK_00c8650c,pbVar7,(double)fVar13,(double)fVar12,iVar5,iVar8,
                        (int)(char)iVar2,(int)cVar4);
        func_0x00401000();
        uStack_a80 = uStack_a80 + 1;
        uVar6 = *(uint *)(iStack_a78 + 0x3f4) >> 1;
        param_2 = iStack_a78;
      } while (uStack_a80 < uVar6);
    }
    func_0x009917f0(&UNK_00c86524);
    iVar8 = iStack_a4c;
    if (iStack_a48 != 0) {
      uVar6 = 0;
      if ((*(uint *)(param_2 + 0x3f4) & 0xfffffffe) != 0) {
        do {
          if (*(int *)(*(int *)(param_2 + 0x3f0) + uVar6 * 4) == 0) {
            iVar8 = param_2 + 0x3f8;
          }
          else {
            iVar8 = *(int *)(*(int *)(param_2 + 0x3f0) + uVar6 * 4);
          }
          if (*(int *)(iVar8 + 0x18) == 4) {
            if (*(int *)(*(int *)(param_2 + 0x3f0) + uVar6 * 4) == 0) {
              piVar9 = (int *)(param_2 + 0x3f8);
            }
            else {
              piVar9 = *(int **)(*(int *)(param_2 + 0x3f0) + uVar6 * 4);
            }
            if (*piVar9 == 0) {
              iVar8 = 0;
            }
            else {
              iVar8 = *piVar9 + 4;
            }
            func_0x00c07782(iStack_a48,&UNK_00c86534,iVar8);
          }
          iVar8 = *(int *)(param_2 + 0x3f0);
          if (*(int *)(iVar8 + uVar6 * 4) == 0) {
            iVar5 = param_2 + 0x3f8;
          }
          else {
            iVar5 = *(int *)(iVar8 + uVar6 * 4);
          }
          if (*(int *)(iVar5 + 0x18) == 5) {
            if (*(int *)(iVar8 + uVar6 * 4) == 0) {
              piVar9 = (int *)(param_2 + 0x3f8);
            }
            else {
              piVar9 = *(int **)(iVar8 + uVar6 * 4);
            }
            if (*piVar9 == 0) {
              iVar8 = 0;
            }
            else {
              iVar8 = *piVar9 + 4;
            }
            func_0x00c07782(iStack_a48,&UNK_00c86544,iVar8);
          }
          uVar6 = uVar6 + 1;
        } while (uVar6 < *(uint *)(param_2 + 0x3f4) >> 1);
      }
      if (uStack_a84._3_1_ != '\0') {
        if (pbStack_a30 == (byte *)0x0) {
          pbVar7 = (byte *)0x0;
        }
        else {
          pbVar7 = pbStack_a30 + 4;
        }
        func_0x00981280(pbVar7,1,0);
      }
      iVar8 = iStack_a4c;
      if (iStack_a4c == 0) {
LAB_004f2b37:
        func_0x0099d890();
      }
      else {
        iVar5 = InterlockedDecrement(iStack_a4c);
        if (iVar5 == 0) {
          func_0x0097caf0(iVar8);
          iStack_a4c = 0;
          goto LAB_004f2b37;
        }
      }
      iVar8 = iStack_a60;
      if (iStack_a60 == 0) {
LAB_004f2b5c:
        func_0x0099d890();
      }
      else {
        iVar5 = InterlockedDecrement(iStack_a60);
        if (iVar5 == 0) {
          func_0x0097caf0(iVar8);
          iStack_a60 = 0;
          goto LAB_004f2b5c;
        }
      }
      pbVar7 = pbStack_210;
      pcVar11 = InterlockedIncrement_exref;
      if ((pbStack_210 != (byte *)0x0) && (*pbStack_210 < 0x80)) {
        cVar4 = InterlockedDecrement(pbStack_210);
        pcVar11 = InterlockedIncrement_exref;
        if (cVar4 == '\x7f') {
          if (*pbVar7 < 0x80) {
            cVar4 = InterlockedIncrement(pbVar7);
          }
          else {
            cVar4 = -1;
          }
        }
        if (cVar4 == '\0') {
          func_0x0097caf0(pbStack_210);
        }
      }
      pbVar7 = pbStack_418;
      pbStack_210 = (byte *)0x0;
      if ((pbStack_418 != (byte *)0x0) && (*pbStack_418 < 0x80)) {
        cVar4 = InterlockedDecrement(pbStack_418);
        if (cVar4 == '\x7f') {
          if (*pbVar7 < 0x80) {
            cVar4 = (*pcVar11)(pbVar7);
          }
          else {
            cVar4 = -1;
          }
        }
        if (cVar4 == '\0') {
          func_0x0097caf0(pbStack_418);
        }
      }
      pbVar7 = pbStack_620;
      pbStack_418 = (byte *)0x0;
      if ((pbStack_620 != (byte *)0x0) && (*pbStack_620 < 0x80)) {
        cVar4 = InterlockedDecrement(pbStack_620);
        if (cVar4 == '\x7f') {
          if (*pbVar7 < 0x80) {
            cVar4 = (*pcVar11)(pbVar7);
          }
          else {
            cVar4 = -1;
          }
        }
        if (cVar4 == '\0') {
          func_0x0097caf0(pbStack_620);
        }
      }
      pbVar7 = pbStack_828;
      pbStack_620 = (byte *)0x0;
      if ((pbStack_828 != (byte *)0x0) && (*pbStack_828 < 0x80)) {
        cVar4 = InterlockedDecrement(pbStack_828);
        if (cVar4 == '\x7f') {
          if (*pbVar7 < 0x80) {
            cVar4 = (*pcVar11)(pbVar7);
          }
          else {
            cVar4 = -1;
          }
        }
        if (cVar4 == '\0') {
          func_0x0097caf0(pbStack_828);
        }
      }
      pbVar7 = pbStack_a30;
      pbStack_828 = (byte *)0x0;
      if ((pbStack_a30 != (byte *)0x0) && (*pbStack_a30 < 0x80)) {
        cVar4 = InterlockedDecrement(pbStack_a30);
        if (cVar4 == '\x7f') {
          if (*pbVar7 < 0x80) {
            cVar4 = (*pcVar11)(pbVar7);
          }
          else {
            cVar4 = -1;
          }
        }
        if (cVar4 == '\0') {
          func_0x0097caf0(pbStack_a30);
        }
      }
      pbVar7 = pbStack_a70;
      pbStack_a30 = (byte *)0x0;
      if ((pbStack_a70 != (byte *)0x0) && (*pbStack_a70 < 0x80)) {
        cVar4 = InterlockedDecrement(pbStack_a70);
        if (cVar4 == '\x7f') {
          if (*pbVar7 < 0x80) {
            cVar4 = (*pcVar11)(pbVar7);
          }
          else {
            cVar4 = -1;
          }
        }
        if (cVar4 == '\0') {
          func_0x0097caf0(pbVar7);
        }
      }
      goto LAB_004f2d75;
    }
    if (iStack_a4c == 0) {
LAB_004f29e3:
      func_0x0099d890();
    }
    else {
      iVar5 = InterlockedDecrement(iStack_a4c);
      if (iVar5 == 0) {
        func_0x0097caf0(iVar8);
        iStack_a4c = 0;
        goto LAB_004f29e3;
      }
    }
    iVar8 = iStack_a60;
    if (iStack_a60 == 0) {
LAB_004f2a08:
      func_0x0099d890();
    }
    else {
      iVar5 = InterlockedDecrement(iStack_a60);
      if (iVar5 == 0) {
        func_0x0097caf0(iVar8);
        iStack_a60 = 0;
        goto LAB_004f2a08;
      }
    }
    func_0x00408c00();
    func_0x00401000();
    goto LAB_004f2d75;
  }
  if (iStack_a74 == 0) {
LAB_004f278f:
    func_0x0099d890();
  }
  else {
    iVar5 = InterlockedDecrement(iStack_a74);
    if (iVar5 == 0) {
      func_0x0097caf0(iVar8);
      iStack_a74 = 0;
      goto LAB_004f278f;
    }
  }
  func_0x00408c00();
  func_0x00401000();
LAB_004f2d75:
  func_0x00bef10a();
  return;
}


