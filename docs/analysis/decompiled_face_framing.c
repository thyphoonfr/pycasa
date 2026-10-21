// =========================================================
// Target Address: 00570511
// Function: FUN_00570511 @ 00570511

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_00570511(uint param_1)

{
  undefined4 uVar1;
  int iVar2;
  uint uVar3;
  uint uVar4;
  int *unaff_EBX;
  int unaff_EBP;
  int unaff_ESI;
  undefined4 uStack00000010;
  undefined4 in_stack_00000028;
  char in_stack_0000002c;
  undefined4 uStack00000038;
  
  uStack00000010 = 1;
  uStack00000038 = 1;
  func_0x00407a20(&stack0x00000018,&UNK_00c7eafc,&UNK_00c8f570);
  iVar2 = func_0x004019b0();
  in_stack_0000002c = iVar2 != 0;
  if ((param_1 & 1) != 0) {
    func_0x00401000();
    func_0x00401000();
    uStack00000010 = 0;
  }
  if (in_stack_0000002c == '\0') {
    if (unaff_ESI != -1) {
      func_0x00506270();
    }
    if (*unaff_EBX != -1) {
      if (((_DAT_00d67914 == 0) || (iVar2 = func_0x009c2fc0(), iVar2 == 0)) ||
         (*(char *)(iVar2 + 0x20c) != '\0')) {
        uVar1 = *(undefined4 *)(unaff_EBP + 0xe68);
        iVar2 = *(int *)(unaff_EBP + 700);
        func_0x006abd70(*unaff_EBX);
        *(undefined4 *)(iVar2 + 0x2f34) = uVar1;
        return 0;
      }
      in_stack_0000002c = 0;
      func_0x005696c0();
      if (*(int *)(unaff_EBP + 0xea8) != 0) {
        uVar3 = func_0x00562130(param_1);
        uVar4 = func_0x00562130(in_stack_00000028);
        in_stack_00000028 = CONCAT31(in_stack_00000028._1_3_,uVar4 < uVar3);
      }
      iVar2 = func_0x0056b020(in_stack_00000028);
      if ((iVar2 != *unaff_EBX) && (iVar2 != -1)) {
        *unaff_EBX = iVar2;
        *(int *)(unaff_EBP + 0xe68) = iVar2;
        func_0x00506270();
        if (*(int *)(unaff_EBP + 0xea8) != 0) {
          func_0x00717c50(*(undefined4 *)(unaff_EBP + 0xe68));
        }
      }
      uVar1 = *(undefined4 *)(unaff_EBP + 0xe68);
      iVar2 = func_0x0056b5c0();
      func_0x006abd70(*unaff_EBX);
      *(undefined4 *)(iVar2 + 0x74) = uVar1;
      func_0x0056a9a0();
    }
  }
  return 0;
}



// =========================================================
// Target Address: 0057a4f0
// Function: FUN_0057a4f0 @ 0057a4f0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int __thiscall FUN_0057a4f0(int param_1,uint param_2,undefined4 param_3,int *param_4)

{
  char cVar1;
  char cVar2;
  int iVar3;
  int iVar4;
  uint unaff_EBX;
  uint unaff_ESI;
  int *piVar5;
  int *unaff_EDI;
  undefined4 uStack_54;
  undefined4 uStack_50;
  undefined4 uStack_4c;
  undefined8 uStack_44;
  int aiStack_3c [7];
  undefined1 uStack_1f;
  
  uStack_4c = 0;
  cVar1 = func_0x00562d00();
  uStack_50 = CONCAT13(cVar1,(undefined3)uStack_50);
  cVar2 = '\0';
  if (cVar1 != '\0') {
    func_0x006d0600(0xffffffff,0);
    cVar2 = uStack_50._3_1_;
  }
  iVar4 = _DAT_00d67aa0;
  if (((char)param_4[2] == '\0') || (cVar2 != '\0')) {
    iVar4 = (**(code **)(*(int *)(*(int *)(param_1 + 0x4c) + 0x58) + 4))(param_2,param_3,param_4);
    return iVar4;
  }
  aiStack_3c[2] = _DAT_00d67aa4;
  GetCurrentThread();
  iVar3 = GetCurrentThreadId();
  if (iVar3 == iVar4) {
    func_0x0052e1f0(param_1 + -0x270);
  }
  piVar5 = *(int **)(*(int *)(param_1 + 0x4c) + 0x346c);
  aiStack_3c[0] = piVar5[5];
  uStack_44 = (double)CONCAT44(piVar5,(undefined4)uStack_44);
  (**(code **)(*piVar5 + 0xc))(0,0);
  QueryPerformanceCounter(&uStack_50);
  uStack_44 = (double)CONCAT44(uStack_50,uStack_54);
  if ((*(char *)(param_1 + 0x30bf) != '\0') || (*(char *)(param_1 + 0x30fc) != '\0')) {
    unaff_EBX = 1;
    func_0x00407a20(aiStack_3c,&UNK_00c7eafc,&UNK_00c8f570);
    iVar4 = func_0x004019b0();
    unaff_ESI = CONCAT13(1,(int3)unaff_ESI);
    if (iVar4 != 0) goto LAB_0057a5ed;
  }
  unaff_ESI = unaff_ESI & 0xffffff;
LAB_0057a5ed:
  if ((unaff_EBX & 1) != 0) {
    func_0x00401000();
    aiStack_3c[2] = 0;
    func_0x00401000();
  }
  if ((char)(unaff_ESI >> 0x18) == '\0') {
    iVar4 = func_0x006d0180(*(undefined4 *)(*(int *)(param_1 + 0x4c) + 0x346c),param_2,param_3,
                            param_4);
    if (iVar4 != 0) {
      (**(code **)(*piVar5 + 0xc))(unaff_ESI,0);
      return iVar4;
    }
  }
  else {
    piVar5 = aiStack_3c;
    for (iVar4 = 10; iVar4 != 0; iVar4 = iVar4 + -1) {
      *piVar5 = *param_4;
      param_4 = param_4 + 1;
      piVar5 = piVar5 + 1;
    }
    func_0x00506270(&stack0xffffffa8);
    if (unaff_ESI != param_2) {
      uStack_1f = 1;
    }
    iVar4 = func_0x006d0180(*(undefined4 *)(*(int *)(param_1 + 0x4c) + 0x346c),param_2,param_3,
                            (int)&uStack_44 + 4);
    piVar5 = unaff_EDI;
    if (iVar4 != 0) {
      (**(code **)(*unaff_EDI + 0xc))(unaff_ESI,0);
      return iVar4;
    }
  }
  func_0x009a51b0(&stack0xffffffa8);
  (**(code **)(*piVar5 + 0xc))(unaff_EDI,0);
  return 0;
}



// =========================================================
// Target Address: 005c785f
// Function: FUN_005c785f @ 005c785f

undefined4 FUN_005c785f(void)

{
  int iVar1;
  undefined4 uStack0000002c;
  
  uStack0000002c = 1;
  func_0x00407a20(&stack0x0000000c,&UNK_00c7eafc,&UNK_00c8f570);
  iVar1 = func_0x004019b0();
  func_0x00401000();
  func_0x00401000();
  if (iVar1 == 0) {
    func_0x00506400();
  }
  return 0;
}



// =========================================================
// Target Address: 005cb316
// No function found or created at 005cb316

// =========================================================
// Target Address: 005e5290
// Function: FUN_005e5290 @ 005e5290

undefined4 FUN_005e5290(undefined4 param_1,undefined4 param_2)

{
  undefined1 auStack_1c [20];
  int iStack_8;
  
  func_0x00407a20(auStack_1c,&UNK_00c7eafc,&UNK_00c8f570);
  func_0x00401900();
  func_0x00401000();
  func_0x00401000();
  func_0x00767e50(*(undefined4 *)(iStack_8 + 0xea0),param_2);
  return 0;
}



// =========================================================
// Target Address: 005e8bf2
// No function found or created at 005e8bf2

// =========================================================
// Target Address: 00787d7a
// No function found or created at 00787d7a

// =========================================================
// Target Address: 00412d26
// No function found or created at 00412d26

// =========================================================
// Target Address: 009b93f0
// Function: FUN_009b93f0 @ 009b93f0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_009b93f0(void)

{
  float fVar1;
  float fVar2;
  uint *in_EAX;
  uint uVar3;
  uint uVar4;
  uint unaff_ESI;
  uint unaff_EDI;
  
  uVar4 = *in_EAX;
  if ((((uVar4 != 0) || (in_EAX[2] != 0)) || (in_EAX[1] != 0)) || (in_EAX[3] != 0)) {
    fVar1 = (float)(int)unaff_ESI;
    if ((int)unaff_ESI < 0) {
      fVar1 = fVar1 + _DAT_00cf39e4;
    }
    fVar1 = fVar1 / (float)_DAT_00cf3b78;
    fVar2 = (float)(int)unaff_EDI;
    if ((int)unaff_EDI < 0) {
      fVar2 = fVar2 + _DAT_00cf39e4;
    }
    fVar2 = fVar2 / (float)_DAT_00cf3b78;
    uVar3 = in_EAX[2];
    if ((int)uVar3 < (int)uVar4) {
      in_EAX[2] = uVar4;
      *in_EAX = uVar3;
    }
    uVar4 = in_EAX[3];
    if ((int)uVar4 < (int)in_EAX[1]) {
      in_EAX[3] = in_EAX[1];
      in_EAX[1] = uVar4;
    }
    uVar4 = (uint)ROUND((float)(int)*in_EAX * fVar1);
    if ((int)uVar4 < 0) {
      uVar3 = 0;
    }
    else {
      uVar3 = unaff_ESI - 1;
      if (uVar4 <= unaff_ESI - 1) {
        uVar3 = uVar4;
      }
    }
    *in_EAX = uVar3;
    uVar4 = (uint)ROUND((float)(int)in_EAX[2] * fVar1);
    if ((int)uVar4 < 1) {
      uVar4 = 1;
    }
    else if (unaff_ESI < uVar4) {
      uVar4 = unaff_ESI;
    }
    in_EAX[2] = uVar4;
    uVar4 = (uint)ROUND((float)(int)in_EAX[1] * fVar2);
    if ((int)uVar4 < 0) {
      uVar3 = 0;
    }
    else {
      uVar3 = unaff_EDI - 1;
      if (uVar4 <= unaff_EDI - 1) {
        uVar3 = uVar4;
      }
    }
    in_EAX[1] = uVar3;
    uVar4 = (uint)ROUND((float)(int)in_EAX[3] * fVar2);
    if ((int)uVar4 < 1) {
      uVar4 = 1;
    }
    else if (unaff_EDI < uVar4) {
      uVar4 = unaff_EDI;
    }
    in_EAX[3] = uVar4;
    if ((int)in_EAX[2] <= (int)*in_EAX) {
      *in_EAX = in_EAX[2] - 1;
    }
    if ((int)uVar4 <= (int)in_EAX[1]) {
      in_EAX[1] = uVar4 - 1;
    }
  }
  return 0;
}



// =========================================================
// Target Address: 009b9290
// Function: FUN_009b9290 @ 009b9290

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __fastcall FUN_009b9290(undefined4 param_1,int param_2,int param_3)

{
  float fVar1;
  float fVar2;
  int *in_EAX;
  int iVar3;
  
  if ((((*in_EAX != 0) || (in_EAX[2] != 0)) || (in_EAX[1] != 0)) || (in_EAX[3] != 0)) {
    if ((param_3 == 0) || (param_2 == 0)) {
      return 0xffffffff;
    }
    fVar1 = (float)param_3;
    if (param_3 < 0) {
      fVar1 = fVar1 + _DAT_00cf39e4;
    }
    fVar1 = (float)_DAT_00cf3b78 / fVar1;
    fVar2 = (float)param_2;
    if (param_2 < 0) {
      fVar2 = fVar2 + _DAT_00cf39e4;
    }
    fVar2 = (float)_DAT_00cf3b78 / fVar2;
    iVar3 = (int)ROUND((float)*in_EAX * fVar1);
    if (iVar3 < 0) {
      iVar3 = 0;
    }
    else if (0xfffe < iVar3) {
      iVar3 = 0xfffe;
    }
    *in_EAX = iVar3;
    iVar3 = (int)ROUND((float)in_EAX[2] * fVar1);
    if (iVar3 < 1) {
      iVar3 = 1;
    }
    else if (0xffff < iVar3) {
      iVar3 = 0xffff;
    }
    in_EAX[2] = iVar3;
    iVar3 = (int)ROUND((float)in_EAX[1] * fVar2);
    if (iVar3 < 0) {
      iVar3 = 0;
    }
    else if (0xfffe < iVar3) {
      iVar3 = 0xfffe;
    }
    in_EAX[1] = iVar3;
    iVar3 = (int)ROUND((float)in_EAX[3] * fVar2);
    if (iVar3 < 1) {
      iVar3 = 1;
    }
    else if (0xffff < iVar3) {
      iVar3 = 0xffff;
    }
    in_EAX[3] = iVar3;
    if (in_EAX[2] <= *in_EAX) {
      *in_EAX = in_EAX[2] + -1;
    }
    if (iVar3 <= in_EAX[1]) {
      in_EAX[1] = iVar3 + -1;
    }
  }
  return 0;
}



// =========================================================
// Target Address: 00456a15
// Function: FUN_00456a15 @ 00456a15

/* WARNING: Removing unreachable block (ram,0x00458725) */
/* WARNING: Removing unreachable block (ram,0x00456f75) */
/* WARNING: Removing unreachable block (ram,0x00456bf9) */
/* WARNING: Removing unreachable block (ram,0x00458250) */
/* WARNING: Removing unreachable block (ram,0x00459f99) */
/* WARNING: Removing unreachable block (ram,0x0045a2ad) */
/* WARNING: Removing unreachable block (ram,0x0045841c) */
/* WARNING: Removing unreachable block (ram,0x00458106) */
/* WARNING: Removing unreachable block (ram,0x0045840c) */
/* WARNING: Removing unreachable block (ram,0x0045790e) */
/* WARNING: Removing unreachable block (ram,0x004573af) */
/* WARNING: Removing unreachable block (ram,0x00458886) */
/* WARNING: Removing unreachable block (ram,0x0045963d) */
/* WARNING: Removing unreachable block (ram,0x004591f8) */
/* WARNING: Removing unreachable block (ram,0x00457dde) */
/* WARNING: Removing unreachable block (ram,0x00456976) */
/* WARNING: Removing unreachable block (ram,0x004580ef) */
/* WARNING: Removing unreachable block (ram,0x004584fe) */
/* WARNING: Removing unreachable block (ram,0x00459c2b) */
/* WARNING: Removing unreachable block (ram,0x0045a68e) */
/* WARNING: Removing unreachable block (ram,0x0045889a) */
/* WARNING: Removing unreachable block (ram,0x0045850e) */
/* WARNING: Removing unreachable block (ram,0x0045928e) */
/* WARNING: Removing unreachable block (ram,0x0045698a) */
/* WARNING: Heritage AFTER dead removal. Example location: r0x00000000 : 0x00459243 */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */
/* WARNING: Restarted to delay deadcode elimination for space: ram */

undefined4
FUN_00456a15(undefined4 param_1,uint *param_2,undefined4 param_3,undefined4 param_4,
            undefined4 param_5,byte *param_6,byte *param_7,byte *param_8,byte *param_9,
            byte *param_10,byte *param_11,byte *param_12,undefined4 param_13,float param_14,
            byte *param_15,byte *param_16,undefined4 param_17,undefined4 param_18,int param_19,
            byte *param_20,int param_21,uint param_22,int param_23,uint param_24,int param_25,
            uint param_26,int param_27,uint param_28,int param_29,int param_30,int param_31,
            int param_32,undefined4 param_33,int param_34,uint param_35,int param_36,int param_37)

{
  undefined8 *puVar1;
  byte bVar2;
  char cVar3;
  char cVar4;
  char *pcVar5;
  int iVar6;
  int iVar7;
  byte *pbVar8;
  uint *puVar9;
  undefined4 uVar10;
  float fVar11;
  undefined4 *puVar12;
  byte *pbVar13;
  byte *pbVar14;
  uint *puVar15;
  undefined4 uVar16;
  uint uVar17;
  undefined4 extraout_ECX;
  int iVar18;
  char *pcVar19;
  uint uVar20;
  int unaff_EBP;
  int unaff_ESI;
  uint *puVar21;
  uint uVar22;
  byte *pbVar23;
  bool bVar24;
  undefined8 uVar25;
  char cStack000000a4;
  undefined3 uStack000000a5;
  uint in_stack_000000a8;
  int in_stack_000000ac;
  undefined4 in_stack_000000b0;
  undefined4 in_stack_000000b4;
  undefined4 in_stack_000000b8;
  undefined4 in_stack_000000bc;
  float in_stack_000000ec;
  int in_stack_000000f0;
  float in_stack_000000f4;
  float in_stack_000000f8;
  int in_stack_000000fc;
  float in_stack_00000100;
  float in_stack_00000104;
  float in_stack_00000108;
  float in_stack_0000010c;
  int in_stack_00000110;
  byte *in_stack_00000114;
  undefined8 in_stack_00000118;
  undefined4 in_stack_00000120;
  undefined4 in_stack_00000124;
  int in_stack_00000128;
  int *in_stack_0000012c;
  int in_stack_00000130;
  int *in_stack_00000134;
  int in_stack_00000138;
  int *in_stack_0000013c;
  undefined8 in_stack_00000140;
  int in_stack_0000014c;
  byte *in_stack_00000150;
  int in_stack_00000154;
  int *in_stack_00000158;
  int in_stack_0000015c;
  byte *in_stack_00000160;
  
code_r0x00456a15:
  iVar6 = FUN_009b9190();
  if (iVar6 != unaff_ESI) goto LAB_004570bd;
  if (param_31 <= param_29) goto LAB_004570bd;
  if (param_32 <= param_30) goto LAB_004570bd;
  uVar25 = FUN_009b9150();
  iVar6 = *(int *)(unaff_EBP + 8);
  in_stack_00000128 = iVar6 + 0x14f8;
  in_stack_0000012c = (int *)(iVar6 + 0x14d0);
  _param_34 = uVar25;
  iVar7 = GetCurrentThreadId();
  if ((*(int *)(iVar6 + 0x14f0) == 0) || (*(int *)(iVar6 + 0x14f0) != iVar7)) {
    if (*(char *)(iVar6 + 0x14dc) == '\0') {
      (**(code **)(*(int *)(iVar6 + 0x14d0) + 0x18))();
      uVar25 = _param_34;
    }
    else {
      EnterCriticalSection();
      uVar25 = _param_34;
    }
    *(undefined4 *)(iVar6 + 0x14f4) = 0;
    *(int *)(iVar6 + 0x14f0) = iVar7;
  }
  else {
    *(int *)(iVar6 + 0x14f4) = *(int *)(iVar6 + 0x14f4) + 1;
    uVar25 = _param_34;
  }
  param_35 = (uint)((ulonglong)uVar25 >> 0x20);
  param_34 = (int)uVar25;
  if ((*(int *)(iVar6 + 0x1528) == 0) || (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 == 0xffffffff)
     ) {
LAB_00456d54:
    _param_34 = uVar25;
    func_0x0041edb0();
    _cStack000000a4 = CONCAT31(uStack000000a5,1);
  }
  else {
    iVar7 = *(int *)(iVar6 + 0x1528);
    _param_34 = uVar25;
    if (uVar20 < *(uint *)(iVar7 + 0x4c) >> 1) {
      puVar1 = (undefined8 *)(*(int *)(iVar7 + 0x48) + uVar20 * 8);
      if ((*(int *)(*(int *)(iVar7 + 0x48) + uVar20 * 8) != param_34) ||
         (*(int *)((int)puVar1 + 4) != param_35)) {
        *puVar1 = uVar25;
        func_0x006a2a60();
        uVar25 = _param_34;
      }
      goto LAB_00456d54;
    }
    pbVar23 = (byte *)(uVar20 + 1);
    param_7 = (byte *)(*(uint *)(iVar7 + 0x4c) >> 1);
    if (pbVar23 < (byte *)0x10000000) {
      if (pbVar23 == param_7) {
        pbVar8 = *(byte **)(iVar7 + 0x48);
      }
      else if ((*(uint *)(iVar7 + 0x4c) & 1) == 0) {
        if ((uint)((int)pbVar23 * 8) < 0x100000) {
          pbVar13 = (byte *)0x1;
          if (pbVar23 != (byte *)0x0) {
            do {
              pbVar13 = (byte *)((int)pbVar13 * 2);
            } while (pbVar13 <= pbVar23);
          }
        }
        else {
          pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
        }
        if ((uint)((int)param_7 * 8) < 0x100000) {
          pbVar14 = param_7;
          if ((byte *)0x1 < param_7) {
            in_stack_000000f4 = (float)(int)param_7;
            pbVar14 = (byte *)(1 << ((char)((uint)in_stack_000000f4 >> 0x17) + 0x81U & 0x1f));
            param_10 = param_7;
            if (pbVar14 < param_7) {
              pbVar14 = (byte *)((int)pbVar14 * 2);
            }
          }
        }
        else {
          pbVar14 = (byte *)(((uint)param_7 & 0x7ffffc00) + 0x400);
        }
        pbVar8 = *(byte **)(iVar7 + 0x48);
        if (pbVar14 != pbVar13) {
          if (pbVar13 == (byte *)0x0) {
            if (pbVar8 != (byte *)0x0) {
              func_0x0097caf0();
              *(undefined4 *)(iVar7 + 0x48) = 0;
              uVar25 = _param_34;
            }
          }
          else {
            uVar10 = func_0x0097c810();
            *(undefined4 *)(iVar7 + 0x48) = uVar10;
            uVar25 = _param_34;
          }
          pbVar8 = *(byte **)(iVar7 + 0x48);
          if (pbVar8 == (byte *)0x0) {
            *(undefined4 *)(iVar7 + 0x48) = 0;
            *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
            _param_34 = uVar25;
            func_0x0041edb0();
            _cStack000000a4 = CONCAT31(uStack000000a5,1);
            goto LAB_00458824;
          }
        }
        *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1 | (int)pbVar23 * 2;
      }
      else {
        if (pbVar23 == (byte *)0x0) {
          if (*(int *)(iVar7 + 0x48) != 0) {
            func_0x0097caf0();
            *(undefined4 *)(iVar7 + 0x48) = 0;
            uVar25 = _param_34;
          }
        }
        else {
          uVar10 = func_0x0097c810();
          *(undefined4 *)(iVar7 + 0x48) = uVar10;
          uVar25 = _param_34;
        }
        pbVar8 = *(byte **)(iVar7 + 0x48);
        param_10 = pbVar8;
        if (pbVar8 == (byte *)0x0) {
          *(undefined4 *)(iVar7 + 0x48) = 0;
          *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
          _param_34 = uVar25;
          func_0x0041edb0();
          _cStack000000a4 = CONCAT31(uStack000000a5,1);
          goto LAB_00458824;
        }
        *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1 | (int)pbVar23 * 2;
      }
      param_35 = (uint)((ulonglong)uVar25 >> 0x20);
      param_34 = (int)uVar25;
      pbVar13 = param_7;
      if (pbVar8 == (byte *)0x0) goto LAB_00456d54;
      for (; pbVar13 < pbVar23; pbVar13 = pbVar13 + 1) {
        iVar18 = *(int *)(iVar7 + 0x48);
        *(undefined4 *)(iVar18 + (int)pbVar13 * 8) = *(undefined4 *)(iVar6 + 0x1530);
        *(undefined4 *)(iVar18 + 4 + (int)pbVar13 * 8) = *(undefined4 *)(iVar6 + 0x1534);
      }
      iVar6 = *(int *)(*(int *)(iVar6 + 0x1528) + 0x48);
      iVar7 = *(int *)(unaff_EBP + 0xc);
      *(int *)(iVar6 + iVar7 * 8) = param_34;
      *(uint *)(iVar6 + 4 + iVar7 * 8) = param_35;
      _param_34 = uVar25;
      func_0x006a2a60();
      func_0x0041edb0();
      _cStack000000a4 = CONCAT31(uStack000000a5,1);
    }
    else {
      if (*(int *)(iVar7 + 0x48) != 0) {
        func_0x0097caf0();
      }
      *(undefined4 *)(iVar7 + 0x48) = 0;
      *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
      func_0x0041edb0();
      _cStack000000a4 = CONCAT31(uStack000000a5,1);
    }
  }
LAB_00458824:
  pbVar23 = param_11;
  if (in_stack_000000f0 != 0) {
    puVar15 = *(uint **)param_11;
    puVar9 = (uint *)0x0;
    if (puVar15 == (uint *)0x0) {
LAB_00458954:
      if (*(int *)param_11 == 0) {
LAB_004589af:
        if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_004589d9;
        if (puVar15 == (uint *)0x0) {
          puVar21 = (uint *)0x0;
        }
        else {
          puVar21 = puVar15 + 1;
        }
        bVar24 = true;
        iVar6 = 7;
        pcVar5 = "rating";
        do {
          if (iVar6 == 0) break;
          iVar6 = iVar6 + -1;
          bVar24 = *pcVar5 == (char)*puVar21;
          pcVar5 = pcVar5 + 1;
          puVar21 = (uint *)((int)puVar21 + 1);
        } while (bVar24);
LAB_00458a1b:
        if (!bVar24) goto LAB_00458b35;
        iVar6 = func_0x00bf6a2d();
        if (iVar6 == 0) goto LAB_004599fe;
        func_0x008e7cd0();
        uVar20 = param_26;
        if ((param_26 & 1) == 0) {
          uVar22 = param_26 >> 1;
          if (uVar22 * 4 < 0x100000) {
            uVar17 = uVar22;
            if ((uVar22 & uVar22 - 1) == 0) {
              if (uVar22 == 0) {
                uVar17 = 1;
              }
              else {
                uVar17 = uVar22 * 2;
              }
            }
          }
          else {
            uVar17 = (uVar22 & 0x7ffffc00) + 0x400;
          }
          if (uVar22 < uVar17) {
            if (uVar17 == 0) {
              if (param_25 != 0) {
                func_0x0097caf0();
                param_25 = 0;
              }
              goto LAB_00458aeb;
            }
            param_25 = func_0x0097c810();
          }
          if (param_25 != 0) {
            param_26 = (uVar20 & 0xfffffffe) + 2;
            *(undefined4 *)(uVar22 * 4 + param_25) = *(undefined4 *)(unaff_EBP + 0xc);
          }
        }
LAB_00458aeb:
        param_17._3_1_ = '\x01';
        param_6 = (byte *)0x0;
        func_0x00985ff0();
        func_0x004d9aa0(*(int *)(unaff_EBP + 8) + 0x68,&param_24,1);
        func_0x00401000();
        func_0x00407610();
      }
      else {
        if (puVar15 != (uint *)0x0) {
          if (*puVar15 >> 8 != 0) {
            if (puVar15 == (uint *)0x0) {
              puVar21 = (uint *)0x0;
            }
            else {
              puVar21 = puVar15 + 1;
            }
            if ((char)*puVar21 != '\0') {
              if (puVar15 == (uint *)0x0) {
                puVar21 = (uint *)0x0;
              }
              else {
                puVar21 = puVar15 + 1;
              }
              bVar24 = puVar21 == (uint *)&UNK_00c7fad0;
              goto LAB_0045898a;
            }
          }
          goto LAB_004589af;
        }
LAB_004589d9:
        if (*(int *)param_11 == 0) {
LAB_00458b35:
          if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_00458b5f;
          if (puVar15 == (uint *)0x0) {
            puVar21 = (uint *)0x0;
          }
          else {
            puVar21 = puVar15 + 1;
          }
          bVar24 = true;
          iVar6 = 5;
          pcVar5 = "star";
          do {
            if (iVar6 == 0) break;
            iVar6 = iVar6 + -1;
            bVar24 = *pcVar5 == (char)*puVar21;
            pcVar5 = pcVar5 + 1;
            puVar21 = (uint *)((int)puVar21 + 1);
          } while (bVar24);
LAB_00458ba1:
          if (!bVar24) goto LAB_00458d33;
          func_0x008e7cd0();
          uVar20 = param_22;
          if ((param_22 & 1) == 0) {
            uVar22 = param_22 >> 1;
            if (uVar22 * 4 < 0x100000) {
              uVar17 = uVar22;
              if ((uVar22 & uVar22 - 1) == 0) {
                if (uVar22 == 0) {
                  uVar17 = 1;
                }
                else {
                  uVar17 = uVar22 * 2;
                }
              }
            }
            else {
              uVar17 = (uVar22 & 0x7ffffc00) + 0x400;
            }
            if (uVar22 < uVar17) {
              if (uVar17 == 0) {
                if (param_21 != 0) {
                  func_0x0097caf0();
                  param_21 = 0;
                }
                goto LAB_00458c53;
              }
              param_21 = func_0x0097c810();
            }
            if (param_21 != 0) {
              param_22 = (uVar20 & 0xfffffffe) + 2;
              *(undefined4 *)(uVar22 * 4 + param_21) = *(undefined4 *)(unaff_EBP + 0xc);
            }
          }
LAB_00458c53:
          param_17._3_1_ = '\x01';
          if (*(int *)param_12 == 0) {
LAB_00458cf0:
            param_6 = (byte *)0x0;
            func_0x00985ff0();
            puVar12 = &param_20;
            uVar25 = CONCAT44(*(int *)(unaff_EBP + 8) + 0x68,0x458d1c);
            func_0x004da1d0();
          }
          else {
            if (*(int *)param_12 == 0) {
              pcVar5 = (char *)0x0;
            }
            else {
              pcVar5 = (char *)(*(int *)param_12 + 4);
            }
            pcVar19 = "yes";
            if (pcVar5 != "yes") {
              if (pcVar5 != (char *)0x0) {
                do {
                  cVar4 = *pcVar5;
                  if (cVar4 == '\0') {
                    if (*pcVar19 != '\0') goto LAB_00458cf0;
                    break;
                  }
                  cVar3 = *pcVar19;
                  if (('@' < cVar3) && (cVar3 < '[')) {
                    cVar3 = cVar3 + ' ';
                  }
                  if (('@' < cVar4) && (cVar4 < '[')) {
                    cVar4 = cVar4 + ' ';
                  }
                  if ((cVar3 < cVar4) || (cVar4 < cVar3)) goto LAB_00458cf0;
                  pcVar19 = pcVar19 + 1;
                  pcVar5 = pcVar5 + 1;
                } while (*pcVar19 != '\0');
                if (*pcVar5 == '\0') goto LAB_00458cc0;
              }
              goto LAB_00458cf0;
            }
LAB_00458cc0:
            param_6 = (byte *)0x0;
            func_0x00985ff0();
            puVar12 = (undefined4 *)0x1;
            iVar6 = *(int *)(unaff_EBP + 8) + 0x68;
            uVar25 = CONCAT44(&param_20,iVar6);
            func_0x004d9aa0(iVar6,&param_20,1);
          }
          func_0x00401000(uVar25,puVar12);
          func_0x00407610();
        }
        else {
          if (puVar15 != (uint *)0x0) {
            if (*puVar15 >> 8 != 0) {
              if (puVar15 == (uint *)0x0) {
                puVar21 = (uint *)0x0;
              }
              else {
                puVar21 = puVar15 + 1;
              }
              if ((char)*puVar21 != '\0') {
                if (puVar15 == (uint *)0x0) {
                  puVar21 = (uint *)0x0;
                }
                else {
                  puVar21 = puVar15 + 1;
                }
                bVar24 = puVar21 == (uint *)&UNK_00c81448;
                goto LAB_00458a1b;
              }
            }
            goto LAB_00458b35;
          }
LAB_00458b5f:
          if (*(int *)param_11 == 0) {
LAB_00458d33:
            if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_00458d5d;
            if (puVar15 == (uint *)0x0) {
              puVar21 = (uint *)0x0;
            }
            else {
              puVar21 = puVar15 + 1;
            }
            bVar24 = true;
            iVar6 = 7;
            pcVar5 = "hidden";
            do {
              if (iVar6 == 0) break;
              iVar6 = iVar6 + -1;
              bVar24 = *pcVar5 == (char)*puVar21;
              pcVar5 = pcVar5 + 1;
              puVar21 = (uint *)((int)puVar21 + 1);
            } while (bVar24);
LAB_00458d9f:
            if (!bVar24) goto LAB_00458f2f;
            func_0x008e7cd0();
            uVar20 = param_24;
            if ((param_24 & 1) == 0) {
              uVar22 = param_24 >> 1;
              if (uVar22 * 4 < 0x100000) {
                uVar17 = uVar22;
                if ((uVar22 & uVar22 - 1) == 0) {
                  if (uVar22 == 0) {
                    uVar17 = 1;
                  }
                  else {
                    uVar17 = uVar22 * 2;
                  }
                }
              }
              else {
                uVar17 = (uVar22 & 0x7ffffc00) + 0x400;
              }
              if (uVar22 < uVar17) {
                if (uVar17 == 0) {
                  if (param_23 != 0) {
                    func_0x0097caf0();
                    param_23 = 0;
                  }
                  goto LAB_00458e51;
                }
                param_23 = func_0x0097c810();
              }
              if (param_23 != 0) {
                param_24 = (uVar20 & 0xfffffffe) + 2;
                *(undefined4 *)(uVar22 * 4 + param_23) = *(undefined4 *)(unaff_EBP + 0xc);
              }
            }
LAB_00458e51:
            if (*(int *)param_12 == 0) {
LAB_00458eec:
              param_6 = (byte *)0x0;
              func_0x00985ff0();
              puVar12 = &param_22;
              uVar25 = CONCAT44(*(int *)(unaff_EBP + 8) + 0x68,0x458f18);
              func_0x004da1d0();
            }
            else {
              if (*(int *)param_12 == 0) {
                pcVar5 = (char *)0x0;
              }
              else {
                pcVar5 = (char *)(*(int *)param_12 + 4);
              }
              pcVar19 = "yes";
              if (pcVar5 != "yes") {
                if (pcVar5 != (char *)0x0) {
                  do {
                    cVar4 = *pcVar5;
                    if (cVar4 == '\0') {
                      if (*pcVar19 != '\0') goto LAB_00458eec;
                      break;
                    }
                    cVar3 = *pcVar19;
                    if (('@' < cVar3) && (cVar3 < '[')) {
                      cVar3 = cVar3 + ' ';
                    }
                    if (('@' < cVar4) && (cVar4 < '[')) {
                      cVar4 = cVar4 + ' ';
                    }
                    if ((cVar3 < cVar4) || (cVar4 < cVar3)) goto LAB_00458eec;
                    pcVar19 = pcVar19 + 1;
                    pcVar5 = pcVar5 + 1;
                  } while (*pcVar19 != '\0');
                  if (*pcVar5 == '\0') goto LAB_00458ebc;
                }
                goto LAB_00458eec;
              }
LAB_00458ebc:
              param_6 = (byte *)0x0;
              func_0x00985ff0();
              puVar12 = (undefined4 *)0x1;
              iVar6 = *(int *)(unaff_EBP + 8) + 0x68;
              uVar25 = CONCAT44(&param_22,iVar6);
              func_0x004d9aa0(iVar6,&param_22,1);
            }
            func_0x00401000(uVar25,puVar12);
            func_0x00407610();
          }
          else {
            if (puVar15 != (uint *)0x0) {
              if (*puVar15 >> 8 != 0) {
                if (puVar15 == (uint *)0x0) {
                  puVar21 = (uint *)0x0;
                }
                else {
                  puVar21 = puVar15 + 1;
                }
                if ((char)*puVar21 != '\0') {
                  if (puVar15 == (uint *)0x0) {
                    puVar21 = (uint *)0x0;
                  }
                  else {
                    puVar21 = puVar15 + 1;
                  }
                  bVar24 = puVar21 == (uint *)&UNK_00c81854;
                  goto LAB_00458ba1;
                }
              }
              goto LAB_00458d33;
            }
LAB_00458d5d:
            if (*(int *)param_11 == 0) {
LAB_00458f2f:
              if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_00458f59;
              if (puVar15 == (uint *)0x0) {
                puVar21 = (uint *)0x0;
              }
              else {
                puVar21 = puVar15 + 1;
              }
              bVar24 = true;
              iVar6 = 0xc;
              pcVar5 = "screensaver";
              do {
                if (iVar6 == 0) break;
                iVar6 = iVar6 + -1;
                bVar24 = *pcVar5 == (char)*puVar21;
                pcVar5 = pcVar5 + 1;
                puVar21 = (uint *)((int)puVar21 + 1);
              } while (bVar24);
LAB_00458f9b:
              if (!bVar24) goto LAB_00459092;
              func_0x008e7cd0();
              uVar20 = param_28;
              if ((param_28 & 1) == 0) {
                uVar22 = param_28 >> 1;
                if (uVar22 * 4 < 0x100000) {
                  uVar17 = uVar22;
                  if ((uVar22 & uVar22 - 1) == 0) {
                    if (uVar22 == 0) {
                      uVar17 = 1;
                    }
                    else {
                      uVar17 = uVar22 * 2;
                    }
                  }
                }
                else {
                  uVar17 = (uVar22 & 0x7ffffc00) + 0x400;
                }
                if (uVar22 < uVar17) {
                  if (uVar17 == 0) {
                    if (param_27 != 0) {
                      func_0x0097caf0();
                      param_27 = 0;
                    }
                    goto LAB_0045904d;
                  }
                  param_27 = func_0x0097c810();
                }
                if (param_27 != 0) {
                  param_28 = (uVar20 & 0xfffffffe) + 2;
                  *(undefined4 *)(uVar22 * 4 + param_27) = *(undefined4 *)(unaff_EBP + 0xc);
                }
              }
LAB_0045904d:
              param_6 = (byte *)0x0;
              func_0x00985ff0();
              func_0x004d9aa0(*(int *)(unaff_EBP + 8) + 0x68,&param_26,1);
              func_0x00401000();
              func_0x00407610();
            }
            else {
              if (puVar15 != (uint *)0x0) {
                if (*puVar15 >> 8 != 0) {
                  if (puVar15 == (uint *)0x0) {
                    puVar21 = (uint *)0x0;
                  }
                  else {
                    puVar21 = puVar15 + 1;
                  }
                  if ((char)*puVar21 != '\0') {
                    if (puVar15 == (uint *)0x0) {
                      puVar21 = (uint *)0x0;
                    }
                    else {
                      puVar21 = puVar15 + 1;
                    }
                    bVar24 = puVar21 == (uint *)&UNK_00c81860;
                    goto LAB_00458d9f;
                  }
                }
                goto LAB_00458f2f;
              }
LAB_00458f59:
              if (*(int *)param_11 == 0) {
LAB_00459092:
                if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_004590c6;
                if (puVar15 == (uint *)0x0) {
                  iVar6 = 9;
                  bVar24 = true;
                  pcVar5 = "suppress";
                  pcVar19 = (char *)0x0;
                  do {
                    if (iVar6 == 0) break;
                    iVar6 = iVar6 + -1;
                    bVar24 = *pcVar5 == *pcVar19;
                    pcVar5 = pcVar5 + 1;
                    pcVar19 = pcVar19 + 1;
                  } while (bVar24);
                }
                else {
                  iVar6 = 9;
                  bVar24 = true;
                  pcVar5 = "suppress";
                  puVar9 = puVar15 + 1;
                  do {
                    if (iVar6 == 0) break;
                    iVar6 = iVar6 + -1;
                    bVar24 = *pcVar5 == (char)*puVar9;
                    pcVar5 = pcVar5 + 1;
                    puVar9 = (uint *)((int)puVar9 + 1);
                  } while (bVar24);
                }
LAB_004590f3:
                if (bVar24) {
                  (**(code **)(*(int *)(*(int *)(unaff_EBP + 8) + 0x48) + 0x80))();
                  goto LAB_004599fe;
                }
              }
              else {
                if (puVar15 != (uint *)0x0) {
                  if (*puVar15 >> 8 != 0) {
                    if (puVar15 == (uint *)0x0) {
                      puVar21 = (uint *)0x0;
                    }
                    else {
                      puVar21 = puVar15 + 1;
                    }
                    if ((char)*puVar21 != '\0') {
                      if (puVar15 == (uint *)0x0) {
                        puVar21 = (uint *)0x0;
                      }
                      else {
                        puVar21 = puVar15 + 1;
                      }
                      bVar24 = puVar21 == (uint *)&UNK_00c81868;
                      goto LAB_00458f9b;
                    }
                  }
                  goto LAB_00459092;
                }
LAB_004590c6:
                if ((*(int *)param_11 != 0) && ((puVar15 != (uint *)0x0 && (*puVar15 >> 8 != 0)))) {
                  if (puVar15 == (uint *)0x0) {
                    puVar21 = (uint *)0x0;
                  }
                  else {
                    puVar21 = puVar15 + 1;
                  }
                  if ((char)*puVar21 != '\0') {
                    if (puVar15 != (uint *)0x0) {
                      puVar9 = puVar15 + 1;
                    }
                    bVar24 = puVar9 == (uint *)&UNK_00c81508;
                    goto LAB_004590f3;
                  }
                }
              }
              puVar9 = (uint *)0x0;
              cVar4 = func_0x00987030();
              if (cVar4 == '\0') {
                if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) {
                  if (*(int *)pbVar23 == 0) goto LAB_004593d1;
                  if (puVar15 != (uint *)0x0) {
                    if (*puVar15 >> 8 != 0) {
                      if (puVar15 == (uint *)0x0) {
                        puVar9 = (uint *)0x0;
                      }
                      else {
                        puVar9 = puVar15 + 1;
                      }
                      if ((char)*puVar9 != '\0') {
                        if (puVar15 == (uint *)0x0) {
                          puVar9 = (uint *)0x0;
                        }
                        else {
                          puVar9 = puVar15 + 1;
                        }
                        bVar24 = puVar9 == (uint *)&UNK_00c81874;
                        goto LAB_00459339;
                      }
                    }
                    goto LAB_004593d1;
                  }
LAB_004593fb:
                  if (*(int *)param_11 == 0) {
LAB_00459880:
                    if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_004598b4;
                    if (puVar15 == (uint *)0x0) {
                      iVar6 = 0xf;
                      bVar24 = true;
                      pcVar5 = "onlinechecksum";
                      pcVar19 = (char *)0x0;
                      do {
                        if (iVar6 == 0) break;
                        iVar6 = iVar6 + -1;
                        bVar24 = *pcVar5 == *pcVar19;
                        pcVar5 = pcVar5 + 1;
                        pcVar19 = pcVar19 + 1;
                      } while (bVar24);
                    }
                    else {
                      iVar6 = 0xf;
                      bVar24 = true;
                      pcVar5 = "onlinechecksum";
                      puVar9 = puVar15 + 1;
                      do {
                        if (iVar6 == 0) break;
                        iVar6 = iVar6 + -1;
                        bVar24 = *pcVar5 == (char)*puVar9;
                        pcVar5 = pcVar5 + 1;
                        puVar9 = (uint *)((int)puVar9 + 1);
                      } while (bVar24);
                    }
LAB_004598e8:
                    if (!bVar24) goto LAB_00459904;
                    in_stack_000000a8 = func_0x0049f7e0();
                  }
                  else {
                    if (puVar15 != (uint *)0x0) {
                      if (*puVar15 >> 8 != 0) {
                        if (puVar15 == (uint *)0x0) {
                          puVar9 = (uint *)0x0;
                        }
                        else {
                          puVar9 = puVar15 + 1;
                        }
                        if ((char)*puVar9 != '\0') {
                          if (puVar15 == (uint *)0x0) {
                            puVar9 = (uint *)0x0;
                          }
                          else {
                            puVar9 = puVar15 + 1;
                          }
                          bVar24 = puVar9 == (uint *)&UNK_00c81884;
                          goto LAB_0045943f;
                        }
                      }
                      goto LAB_00459880;
                    }
LAB_004598b4:
                    if (*(int *)param_11 == 0) {
LAB_00459904:
                      if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_00459938;
                      if (puVar15 == (uint *)0x0) {
                        iVar6 = 10;
                        bVar24 = true;
                        pcVar5 = "albumlist";
                        pcVar19 = (char *)0x0;
                        do {
                          if (iVar6 == 0) break;
                          iVar6 = iVar6 + -1;
                          bVar24 = *pcVar5 == *pcVar19;
                          pcVar5 = pcVar5 + 1;
                          pcVar19 = pcVar19 + 1;
                        } while (bVar24);
                      }
                      else {
                        iVar6 = 10;
                        bVar24 = true;
                        pcVar5 = "albumlist";
                        puVar9 = puVar15 + 1;
                        do {
                          if (iVar6 == 0) break;
                          iVar6 = iVar6 + -1;
                          bVar24 = *pcVar5 == (char)*puVar9;
                          pcVar5 = pcVar5 + 1;
                          puVar9 = (uint *)((int)puVar9 + 1);
                        } while (bVar24);
                      }
LAB_0045996c:
                      if (!bVar24) goto LAB_0045998e;
                      if (*(int *)(unaff_EBP + 0x18) != 0) {
                        FUN_005c2100();
                      }
                    }
                    else {
                      if (puVar15 != (uint *)0x0) {
                        if (*puVar15 >> 8 != 0) {
                          if (puVar15 == (uint *)0x0) {
                            puVar9 = (uint *)0x0;
                          }
                          else {
                            puVar9 = puVar15 + 1;
                          }
                          if ((char)*puVar9 != '\0') {
                            if (puVar15 == (uint *)0x0) {
                              puVar9 = (uint *)0x0;
                            }
                            else {
                              puVar9 = puVar15 + 1;
                            }
                            bVar24 = puVar9 == (uint *)&UNK_00c8149c;
                            goto LAB_004598e8;
                          }
                        }
                        goto LAB_00459904;
                      }
LAB_00459938:
                      if (*(int *)param_11 == 0) {
LAB_0045998e:
                        if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc))
                        goto LAB_004599c2;
                        if (puVar15 == (uint *)0x0) {
                          iVar6 = 0xb;
                          bVar24 = true;
                          pcVar5 = "backuphash";
                          pcVar19 = (char *)0x0;
                          do {
                            if (iVar6 == 0) break;
                            iVar6 = iVar6 + -1;
                            bVar24 = *pcVar5 == *pcVar19;
                            pcVar5 = pcVar5 + 1;
                            pcVar19 = pcVar19 + 1;
                          } while (bVar24);
                        }
                        else {
                          iVar6 = 0xb;
                          bVar24 = true;
                          pcVar5 = "backuphash";
                          puVar9 = puVar15 + 1;
                          do {
                            if (iVar6 == 0) break;
                            iVar6 = iVar6 + -1;
                            bVar24 = *pcVar5 == (char)*puVar9;
                            pcVar5 = pcVar5 + 1;
                            puVar9 = (uint *)((int)puVar9 + 1);
                          } while (bVar24);
                        }
LAB_004599f2:
                        if (bVar24) {
                          param_18._0_1_ = '\x01';
                        }
                      }
                      else {
                        if (puVar15 != (uint *)0x0) {
                          if (*puVar15 >> 8 != 0) {
                            if (puVar15 == (uint *)0x0) {
                              puVar9 = (uint *)0x0;
                            }
                            else {
                              puVar9 = puVar15 + 1;
                            }
                            if ((char)*puVar9 != '\0') {
                              if (puVar15 == (uint *)0x0) {
                                puVar9 = (uint *)0x0;
                              }
                              else {
                                puVar9 = puVar15 + 1;
                              }
                              bVar24 = puVar9 == (uint *)&UNK_00c8188c;
                              goto LAB_0045996c;
                            }
                          }
                          goto LAB_0045998e;
                        }
LAB_004599c2:
                        if ((*(int *)param_11 != 0) &&
                           ((puVar15 != (uint *)0x0 && (*puVar15 >> 8 != 0)))) {
                          if (puVar15 == (uint *)0x0) {
                            puVar9 = (uint *)0x0;
                          }
                          else {
                            puVar9 = puVar15 + 1;
                          }
                          if ((char)*puVar9 != '\0') {
                            if (puVar15 == (uint *)0x0) {
                              puVar15 = (uint *)0x0;
                            }
                            else {
                              puVar15 = puVar15 + 1;
                            }
                            bVar24 = puVar15 == (uint *)&UNK_00c80c6c;
                            goto LAB_004599f2;
                          }
                        }
                      }
                    }
                  }
                }
                else {
                  if (puVar15 != (uint *)0x0) {
                    puVar9 = puVar15 + 1;
                  }
                  iVar6 = 7;
                  bVar24 = true;
                  pcVar5 = "geotag";
                  do {
                    if (iVar6 == 0) break;
                    iVar6 = iVar6 + -1;
                    bVar24 = *pcVar5 == (char)*puVar9;
                    pcVar5 = pcVar5 + 1;
                    puVar9 = (uint *)((int)puVar9 + 1);
                  } while (bVar24);
LAB_00459339:
                  if (bVar24) {
                    in_stack_00000118 = 0;
                    in_stack_00000140 = 0;
                    iVar6 = func_0x00c07eef();
                    if (iVar6 == 2) {
                      iVar6 = *(int *)(unaff_EBP + 8);
                      uVar10 = *(undefined4 *)(unaff_EBP + 0xc);
                      (**(code **)(*(int *)(iVar6 + 0x48) + 0x68))
                                (uVar10,in_stack_00000118,in_stack_00000140,0);
                      (**(code **)(*(int *)(iVar6 + 0x48) + 0x70))(uVar10,1);
                    }
                    goto LAB_004599fe;
                  }
LAB_004593d1:
                  if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_004593fb;
                  if (puVar15 == (uint *)0x0) {
                    puVar9 = (uint *)0x0;
                  }
                  else {
                    puVar9 = puVar15 + 1;
                  }
                  bVar24 = true;
                  iVar6 = 6;
                  pcVar5 = "faces";
                  do {
                    if (iVar6 == 0) break;
                    iVar6 = iVar6 + -1;
                    bVar24 = *pcVar5 == (char)*puVar9;
                    pcVar5 = pcVar5 + 1;
                    puVar9 = (uint *)((int)puVar9 + 1);
                  } while (bVar24);
LAB_0045943f:
                  if (!bVar24) goto LAB_00459880;
                  iVar6 = *(int *)(unaff_EBP + 8);
                  pbVar23 = (byte *)(iVar6 + 0x1d48);
                  param_19 = iVar6 + 0x1d70;
                  param_11 = pbVar23;
                  param_20 = pbVar23;
                  iVar7 = GetCurrentThreadId();
                  if ((*(int *)(iVar6 + 0x1d68) == 0) || (*(int *)(iVar6 + 0x1d68) != iVar7)) {
                    if (*(char *)(iVar6 + 0x1d54) == '\0') {
                      (**(code **)(*(int *)pbVar23 + 0x18))();
                    }
                    else {
                      EnterCriticalSection();
                    }
                    *(undefined4 *)(iVar6 + 0x1d6c) = 0;
                    *(int *)(iVar6 + 0x1d68) = iVar7;
                  }
                  else {
                    *(int *)(iVar6 + 0x1d6c) = *(int *)(iVar6 + 0x1d6c) + 1;
                  }
                  if ((*(int *)(iVar6 + 0x1da0) != 0) &&
                     (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 != 0xffffffff)) {
                    iVar6 = *(int *)(iVar6 + 0x1da0);
                    if (uVar20 < *(uint *)(iVar6 + 0x4c) >> 1) {
                      if (*(int *)param_12 == 0) {
                        puVar9 = (uint *)0x0;
                      }
                      else {
                        puVar9 = (uint *)(*(int *)param_12 + 4);
                      }
                      puVar15 = *(uint **)(*(int *)(iVar6 + 0x48) + uVar20 * 4);
                      if (puVar15 == (uint *)0x0) {
LAB_0045982c:
                        if (puVar9 == (uint *)0x0) goto LAB_00459872;
                        if ((char)*puVar9 == '\0') {
                          func_0x0041edb0();
                          goto LAB_004599fe;
                        }
                      }
                      else {
                        if ((puVar15 == &uRamfffffffc) || (puVar9 == (uint *)0x0)) {
                          if ((puVar15 != (uint *)0x0) && (*puVar15 >> 8 != 0)) {
                            if (puVar15 == (uint *)0x0) {
                              puVar21 = (uint *)0x0;
                            }
                            else {
                              puVar21 = puVar15 + 1;
                            }
                            if ((char)*puVar21 != '\0') {
                              if (puVar15 == (uint *)0x0) {
                                puVar15 = (uint *)0x0;
                              }
                              else {
                                puVar15 = puVar15 + 1;
                              }
                              bVar24 = puVar15 == puVar9;
                              goto LAB_00459850;
                            }
                          }
                          goto LAB_0045982c;
                        }
                        if (puVar15 == (uint *)0x0) {
                          puVar15 = (uint *)0x0;
                        }
                        else {
                          puVar15 = puVar15 + 1;
                        }
                        do {
                          bVar2 = (byte)*puVar9;
                          bVar24 = bVar2 < (byte)*puVar15;
                          if (bVar2 != (byte)*puVar15) {
LAB_00459808:
                            bVar24 = 1 - bVar24 == (uint)(bVar24 != 0);
                            goto LAB_00459850;
                          }
                          if (bVar2 == 0) break;
                          bVar2 = *(byte *)((int)puVar9 + 1);
                          bVar24 = bVar2 < *(byte *)((int)puVar15 + 1);
                          if (bVar2 != *(byte *)((int)puVar15 + 1)) goto LAB_00459808;
                          puVar9 = (uint *)((int)puVar9 + 2);
                          puVar15 = (uint *)((int)puVar15 + 2);
                        } while (bVar2 != 0);
                        bVar24 = true;
LAB_00459850:
                        if (bVar24) goto LAB_00459872;
                      }
                      FUN_005c2100();
                    }
                    else {
                      pbVar23 = (byte *)(uVar20 + 1);
                      param_10 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
                      if ((byte *)0x1fffffff < pbVar23) goto LAB_004594d9;
                      if (pbVar23 != param_10) {
                        if ((*(uint *)(iVar6 + 0x4c) & 1) == 0) {
                          if ((uint)((int)pbVar23 * 4) < 0x100000) {
                            pbVar13 = (byte *)0x1;
                            if (pbVar23 != (byte *)0x0) {
                              do {
                                pbVar13 = (byte *)((int)pbVar13 * 2);
                              } while (pbVar13 <= pbVar23);
                            }
                          }
                          else {
                            pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
                          }
                          if ((uint)((int)param_10 * 4) < 0x100000) {
                            pbVar14 = param_10;
                            if ((byte *)0x1 < param_10) {
                              param_14 = (float)(int)param_10;
                              pbVar14 = (byte *)(1 << ((char)((uint)param_14 >> 0x17) + 0x81U & 0x1f
                                                      ));
                              param_15 = param_10;
                              if (pbVar14 < param_10) {
                                pbVar14 = (byte *)((int)pbVar14 * 2);
                              }
                            }
                          }
                          else {
                            pbVar14 = (byte *)(((uint)param_10 & 0x7ffffc00) + 0x400);
                          }
                          pbVar23 = *(byte **)(iVar6 + 0x48);
                          if (pbVar14 == pbVar13) {
LAB_00459741:
                            uVar20 = *(uint *)(iVar6 + 0x4c) & 1 |
                                     (*(int *)(unaff_EBP + 0xc) + 1) * 2;
LAB_00459753:
                            *(uint *)(iVar6 + 0x4c) = uVar20;
                            goto LAB_00459756;
                          }
                          param_8 = (byte *)0x0;
                          if (pbVar13 == (byte *)0x0) {
LAB_00459720:
                            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
                              func_0x004010c0();
                            }
                            *(byte **)(iVar6 + 0x48) = param_8;
                            pbVar23 = param_8;
                            if (param_8 != (byte *)0x0) goto LAB_00459741;
                          }
                          else {
                            puVar12 = (undefined4 *)func_0x0097c5d0();
                            if (puVar12 != (undefined4 *)0x0) {
                              pbVar23 = (byte *)(puVar12 + 1);
                              *puVar12 = pbVar13;
                              func_0x004010e0();
                              param_8 = pbVar23;
                              if (pbVar23 != (byte *)0x0) {
                                pbVar23 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
                                param_6 = pbVar13;
                                if (pbVar23 <= pbVar13) {
                                  param_6 = pbVar23;
                                }
                                pbVar23 = (byte *)0x0;
                                if (param_6 != (byte *)0x0) {
                                  do {
                                    FUN_005c2100();
                                    pbVar23 = pbVar23 + 1;
                                  } while (pbVar23 < param_6);
                                }
                                goto LAB_00459720;
                              }
                            }
                          }
                        }
                        else {
                          param_7 = (byte *)0x0;
                          if (pbVar23 == (byte *)0x0) {
LAB_004595b0:
                            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
                              func_0x004010c0();
                            }
                            *(byte **)(iVar6 + 0x48) = param_7;
                            if (param_7 != (byte *)0x0) {
                              uVar20 = *(uint *)(iVar6 + 0x4c) & 1 |
                                       (*(int *)(unaff_EBP + 0xc) + 1) * 2;
                              pbVar23 = param_7;
                              goto LAB_00459753;
                            }
                          }
                          else {
                            puVar12 = (undefined4 *)func_0x0097c5d0();
                            if (puVar12 != (undefined4 *)0x0) {
                              pbVar13 = (byte *)(puVar12 + 1);
                              *puVar12 = pbVar23;
                              func_0x004010e0();
                              param_7 = pbVar13;
                              if (pbVar13 != (byte *)0x0) {
                                pbVar13 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
                                param_6 = pbVar23;
                                if (pbVar13 <= pbVar23) {
                                  param_6 = pbVar13;
                                }
                                pbVar23 = (byte *)0x0;
                                if (param_6 != (byte *)0x0) {
                                  do {
                                    FUN_005c2100();
                                    pbVar23 = pbVar23 + 1;
                                  } while (pbVar23 < param_6);
                                }
                                goto LAB_004595b0;
                              }
                            }
                          }
                        }
LAB_004594d9:
                        if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
                          func_0x004010c0();
                        }
                        *(undefined4 *)(iVar6 + 0x48) = 0;
                        *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1;
                        func_0x0041edb0();
                        goto LAB_004599fe;
                      }
                      pbVar23 = *(byte **)(iVar6 + 0x48);
LAB_00459756:
                      if (pbVar23 == (byte *)0x0) goto LAB_00459872;
                      pbVar23 = param_10;
                      if (param_10 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1)) {
                        do {
                          FUN_005c2100();
                          pbVar23 = pbVar23 + 1;
                        } while (pbVar23 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1));
                      }
                      FUN_005c2100();
                    }
                    func_0x006a2a60();
                  }
LAB_00459872:
                  func_0x0041edb0();
                }
              }
              else {
                param_8 = (byte *)0x0;
                if (puVar15 == (uint *)0x0) {
                  puVar15 = (uint *)0x0;
                }
                else {
                  puVar15 = puVar15 + 1;
                }
                puVar15 = puVar15 + 2;
                param_11 = (byte *)0x0;
                if (puVar15 != (uint *)0x0) {
                  do {
                    uVar20 = *puVar15;
                    puVar15 = (uint *)((int)puVar15 + 1);
                  } while ((char)uVar20 != '\0');
                  func_0x00985ff0();
                }
                param_7 = param_11;
                if ((param_11 != (byte *)0x0) && (*param_11 < 0x80)) {
                  InterlockedIncrement();
                }
                param_6 = *(byte **)param_12;
                if ((param_6 != (byte *)0x0) && (*param_6 < 0x80)) {
                  InterlockedIncrement();
                }
                func_0x00432970();
                func_0x00985af0(&param_6);
                iVar6 = *(int *)(unaff_EBP + 8);
                param_7 = (byte *)(iVar6 + 0xf20);
                uVar25 = CONCAT44(&param_5,*(undefined4 *)(unaff_EBP + 0xc));
                pbVar23 = param_7;
                func_0x006a46c0();
                pcVar5 = "";
                if (param_2 == (uint *)0x0) {
code_r0x00459250:
                  if (UNK_00c81524 != '\0') goto LAB_00459263;
                }
                else {
                  puVar9 = param_2 + 1;
                  if (puVar9 == (uint *)0x0) {
                    if (((*param_2 & 0xffffff00) == 0) || (DAT_00000000 == '\0'))
                    goto code_r0x00459250;
                    bVar24 = false;
                  }
                  else {
                    do {
                      bVar2 = *pcVar5;
                      bVar24 = bVar2 < (byte)*puVar9;
                      if (bVar2 != (byte)*puVar9) {
LAB_00459232:
                        bVar24 = 1 - bVar24 == (uint)(bVar24 != 0);
                        goto LAB_0045925c;
                      }
                      if (bVar2 == 0) break;
                      bVar2 = pcVar5[1];
                      bVar24 = bVar2 < *(byte *)((int)puVar9 + 1);
                      if (bVar2 != *(byte *)((int)puVar9 + 1)) goto LAB_00459232;
                      pcVar5 = pcVar5 + 2;
                      puVar9 = (uint *)((int)puVar9 + 2);
                    } while (bVar2 != 0);
                    bVar24 = true;
                  }
LAB_0045925c:
                  if (!bVar24) {
LAB_00459263:
                    if (((param_2 == (uint *)0x0) || ((*param_2 & 0xffffff00) == 0)) ||
                       ((char)param_2[1] == '\0')) {
                      func_0x00474300(iVar6,*(undefined4 *)(unaff_EBP + 0xc),1,pbVar23,uVar25);
                    }
                    if (&stack0x00000000 == (undefined1 *)0xffffffe8) {
                      puVar12 = (undefined4 *)0x0;
                    }
                    else {
                      puVar12 = &param_7;
                    }
                    func_0x006a63f0(param_4,puVar12,*(undefined4 *)(unaff_EBP + 0xc),"");
                  }
                }
                func_0x00401000();
                func_0x00401000();
                func_0x00401000();
                func_0x00401000();
              }
            }
          }
        }
      }
    }
    else {
      if (puVar15 == &uRamfffffffc) {
        if ((uRamfffffffc >> 8 != 0) && (DAT_00000000 != '\0')) {
          bVar24 = false;
          goto LAB_004588a2;
        }
      }
      else {
        if (puVar15 == (uint *)0x0) {
          puVar21 = (uint *)0x0;
        }
        else {
          puVar21 = puVar15 + 1;
        }
        bVar24 = true;
        iVar6 = 9;
        pcVar5 = "keywords";
        do {
          if (iVar6 == 0) break;
          iVar6 = iVar6 + -1;
          bVar24 = *pcVar5 == (char)*puVar21;
          pcVar5 = pcVar5 + 1;
          puVar21 = (uint *)((int)puVar21 + 1);
        } while (bVar24);
LAB_004588a2:
        if (bVar24) {
          in_stack_000000b0 = 0;
          in_stack_000000b4 = 0;
          func_0x009881d0(&stack0x000000b0);
          uVar22 = 0;
          uVar20 = in_stack_000000a8 >> 1;
          if (uVar20 != 0) {
            iVar6 = *(int *)(unaff_EBP + 8);
            do {
              (**(code **)(*(int *)(iVar6 + 0x48) + 0x5c))();
              uVar22 = uVar22 + 1;
            } while (uVar22 < uVar20);
          }
          func_0x00401210();
          goto LAB_004599fe;
        }
      }
      if ((puVar15 == (uint *)0x0) || (puVar15 == &uRamfffffffc)) goto LAB_00458954;
      if (puVar15 == (uint *)0x0) {
        puVar21 = (uint *)0x0;
      }
      else {
        puVar21 = puVar15 + 1;
      }
      bVar24 = true;
      iVar6 = 8;
      pcVar5 = "caption";
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar24 = *pcVar5 == (char)*puVar21;
        pcVar5 = pcVar5 + 1;
        puVar21 = (uint *)((int)puVar21 + 1);
      } while (bVar24);
LAB_0045898a:
      if (!bVar24) goto LAB_004589af;
      (**(code **)(*(int *)(*(int *)(unaff_EBP + 8) + 0x48) + 0x50))
                (*(undefined4 *)(unaff_EBP + 0xc));
    }
  }
LAB_004599fe:
  param_16 = param_16 + 2;
  if (param_16 < (byte *)((*(uint *)(param_9 + 4) >> 1) - 1)) goto LAB_00456900;
  if (*(char *)(unaff_EBP + 0x14) == '\0') {
    if ((*(byte *)(unaff_EBP + 0x10) & 2) != 0) {
      func_0x0045bb00(*(undefined4 *)(unaff_EBP + 8),*(undefined4 *)(unaff_EBP + 0xc),
                      in_stack_000000b8);
    }
    goto LAB_0045a8f6;
  }
  if ((char)param_18 == '\0') goto LAB_0045a8f6;
  if ((*(byte *)(unaff_EBP + 0x10) & 2) == 0) goto LAB_0045a868;
  if (param_18._1_1_ != '\0') {
    if (cStack000000a4 == '\0') goto LAB_00459e21;
    goto LAB_0045a0af;
  }
  iVar6 = *(int *)(unaff_EBP + 8);
  pbVar23 = (byte *)(iVar6 + 0x16b8);
  param_19 = iVar6 + 0x16e0;
  param_7 = (byte *)0x0;
  param_8 = pbVar23;
  param_20 = pbVar23;
  iVar7 = GetCurrentThreadId();
  if ((*(int *)(iVar6 + 0x16d8) == 0) || (*(int *)(iVar6 + 0x16d8) != iVar7)) {
    if (*(char *)(iVar6 + 0x16c4) == '\0') {
      (**(code **)(*(int *)pbVar23 + 0x18))();
    }
    else {
      EnterCriticalSection();
    }
    *(undefined4 *)(iVar6 + 0x16dc) = 0;
    *(int *)(iVar6 + 0x16d8) = iVar7;
  }
  else {
    *(int *)(iVar6 + 0x16dc) = *(int *)(iVar6 + 0x16dc) + 1;
  }
  if ((*(int *)(iVar6 + 0x1710) == 0) || (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 == 0xffffffff)
     ) goto LAB_00459dff;
  iVar6 = *(int *)(iVar6 + 0x1710);
  if (uVar20 < *(uint *)(iVar6 + 0x4c) >> 1) {
    puVar9 = *(uint **)(*(int *)(iVar6 + 0x48) + uVar20 * 4);
    if ((puVar9 == (uint *)0x0) || (*puVar9 >> 8 == 0)) goto LAB_00459dff;
    if (puVar9 == (uint *)0x0) {
      puVar15 = (uint *)0x0;
    }
    else {
      puVar15 = puVar9 + 1;
    }
    if ((char)*puVar15 == '\0') goto LAB_00459dff;
    if (puVar9 == (uint *)0x0) {
      puVar9 = (uint *)0x0;
    }
    else {
      puVar9 = puVar9 + 1;
    }
    if (puVar9 == (uint *)0x0) goto LAB_00459dff;
    FUN_005c2100();
    goto LAB_00459dfa;
  }
  pbVar23 = (byte *)(uVar20 + 1);
  param_6 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
  if ((byte *)0x1fffffff < pbVar23) goto LAB_00459ade;
  if (pbVar23 == param_6) {
    pbVar13 = *(byte **)(iVar6 + 0x48);
    goto LAB_00459d39;
  }
  if ((*(uint *)(iVar6 + 0x4c) & 1) == 0) {
    if ((uint)((int)pbVar23 * 4) < 0x100000) {
      pbVar14 = (byte *)0x1;
      if (pbVar23 != (byte *)0x0) {
        do {
          pbVar14 = (byte *)((int)pbVar14 * 2);
        } while (pbVar14 <= pbVar23);
      }
    }
    else {
      pbVar14 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
    }
    if ((uint)((int)param_6 * 4) < 0x100000) {
      pbVar23 = param_6;
      if ((byte *)0x1 < param_6) {
        param_14 = (float)(int)param_6;
        pbVar23 = (byte *)(1 << ((char)((uint)param_14 >> 0x17) + 0x81U & 0x1f));
        if (pbVar23 < param_6) {
          pbVar23 = (byte *)((int)pbVar23 * 2);
        }
      }
    }
    else {
      pbVar23 = (byte *)(((uint)param_6 & 0x7ffffc00) + 0x400);
    }
    pbVar13 = *(byte **)(iVar6 + 0x48);
    if (pbVar23 == pbVar14) goto LAB_00459d25;
    param_16 = (byte *)0x0;
    if (pbVar14 == (byte *)0x0) {
LAB_00459d02:
      if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
        func_0x004010c0();
      }
      *(byte **)(iVar6 + 0x48) = param_16;
      pbVar13 = param_16;
      goto joined_r0x00459d1d;
    }
    puVar12 = (undefined4 *)func_0x0097c5d0();
    if (puVar12 != (undefined4 *)0x0) {
      pbVar23 = (byte *)(puVar12 + 1);
      *puVar12 = pbVar14;
      func_0x004010e0();
      param_16 = pbVar23;
      if (pbVar23 != (byte *)0x0) {
        pbVar23 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
        param_9 = pbVar14;
        if (pbVar23 <= pbVar14) {
          param_9 = pbVar23;
        }
        pbVar23 = (byte *)0x0;
        if (param_9 != (byte *)0x0) {
          do {
            FUN_005c2100();
            pbVar23 = pbVar23 + 1;
          } while (pbVar23 < param_9);
        }
        goto LAB_00459d02;
      }
    }
    goto LAB_00459ade;
  }
  pbVar13 = (byte *)0x0;
  if (pbVar23 == (byte *)0x0) goto LAB_00459bb4;
  puVar12 = (undefined4 *)func_0x0097c5d0();
  if (puVar12 == (undefined4 *)0x0) goto LAB_00459ade;
  pbVar13 = (byte *)(puVar12 + 1);
  *puVar12 = pbVar23;
  func_0x004010e0();
  param_10 = pbVar13;
  if (pbVar13 == (byte *)0x0) goto LAB_00459ade;
  pbVar14 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
  param_9 = pbVar23;
  if (pbVar14 <= pbVar23) {
    param_9 = pbVar14;
  }
  pbVar23 = (byte *)0x0;
  if (param_9 != (byte *)0x0) {
    do {
      FUN_005c2100();
      pbVar23 = pbVar23 + 1;
      pbVar13 = param_10;
    } while (pbVar23 < param_9);
  }
LAB_00459bb4:
  if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
    func_0x004010c0();
  }
  *(byte **)(iVar6 + 0x48) = pbVar13;
joined_r0x00459d1d:
  if (pbVar13 == (byte *)0x0) {
LAB_00459ade:
    if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
      func_0x004010c0();
    }
    *(undefined4 *)(iVar6 + 0x48) = 0;
    *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1;
  }
  else {
LAB_00459d25:
    pbVar23 = (byte *)(*(int *)(unaff_EBP + 0xc) + 1);
    *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1 | (int)pbVar23 * 2;
LAB_00459d39:
    if (pbVar13 != (byte *)0x0) {
      pbVar13 = param_6;
      if (param_6 < pbVar23) {
        while (param_9 = pbVar13, param_9 < pbVar23) {
          FUN_005c2100();
          pbVar13 = param_9 + 1;
        }
      }
      FUN_005c2100();
LAB_00459dfa:
      func_0x006a2a60();
    }
  }
LAB_00459dff:
  func_0x0041edb0();
  func_0x00401000();
LAB_00459e21:
  iVar6 = *(int *)(unaff_EBP + 8);
  param_19 = iVar6 + 0x14f8;
  param_20 = (byte *)(iVar6 + 0x14d0);
  iVar7 = GetCurrentThreadId();
  if ((*(int *)(iVar6 + 0x14f0) == 0) || (*(int *)(iVar6 + 0x14f0) != iVar7)) {
    if (*(char *)(iVar6 + 0x14dc) == '\0') {
      (**(code **)(*(int *)(iVar6 + 0x14d0) + 0x18))();
    }
    else {
      EnterCriticalSection();
    }
    *(undefined4 *)(iVar6 + 0x14f4) = 0;
    *(int *)(iVar6 + 0x14f0) = iVar7;
  }
  else {
    *(int *)(iVar6 + 0x14f4) = *(int *)(iVar6 + 0x14f4) + 1;
  }
  if ((*(int *)(iVar6 + 0x1528) != 0) && (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 != 0xffffffff)
     ) {
    iVar7 = *(int *)(iVar6 + 0x1528);
    if (uVar20 < *(uint *)(iVar7 + 0x4c) >> 1) {
      iVar6 = *(int *)(iVar7 + 0x48);
      puVar12 = (undefined4 *)(iVar6 + uVar20 * 8);
      if (*(int *)(iVar6 + uVar20 * 8) != 0 || *(int *)(iVar6 + 4 + uVar20 * 8) != 0) {
        *puVar12 = 0;
        puVar12[1] = 0;
LAB_0045a09e:
        func_0x006a2a60();
      }
    }
    else {
      pbVar23 = (byte *)(uVar20 + 1);
      param_7 = (byte *)(*(uint *)(iVar7 + 0x4c) >> 1);
      if (pbVar23 < (byte *)0x10000000) {
        if (pbVar23 == param_7) {
          fVar11 = *(float *)(iVar7 + 0x48);
        }
        else if ((*(uint *)(iVar7 + 0x4c) & 1) == 0) {
          if ((uint)((int)pbVar23 * 8) < 0x100000) {
            pbVar13 = (byte *)0x1;
            if (pbVar23 != (byte *)0x0) {
              do {
                pbVar13 = (byte *)((int)pbVar13 * 2);
              } while (pbVar13 <= pbVar23);
            }
          }
          else {
            pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
          }
          if ((uint)((int)param_7 * 8) < 0x100000) {
            pbVar14 = param_7;
            if ((byte *)0x1 < param_7) {
              param_14 = (float)(int)param_7;
              pbVar14 = (byte *)(1 << ((char)((uint)param_14 >> 0x17) + 0x81U & 0x1f));
              if (pbVar14 < param_7) {
                pbVar14 = (byte *)((int)pbVar14 * 2);
              }
            }
          }
          else {
            pbVar14 = (byte *)(((uint)param_7 & 0x7ffffc00) + 0x400);
          }
          fVar11 = *(float *)(iVar7 + 0x48);
          if (pbVar14 != pbVar13) {
            if (pbVar13 == (byte *)0x0) {
              if (fVar11 != 0.0) {
                func_0x0097caf0();
                *(undefined4 *)(iVar7 + 0x48) = 0;
              }
            }
            else {
              uVar10 = func_0x0097c810();
              *(undefined4 *)(iVar7 + 0x48) = uVar10;
            }
            fVar11 = *(float *)(iVar7 + 0x48);
            if (fVar11 == 0.0) {
              *(undefined4 *)(iVar7 + 0x48) = 0;
              *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
              goto LAB_0045a0a6;
            }
          }
          *(uint *)(iVar7 + 0x4c) = (int)pbVar23 * 2 | *(uint *)(iVar7 + 0x4c) & 1;
        }
        else {
          if (pbVar23 == (byte *)0x0) {
            if (*(int *)(iVar7 + 0x48) != 0) {
              func_0x0097caf0();
              *(undefined4 *)(iVar7 + 0x48) = 0;
            }
          }
          else {
            uVar10 = func_0x0097c810();
            *(undefined4 *)(iVar7 + 0x48) = uVar10;
          }
          fVar11 = *(float *)(iVar7 + 0x48);
          param_14 = fVar11;
          if (fVar11 == 0.0) {
            *(undefined4 *)(iVar7 + 0x48) = 0;
            *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
            goto LAB_0045a0a6;
          }
          *(uint *)(iVar7 + 0x4c) = (int)pbVar23 * 2 | *(uint *)(iVar7 + 0x4c) & 1;
        }
        pbVar13 = param_7;
        if (fVar11 != 0.0) {
          for (; pbVar13 < pbVar23; pbVar13 = pbVar13 + 1) {
            iVar18 = *(int *)(iVar7 + 0x48);
            *(undefined4 *)(iVar18 + (int)pbVar13 * 8) = *(undefined4 *)(iVar6 + 0x1530);
            *(undefined4 *)(iVar18 + 4 + (int)pbVar13 * 8) = *(undefined4 *)(iVar6 + 0x1534);
          }
          iVar6 = *(int *)(*(int *)(iVar6 + 0x1528) + 0x48);
          iVar7 = *(int *)(unaff_EBP + 0xc);
          *(undefined4 *)(iVar6 + iVar7 * 8) = 0;
          *(undefined4 *)(iVar6 + 4 + iVar7 * 8) = 0;
          goto LAB_0045a09e;
        }
      }
      else {
        if (*(int *)(iVar7 + 0x48) != 0) {
          func_0x0097caf0();
        }
        *(undefined4 *)(iVar7 + 0x48) = 0;
        *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
      }
    }
  }
LAB_0045a0a6:
  func_0x0041edb0();
LAB_0045a0af:
  if (param_18._3_1_ == '\0') {
    iVar6 = *(int *)(unaff_EBP + 8);
    pbVar23 = (byte *)(iVar6 + 0x1470);
    param_19 = iVar6 + 0x1498;
    param_8 = (byte *)0x0;
    param_6 = pbVar23;
    param_20 = pbVar23;
    iVar7 = GetCurrentThreadId();
    if ((*(int *)(iVar6 + 0x1490) == 0) || (*(int *)(iVar6 + 0x1490) != iVar7)) {
      if (*(char *)(iVar6 + 0x147c) == '\0') {
        (**(code **)(*(int *)pbVar23 + 0x18))();
      }
      else {
        EnterCriticalSection();
      }
      *(undefined4 *)(iVar6 + 0x1494) = 0;
      *(int *)(iVar6 + 0x1490) = iVar7;
    }
    else {
      *(int *)(iVar6 + 0x1494) = *(int *)(iVar6 + 0x1494) + 1;
    }
    if ((*(int *)(iVar6 + 0x14c8) != 0) &&
       (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 != 0xffffffff)) {
      iVar6 = *(int *)(iVar6 + 0x14c8);
      if (uVar20 < *(uint *)(iVar6 + 0x4c) >> 1) {
        puVar9 = *(uint **)(*(int *)(iVar6 + 0x48) + uVar20 * 4);
        if ((puVar9 != (uint *)0x0) && (*puVar9 >> 8 != 0)) {
          if (puVar9 == (uint *)0x0) {
            puVar15 = (uint *)0x0;
          }
          else {
            puVar15 = puVar9 + 1;
          }
          if ((char)*puVar15 != '\0') {
            if (puVar9 == (uint *)0x0) {
              puVar9 = (uint *)0x0;
            }
            else {
              puVar9 = puVar9 + 1;
            }
            if (puVar9 != (uint *)0x0) {
              FUN_005c2100();
              goto LAB_0045a46a;
            }
          }
        }
      }
      else {
        pbVar23 = (byte *)(uVar20 + 1);
        param_10 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
        if ((byte *)0x1fffffff < pbVar23) goto LAB_0045a151;
        if (pbVar23 == param_10) {
          pbVar23 = *(byte **)(iVar6 + 0x48);
LAB_0045a3c6:
          if (pbVar23 != (byte *)0x0) {
            pbVar23 = param_10;
            if (param_10 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1)) {
              do {
                FUN_005c2100();
                pbVar23 = pbVar23 + 1;
              } while (pbVar23 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1));
            }
            FUN_005c2100();
LAB_0045a46a:
            func_0x006a2a60();
          }
        }
        else {
          if ((*(uint *)(iVar6 + 0x4c) & 1) == 0) {
            if ((uint)((int)pbVar23 * 4) < 0x100000) {
              pbVar13 = (byte *)0x1;
              if (pbVar23 != (byte *)0x0) {
                do {
                  pbVar13 = (byte *)((int)pbVar13 * 2);
                } while (pbVar13 <= pbVar23);
              }
            }
            else {
              pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
            }
            if ((uint)((int)param_10 * 4) < 0x100000) {
              pbVar14 = param_10;
              if ((byte *)0x1 < param_10) {
                param_14 = (float)(int)param_10;
                pbVar14 = (byte *)(1 << ((char)((uint)param_14 >> 0x17) + 0x81U & 0x1f));
                if (pbVar14 < param_10) {
                  pbVar14 = (byte *)((int)pbVar14 * 2);
                }
              }
            }
            else {
              pbVar14 = (byte *)(((uint)param_10 & 0x7ffffc00) + 0x400);
            }
            pbVar23 = *(byte **)(iVar6 + 0x48);
            if (pbVar14 == pbVar13) {
LAB_0045a3b1:
              uVar20 = *(uint *)(iVar6 + 0x4c) & 1 | (*(int *)(unaff_EBP + 0xc) + 1) * 2;
LAB_0045a3c3:
              *(uint *)(iVar6 + 0x4c) = uVar20;
              goto LAB_0045a3c6;
            }
            param_16 = (byte *)0x0;
            if (pbVar13 == (byte *)0x0) {
LAB_0045a390:
              if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
                func_0x004010c0();
              }
              *(byte **)(iVar6 + 0x48) = param_16;
              pbVar23 = param_16;
              if (param_16 != (byte *)0x0) goto LAB_0045a3b1;
            }
            else {
              puVar12 = (undefined4 *)func_0x0097c5d0();
              if (puVar12 != (undefined4 *)0x0) {
                pbVar23 = (byte *)(puVar12 + 1);
                *puVar12 = pbVar13;
                func_0x004010e0();
                param_16 = pbVar23;
                if (pbVar23 != (byte *)0x0) {
                  pbVar23 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
                  param_9 = pbVar13;
                  if (pbVar23 <= pbVar13) {
                    param_9 = pbVar23;
                  }
                  pbVar23 = (byte *)0x0;
                  if (param_9 != (byte *)0x0) {
                    do {
                      FUN_005c2100();
                      pbVar23 = pbVar23 + 1;
                    } while (pbVar23 < param_9);
                  }
                  goto LAB_0045a390;
                }
              }
            }
          }
          else {
            param_7 = (byte *)0x0;
            if (pbVar23 == (byte *)0x0) {
LAB_0045a220:
              if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
                func_0x004010c0();
              }
              *(byte **)(iVar6 + 0x48) = param_7;
              if (param_7 != (byte *)0x0) {
                uVar20 = *(uint *)(iVar6 + 0x4c) & 1 | (*(int *)(unaff_EBP + 0xc) + 1) * 2;
                pbVar23 = param_7;
                goto LAB_0045a3c3;
              }
            }
            else {
              puVar12 = (undefined4 *)func_0x0097c5d0();
              if (puVar12 != (undefined4 *)0x0) {
                pbVar13 = (byte *)(puVar12 + 1);
                *puVar12 = pbVar23;
                func_0x004010e0();
                param_7 = pbVar13;
                if (pbVar13 != (byte *)0x0) {
                  pbVar13 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
                  param_9 = pbVar23;
                  if (pbVar13 <= pbVar23) {
                    param_9 = pbVar13;
                  }
                  pbVar23 = (byte *)0x0;
                  if (param_9 != (byte *)0x0) {
                    do {
                      FUN_005c2100();
                      pbVar23 = pbVar23 + 1;
                    } while (pbVar23 < param_9);
                  }
                  goto LAB_0045a220;
                }
              }
            }
          }
LAB_0045a151:
          if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
            func_0x004010c0();
          }
          *(undefined4 *)(iVar6 + 0x48) = 0;
          *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1;
        }
      }
    }
    func_0x0041edb0();
    func_0x00401000();
  }
  if (param_18._2_1_ != '\0') goto LAB_0045a868;
  iVar6 = *(int *)(unaff_EBP + 8);
  pbVar23 = (byte *)(iVar6 + 0x1718);
  param_19 = iVar6 + 0x1740;
  param_8 = (byte *)0x0;
  param_6 = pbVar23;
  param_20 = pbVar23;
  iVar7 = GetCurrentThreadId();
  if ((*(int *)(iVar6 + 0x1738) == 0) || (*(int *)(iVar6 + 0x1738) != iVar7)) {
    if (*(char *)(iVar6 + 0x1724) == '\0') {
      (**(code **)(*(int *)pbVar23 + 0x18))();
    }
    else {
      EnterCriticalSection();
    }
    *(undefined4 *)(iVar6 + 0x173c) = 0;
    *(int *)(iVar6 + 0x1738) = iVar7;
  }
  else {
    *(int *)(iVar6 + 0x173c) = *(int *)(iVar6 + 0x173c) + 1;
  }
  if ((*(int *)(iVar6 + 6000) != 0) && (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 != 0xffffffff))
  {
    iVar6 = *(int *)(iVar6 + 6000);
    if (uVar20 < *(uint *)(iVar6 + 0x4c) >> 1) {
      puVar9 = *(uint **)(*(int *)(iVar6 + 0x48) + uVar20 * 4);
      if ((puVar9 != (uint *)0x0) && (*puVar9 >> 8 != 0)) {
        if (puVar9 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar9 + 1;
        }
        if ((char)*puVar15 != '\0') {
          if (puVar9 == (uint *)0x0) {
            puVar9 = (uint *)0x0;
          }
          else {
            puVar9 = puVar9 + 1;
          }
          if (puVar9 != (uint *)0x0) {
            FUN_005c2100();
            goto LAB_0045a84d;
          }
        }
      }
    }
    else {
      pbVar23 = (byte *)(uVar20 + 1);
      param_10 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
      if ((byte *)0x1fffffff < pbVar23) goto LAB_0045a527;
      if (pbVar23 == param_10) {
        pbVar23 = *(byte **)(iVar6 + 0x48);
LAB_0045a7a7:
        if (pbVar23 != (byte *)0x0) {
          pbVar23 = param_10;
          if (param_10 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1)) {
            do {
              FUN_005c2100();
              pbVar23 = pbVar23 + 1;
            } while (pbVar23 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1));
          }
          FUN_005c2100();
LAB_0045a84d:
          func_0x006a2a60();
        }
      }
      else {
        if ((*(uint *)(iVar6 + 0x4c) & 1) == 0) {
          if ((uint)((int)pbVar23 * 4) < 0x100000) {
            pbVar13 = (byte *)0x1;
            if (pbVar23 != (byte *)0x0) {
              do {
                pbVar13 = (byte *)((int)pbVar13 * 2);
              } while (pbVar13 <= pbVar23);
            }
          }
          else {
            pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
          }
          if ((uint)((int)param_10 * 4) < 0x100000) {
            pbVar14 = param_10;
            if ((byte *)0x1 < param_10) {
              param_14 = (float)(int)param_10;
              pbVar14 = (byte *)(1 << ((char)((uint)param_14 >> 0x17) + 0x81U & 0x1f));
              if (pbVar14 < param_10) {
                pbVar14 = (byte *)((int)pbVar14 * 2);
              }
            }
          }
          else {
            pbVar14 = (byte *)(((uint)param_10 & 0x7ffffc00) + 0x400);
          }
          pbVar23 = *(byte **)(iVar6 + 0x48);
          if (pbVar14 == pbVar13) {
LAB_0045a791:
            uVar20 = (*(int *)(unaff_EBP + 0xc) + 1) * 2 | *(uint *)(iVar6 + 0x4c) & 1;
LAB_0045a7a4:
            *(uint *)(iVar6 + 0x4c) = uVar20;
            goto LAB_0045a7a7;
          }
          param_16 = (byte *)0x0;
          if (pbVar13 == (byte *)0x0) {
LAB_0045a770:
            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
              func_0x004010c0();
            }
            *(byte **)(iVar6 + 0x48) = param_16;
            pbVar23 = param_16;
            if (param_16 != (byte *)0x0) goto LAB_0045a791;
          }
          else {
            puVar12 = (undefined4 *)func_0x0097c5d0();
            if (puVar12 != (undefined4 *)0x0) {
              pbVar23 = (byte *)(puVar12 + 1);
              *puVar12 = pbVar13;
              func_0x004010e0();
              param_16 = pbVar23;
              if (pbVar23 != (byte *)0x0) {
                pbVar23 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
                param_9 = pbVar13;
                if (pbVar23 <= pbVar13) {
                  param_9 = pbVar23;
                }
                pbVar23 = (byte *)0x0;
                if (param_9 != (byte *)0x0) {
                  do {
                    FUN_005c2100();
                    pbVar23 = pbVar23 + 1;
                  } while (pbVar23 < param_9);
                }
                goto LAB_0045a770;
              }
            }
          }
        }
        else {
          param_7 = (byte *)0x0;
          if (pbVar23 == (byte *)0x0) {
LAB_0045a600:
            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
              func_0x004010c0();
            }
            *(byte **)(iVar6 + 0x48) = param_7;
            if (param_7 != (byte *)0x0) {
              uVar20 = (*(int *)(unaff_EBP + 0xc) + 1) * 2 | *(uint *)(iVar6 + 0x4c) & 1;
              pbVar23 = param_7;
              goto LAB_0045a7a4;
            }
          }
          else {
            puVar12 = (undefined4 *)func_0x0097c5d0();
            if (puVar12 != (undefined4 *)0x0) {
              pbVar13 = (byte *)(puVar12 + 1);
              *puVar12 = pbVar23;
              func_0x004010e0();
              param_7 = pbVar13;
              if (pbVar13 != (byte *)0x0) {
                pbVar13 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
                param_9 = pbVar23;
                if (pbVar13 <= pbVar23) {
                  param_9 = pbVar13;
                }
                pbVar23 = (byte *)0x0;
                if (param_9 != (byte *)0x0) {
                  do {
                    FUN_005c2100();
                    pbVar23 = pbVar23 + 1;
                  } while (pbVar23 < param_9);
                }
                goto LAB_0045a600;
              }
            }
          }
        }
LAB_0045a527:
        if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
          func_0x004010c0();
        }
        *(undefined4 *)(iVar6 + 0x48) = 0;
        *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1;
      }
    }
  }
  func_0x0041edb0();
  func_0x00401000();
LAB_0045a868:
  if (((*(byte *)(unaff_EBP + 0x10) & 1) != 0) && (param_17._3_1_ == '\0')) {
    param_9 = (byte *)0x0;
    func_0x00985ff0();
    uVar10 = extraout_ECX;
    uVar16 = func_0x00493050();
    func_0x004da1d0(*(int *)(unaff_EBP + 8) + 0x68,uVar16,uVar10);
    func_0x00407610();
    func_0x00401000();
  }
LAB_0045a8f6:
  if (in_stack_000000a8 != 0) {
    uVar10 = *(undefined4 *)(unaff_EBP + 0xc);
    in_stack_000000ac = 0;
    cVar4 = (**(code **)(*(int *)(*(int *)(unaff_EBP + 8) + 0x48) + 0xe0))();
    if (cVar4 == '\x02') {
      bVar24 = in_stack_000000ac == 0;
    }
    else {
      bVar24 = cVar4 == '\0';
    }
    if (bVar24) {
      param_33 = 0;
      func_0x00985ff0();
      uVar20 = (**(code **)(*(int *)(*(int *)(unaff_EBP + 8) + 0x54) + 0x88))(uVar10,0,1,1,0);
      func_0x00401000();
      param_26 = 0;
      func_0x006a5060(*(int *)(unaff_EBP + 8) + 0xf20,&UNK_00c8149c,uVar20 ^ param_35);
    }
  }
  func_0x00401210();
  return 0;
LAB_00456900:
  param_11 = (byte *)(*(int *)param_9 + (int)param_16 * 4);
  pbVar23 = param_11 + 4;
  param_12 = pbVar23;
  if (in_stack_000000fc == 0) goto LAB_00458824;
  puVar9 = *(uint **)param_11;
  if (puVar9 != (uint *)0x0) {
    if (puVar9 == &uRamfffffffc) {
      if ((uRamfffffffc >> 8 != 0) && (DAT_00000000 != '\0')) {
        bVar24 = false;
        goto LAB_00456992;
      }
    }
    else {
      if (puVar9 == (uint *)0x0) {
        puVar15 = (uint *)0x0;
      }
      else {
        puVar15 = puVar9 + 1;
      }
      bVar24 = true;
      iVar6 = 5;
      pcVar5 = "crop";
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar24 = *pcVar5 == (char)*puVar15;
        pcVar5 = pcVar5 + 1;
        puVar15 = (uint *)((int)puVar15 + 1);
      } while (bVar24);
LAB_00456992:
      if (bVar24) {
        unaff_ESI = 0;
        param_29 = 0;
        param_30 = 0;
        param_31 = 0;
        param_32 = 0;
        cVar4 = func_0x00987030();
        if (cVar4 != '\0') {
          if (((*(int *)pbVar23 != 0) &&
              (pcVar5 = (char *)(*(int *)pbVar23 + 4), pcVar5 != (char *)0x0)) && (*pcVar5 != '\0'))
          {
            iVar6 = func_0x00c07eef(pcVar5);
            if (iVar6 == 1) goto code_r0x00456a15;
          }
          goto LAB_004570bd;
        }
        func_0x009b90f0();
        iVar7 = param_32;
        iVar6 = param_29;
        if (((param_29 == -1) && (param_31 == -1)) && ((param_32 == -1 && (param_30 == -1))))
        goto LAB_004570bd;
        param_32 = param_30;
        param_29 = param_31;
        param_30 = iVar7;
        param_31 = iVar6;
        uVar25 = FUN_009b9150();
        iVar6 = *(int *)(unaff_EBP + 8);
        in_stack_00000154 = iVar6 + 0x14f8;
        in_stack_00000158 = (int *)(iVar6 + 0x14d0);
        _param_36 = uVar25;
        iVar7 = GetCurrentThreadId();
        if ((*(int *)(iVar6 + 0x14f0) == 0) || (*(int *)(iVar6 + 0x14f0) != iVar7)) {
          if (*(char *)(iVar6 + 0x14dc) == '\0') {
            (**(code **)(*(int *)(iVar6 + 0x14d0) + 0x18))();
            uVar25 = _param_36;
          }
          else {
            EnterCriticalSection();
            uVar25 = _param_36;
          }
          *(undefined4 *)(iVar6 + 0x14f4) = 0;
          *(int *)(iVar6 + 0x14f0) = iVar7;
        }
        else {
          *(int *)(iVar6 + 0x14f4) = *(int *)(iVar6 + 0x14f4) + 1;
          uVar25 = _param_36;
        }
        param_37 = (int)((ulonglong)uVar25 >> 0x20);
        param_36 = (int)uVar25;
        if ((*(int *)(iVar6 + 0x1528) != 0) &&
           (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 != 0xffffffff)) {
          iVar7 = *(int *)(iVar6 + 0x1528);
          if (uVar20 < *(uint *)(iVar7 + 0x4c) >> 1) {
            puVar1 = (undefined8 *)(*(int *)(iVar7 + 0x48) + uVar20 * 8);
            if ((*(int *)(*(int *)(iVar7 + 0x48) + uVar20 * 8) != param_36) ||
               (*(int *)((int)puVar1 + 4) != param_37)) {
              *puVar1 = uVar25;
              goto LAB_004570a9;
            }
          }
          else {
            pbVar23 = (byte *)(uVar20 + 1);
            param_7 = (byte *)(*(uint *)(iVar7 + 0x4c) >> 1);
            _param_36 = uVar25;
            if ((byte *)0xfffffff < pbVar23) {
              if (*(int *)(iVar7 + 0x48) != 0) {
                func_0x0097caf0();
              }
              *(undefined4 *)(iVar7 + 0x48) = 0;
              *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
              func_0x0041edb0();
              _cStack000000a4 = CONCAT31(uStack000000a5,1);
              goto LAB_00458824;
            }
            if (pbVar23 == param_7) {
              pbVar8 = *(byte **)(iVar7 + 0x48);
            }
            else if ((*(uint *)(iVar7 + 0x4c) & 1) == 0) {
              if ((uint)((int)pbVar23 * 8) < 0x100000) {
                pbVar13 = (byte *)0x1;
                if (pbVar23 != (byte *)0x0) {
                  do {
                    pbVar13 = (byte *)((int)pbVar13 * 2);
                  } while (pbVar13 <= pbVar23);
                }
              }
              else {
                pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
              }
              if ((uint)((int)param_7 * 8) < 0x100000) {
                pbVar14 = param_7;
                if ((byte *)0x1 < param_7) {
                  in_stack_00000104 = (float)(int)param_7;
                  pbVar14 = (byte *)(1 << ((char)((uint)in_stack_00000104 >> 0x17) + 0x81U & 0x1f));
                  param_10 = param_7;
                  if (pbVar14 < param_7) {
                    pbVar14 = (byte *)((int)pbVar14 * 2);
                  }
                }
              }
              else {
                pbVar14 = (byte *)(((uint)param_7 & 0x7ffffc00) + 0x400);
              }
              pbVar8 = *(byte **)(iVar7 + 0x48);
              if (pbVar14 != pbVar13) {
                if (pbVar13 == (byte *)0x0) {
                  if (pbVar8 != (byte *)0x0) {
                    func_0x0097caf0();
                    *(undefined4 *)(iVar7 + 0x48) = 0;
                    uVar25 = _param_36;
                  }
                }
                else {
                  uVar10 = func_0x0097c810();
                  *(undefined4 *)(iVar7 + 0x48) = uVar10;
                  uVar25 = _param_36;
                }
                pbVar8 = *(byte **)(iVar7 + 0x48);
                if (pbVar8 == (byte *)0x0) {
                  *(undefined4 *)(iVar7 + 0x48) = 0;
                  *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
                  _param_36 = uVar25;
                  func_0x0041edb0();
                  _cStack000000a4 = CONCAT31(uStack000000a5,1);
                  goto LAB_00458824;
                }
              }
              *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1 | (int)pbVar23 * 2;
            }
            else {
              if (pbVar23 == (byte *)0x0) {
                if (*(int *)(iVar7 + 0x48) != 0) {
                  func_0x0097caf0();
                  *(undefined4 *)(iVar7 + 0x48) = 0;
                  uVar25 = _param_36;
                }
              }
              else {
                uVar10 = func_0x0097c810();
                *(undefined4 *)(iVar7 + 0x48) = uVar10;
                uVar25 = _param_36;
              }
              pbVar8 = *(byte **)(iVar7 + 0x48);
              param_10 = pbVar8;
              if (pbVar8 == (byte *)0x0) {
                *(undefined4 *)(iVar7 + 0x48) = 0;
                *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
                _param_36 = uVar25;
                func_0x0041edb0();
                _cStack000000a4 = CONCAT31(uStack000000a5,1);
                goto LAB_00458824;
              }
              *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1 | (int)pbVar23 * 2;
            }
            param_37 = (int)((ulonglong)uVar25 >> 0x20);
            param_36 = (int)uVar25;
            pbVar13 = param_7;
            if (pbVar8 != (byte *)0x0) {
              for (; pbVar13 < pbVar23; pbVar13 = pbVar13 + 1) {
                iVar18 = *(int *)(iVar7 + 0x48);
                *(undefined4 *)(iVar18 + (int)pbVar13 * 8) = *(undefined4 *)(iVar6 + 0x1530);
                *(undefined4 *)(iVar18 + 4 + (int)pbVar13 * 8) = *(undefined4 *)(iVar6 + 0x1534);
              }
              iVar6 = *(int *)(*(int *)(iVar6 + 0x1528) + 0x48);
              iVar7 = *(int *)(unaff_EBP + 0xc);
              *(int *)(iVar6 + iVar7 * 8) = param_36;
              *(int *)(iVar6 + 4 + iVar7 * 8) = param_37;
LAB_004570a9:
              _param_36 = uVar25;
              func_0x006a2a60();
              uVar25 = _param_36;
            }
          }
        }
        _param_36 = uVar25;
        func_0x0041edb0();
LAB_004570bd:
        _cStack000000a4 = CONCAT31(uStack000000a5,1);
        goto LAB_00458824;
      }
    }
    if ((puVar9 == (uint *)0x0) || (puVar9 == &uRamfffffffc)) goto LAB_004570f4;
    if (puVar9 == (uint *)0x0) {
      puVar15 = (uint *)0x0;
    }
    else {
      puVar15 = puVar9 + 1;
    }
    bVar24 = true;
    iVar6 = 7;
    pcVar5 = "rotate";
    do {
      if (iVar6 == 0) break;
      iVar6 = iVar6 + -1;
      bVar24 = *pcVar5 == (char)*puVar15;
      pcVar5 = pcVar5 + 1;
      puVar15 = (uint *)((int)puVar15 + 1);
    } while (bVar24);
LAB_00457135:
    if (!bVar24) goto LAB_0045768e;
    iVar6 = *(int *)(unaff_EBP + 8);
    pbVar23 = (byte *)(iVar6 + 0x1470);
    in_stack_0000015c = iVar6 + 0x1498;
    param_7 = pbVar23;
    in_stack_00000160 = pbVar23;
    iVar7 = GetCurrentThreadId();
    if ((*(int *)(iVar6 + 0x1490) == 0) || (*(int *)(iVar6 + 0x1490) != iVar7)) {
      if (*(char *)(iVar6 + 0x147c) == '\0') {
        (**(code **)(*(int *)pbVar23 + 0x18))();
      }
      else {
        EnterCriticalSection();
      }
      *(undefined4 *)(iVar6 + 0x1494) = 0;
      *(int *)(iVar6 + 0x1490) = iVar7;
    }
    else {
      *(int *)(iVar6 + 0x1494) = *(int *)(iVar6 + 0x1494) + 1;
    }
    if ((*(int *)(iVar6 + 0x14c8) == 0) || (*(int *)(unaff_EBP + 0xc) == -1)) goto LAB_00457678;
    uVar20 = *(uint *)(unaff_EBP + 0xc);
    iVar6 = *(int *)(iVar6 + 0x14c8);
    if (uVar20 < *(uint *)(iVar6 + 0x4c) >> 1) {
      if (*(int *)param_12 == 0) {
        puVar9 = (uint *)0x0;
      }
      else {
        puVar9 = (uint *)(*(int *)param_12 + 4);
      }
      puVar15 = *(uint **)(*(int *)(iVar6 + 0x48) + uVar20 * 4);
      if (puVar15 == (uint *)0x0) {
LAB_00457626:
        if (puVar9 == (uint *)0x0) goto LAB_00457678;
        if ((char)*puVar9 == '\0') {
          func_0x0041edb0();
          param_18._3_1_ = '\x01';
          goto LAB_00458824;
        }
      }
      else {
        if ((puVar15 == &uRamfffffffc) || (puVar9 == (uint *)0x0)) {
          if ((puVar15 != (uint *)0x0) && (*puVar15 >> 8 != 0)) {
            if (puVar15 == (uint *)0x0) {
              puVar21 = (uint *)0x0;
            }
            else {
              puVar21 = puVar15 + 1;
            }
            if ((char)*puVar21 != '\0') {
              if (puVar15 == (uint *)0x0) {
                puVar15 = (uint *)0x0;
              }
              else {
                puVar15 = puVar15 + 1;
              }
              bVar24 = puVar15 == puVar9;
              goto LAB_00457652;
            }
          }
          goto LAB_00457626;
        }
        if (puVar15 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar15 + 1;
        }
        do {
          bVar2 = (byte)*puVar9;
          bVar24 = bVar2 < (byte)*puVar15;
          if (bVar2 != (byte)*puVar15) {
LAB_00457602:
            bVar24 = 1 - bVar24 == (uint)(bVar24 != 0);
            goto LAB_00457652;
          }
          if (bVar2 == 0) break;
          bVar2 = *(byte *)((int)puVar9 + 1);
          bVar24 = bVar2 < *(byte *)((int)puVar15 + 1);
          if (bVar2 != *(byte *)((int)puVar15 + 1)) goto LAB_00457602;
          puVar9 = (uint *)((int)puVar9 + 2);
          puVar15 = (uint *)((int)puVar15 + 2);
        } while (bVar2 != 0);
        bVar24 = true;
LAB_00457652:
        if (bVar24) goto LAB_00457678;
      }
      FUN_005c2100();
    }
    else {
      pbVar23 = (byte *)(uVar20 + 1);
      param_10 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
      if ((byte *)0x1fffffff < pbVar23) goto LAB_004571d8;
      if (pbVar23 == param_10) {
        pbVar14 = *(byte **)(iVar6 + 0x48);
      }
      else {
        if ((*(uint *)(iVar6 + 0x4c) & 1) == 0) {
          if ((uint)((int)pbVar23 * 4) < 0x100000) {
            pbVar23 = (byte *)0x1;
            if (*(int *)(unaff_EBP + 0xc) != -1) {
              do {
                pbVar23 = (byte *)((int)pbVar23 * 2);
              } while (pbVar23 <= (byte *)(*(int *)(unaff_EBP + 0xc) + 1));
            }
          }
          else {
            pbVar23 = (byte *)((*(int *)(unaff_EBP + 0xc) + 1U & 0xfffffc00) + 0x400);
          }
          if ((uint)((int)param_10 * 4) < 0x100000) {
            pbVar13 = param_10;
            if ((byte *)0x1 < param_10) {
              in_stack_0000010c = (float)(int)param_10;
              pbVar13 = (byte *)(1 << ((char)((uint)in_stack_0000010c >> 0x17) + 0x81U & 0x1f));
              param_15 = param_10;
              if (pbVar13 < param_10) {
                pbVar13 = (byte *)((int)pbVar13 * 2);
              }
            }
          }
          else {
            pbVar13 = (byte *)(((uint)param_10 & 0x7ffffc00) + 0x400);
          }
          pbVar14 = *(byte **)(iVar6 + 0x48);
          if (pbVar13 != pbVar23) {
            pbVar14 = (byte *)0x0;
            if (pbVar23 != (byte *)0x0) {
              puVar12 = (undefined4 *)func_0x0097c5d0();
              if (puVar12 == (undefined4 *)0x0) goto LAB_004571d8;
              pbVar13 = (byte *)(puVar12 + 1);
              *puVar12 = pbVar23;
              func_0x004010e0();
              param_15 = pbVar13;
              if (pbVar13 == (byte *)0x0) goto LAB_004571d8;
              pbVar14 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
              param_6 = pbVar23;
              if (pbVar14 <= pbVar23) {
                param_6 = pbVar14;
              }
              param_8 = (byte *)0x0;
              pbVar14 = pbVar13;
              if (param_6 != (byte *)0x0) {
                do {
                  iVar18 = *(int *)(iVar6 + 0x48);
                  iVar7 = (int)param_8 * 4;
                  if (*(int *)pbVar13 != *(int *)(iVar18 + (int)param_8 * 4)) {
                    func_0x00401000();
                    pbVar23 = *(byte **)(iVar18 + iVar7);
                    *(byte **)pbVar13 = pbVar23;
                    if (pbVar23 != (byte *)0x0) {
                      if (*pbVar23 < 0x80) {
                        cVar4 = InterlockedIncrement();
                        if (cVar4 != -1) goto LAB_004574b4;
                      }
                      func_0x00985a60();
                    }
                  }
LAB_004574b4:
                  param_8 = param_8 + 1;
                  pbVar13 = pbVar13 + 4;
                  pbVar14 = param_15;
                } while (param_8 < param_6);
              }
            }
            if ((*(int *)(iVar6 + 0x48) != 0) && (iVar7 = *(int *)(iVar6 + 0x48), iVar7 != 0)) {
              func_0x00401110();
              func_0x0097caf0(iVar7 + -4);
            }
            *(byte **)(iVar6 + 0x48) = pbVar14;
            goto joined_r0x004574fb;
          }
        }
        else {
          pbVar14 = (byte *)0x0;
          if (pbVar23 != (byte *)0x0) {
            puVar12 = (undefined4 *)func_0x0097c5d0();
            if (puVar12 == (undefined4 *)0x0) goto LAB_004571d8;
            pbVar13 = (byte *)(*(int *)(unaff_EBP + 0xc) + 1);
            pbVar23 = (byte *)(puVar12 + 1);
            *puVar12 = pbVar13;
            func_0x004010e0();
            param_15 = pbVar23;
            if (pbVar23 == (byte *)0x0) goto LAB_004571d8;
            param_6 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
            if (pbVar13 < param_6) {
              param_6 = pbVar13;
            }
            param_8 = (byte *)0x0;
            pbVar14 = pbVar23;
            if (param_6 != (byte *)0x0) {
              do {
                iVar18 = *(int *)(iVar6 + 0x48);
                iVar7 = (int)param_8 * 4;
                if (*(int *)pbVar23 != *(int *)(iVar18 + (int)param_8 * 4)) {
                  func_0x00401000();
                  pbVar13 = *(byte **)(iVar18 + iVar7);
                  *(byte **)pbVar23 = pbVar13;
                  if (pbVar13 != (byte *)0x0) {
                    if (*pbVar13 < 0x80) {
                      cVar4 = InterlockedIncrement();
                      if (cVar4 != -1) goto LAB_00457303;
                    }
                    func_0x00985a60();
                  }
                }
LAB_00457303:
                param_8 = param_8 + 1;
                pbVar23 = pbVar23 + 4;
                pbVar14 = param_15;
              } while (param_8 < param_6);
            }
          }
          if ((*(int *)(iVar6 + 0x48) != 0) && (iVar7 = *(int *)(iVar6 + 0x48), iVar7 != 0)) {
            func_0x00401110();
            func_0x0097caf0(iVar7 + -4);
          }
          *(byte **)(iVar6 + 0x48) = pbVar14;
joined_r0x004574fb:
          if (pbVar14 == (byte *)0x0) {
LAB_004571d8:
            if ((*(int *)(iVar6 + 0x48) != 0) && (iVar7 = *(int *)(iVar6 + 0x48), iVar7 != 0)) {
              func_0x00401110();
              func_0x0097caf0(iVar7 + -4);
            }
            *(undefined4 *)(iVar6 + 0x48) = 0;
            *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1;
            func_0x0041edb0();
            param_18._3_1_ = '\x01';
            goto LAB_00458824;
          }
        }
        *(uint *)(iVar6 + 0x4c) = (*(int *)(unaff_EBP + 0xc) + 1) * 2 | *(uint *)(iVar6 + 0x4c) & 1;
      }
      if (pbVar14 == (byte *)0x0) goto LAB_00457678;
      param_15 = (byte *)(*(int *)(unaff_EBP + 0xc) + 1);
      pbVar23 = param_10;
      if (param_10 < param_15) {
        do {
          iVar7 = *(int *)(iVar6 + 0x48);
          if (*(int *)(iVar7 + (int)pbVar23 * 4) != *(int *)(param_7 + 0x5c)) {
            func_0x00401000();
            pbVar13 = *(byte **)(param_7 + 0x5c);
            *(byte **)(iVar7 + (int)pbVar23 * 4) = pbVar13;
            if (pbVar13 != (byte *)0x0) {
              if (*pbVar13 < 0x80) {
                cVar4 = InterlockedIncrement();
                if (cVar4 != -1) goto LAB_0045757a;
              }
              func_0x00985a60();
            }
          }
LAB_0045757a:
          pbVar23 = pbVar23 + 1;
        } while (pbVar23 < param_15);
      }
      FUN_005c2100();
    }
    func_0x006a2a60();
LAB_00457678:
    func_0x0041edb0();
    param_18._3_1_ = '\x01';
    goto LAB_00458824;
  }
LAB_004570f4:
  if (*(int *)param_11 == 0) {
LAB_0045768e:
    if ((puVar9 == (uint *)0x0) || (puVar9 == &uRamfffffffc)) goto LAB_004576b8;
    if (puVar9 == (uint *)0x0) {
      puVar15 = (uint *)0x0;
    }
    else {
      puVar15 = puVar9 + 1;
    }
    bVar24 = true;
    iVar6 = 8;
    pcVar5 = "filters";
    do {
      if (iVar6 == 0) break;
      iVar6 = iVar6 + -1;
      bVar24 = *pcVar5 == (char)*puVar15;
      pcVar5 = pcVar5 + 1;
      puVar15 = (uint *)((int)puVar15 + 1);
    } while (bVar24);
LAB_004576f9:
    if (!bVar24) goto LAB_00457b5c;
    iVar6 = *(int *)(unaff_EBP + 8);
    pbVar23 = (byte *)(iVar6 + 0x16b8);
    in_stack_00000110 = iVar6 + 0x16e0;
    param_15 = pbVar23;
    in_stack_00000114 = pbVar23;
    iVar7 = GetCurrentThreadId();
    if ((*(int *)(iVar6 + 0x16d8) == 0) || (*(int *)(iVar6 + 0x16d8) != iVar7)) {
      if (*(char *)(iVar6 + 0x16c4) == '\0') {
        (**(code **)(*(int *)pbVar23 + 0x18))();
      }
      else {
        EnterCriticalSection();
      }
      *(undefined4 *)(iVar6 + 0x16dc) = 0;
      *(int *)(iVar6 + 0x16d8) = iVar7;
    }
    else {
      *(int *)(iVar6 + 0x16dc) = *(int *)(iVar6 + 0x16dc) + 1;
    }
    if ((*(int *)(iVar6 + 0x1710) == 0) || (*(int *)(unaff_EBP + 0xc) == -1)) goto LAB_00457b46;
    iVar6 = *(int *)(iVar6 + 0x1710);
    uVar20 = *(uint *)(unaff_EBP + 0xc);
    if (uVar20 < *(uint *)(iVar6 + 0x4c) >> 1) {
      if (*(int *)param_12 == 0) {
        puVar9 = (uint *)0x0;
      }
      else {
        puVar9 = (uint *)(*(int *)param_12 + 4);
      }
      puVar15 = *(uint **)(*(int *)(iVar6 + 0x48) + uVar20 * 4);
      if (puVar15 == (uint *)0x0) {
LAB_00457af6:
        if (puVar9 == (uint *)0x0) goto LAB_00457b46;
        if ((char)*puVar9 == '\0') {
          func_0x0041edb0();
          param_18._1_1_ = '\x01';
          goto LAB_00458824;
        }
      }
      else {
        if ((puVar15 == &uRamfffffffc) || (puVar9 == (uint *)0x0)) {
          if ((puVar15 != (uint *)0x0) && (*puVar15 >> 8 != 0)) {
            if (puVar15 == (uint *)0x0) {
              puVar21 = (uint *)0x0;
            }
            else {
              puVar21 = puVar15 + 1;
            }
            if ((char)*puVar21 != '\0') {
              if (puVar15 == (uint *)0x0) {
                puVar15 = (uint *)0x0;
              }
              else {
                puVar15 = puVar15 + 1;
              }
              bVar24 = puVar15 == puVar9;
              goto LAB_00457b22;
            }
          }
          goto LAB_00457af6;
        }
        if (puVar15 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar15 + 1;
        }
        do {
          bVar2 = (byte)*puVar9;
          bVar24 = bVar2 < (byte)*puVar15;
          if (bVar2 != (byte)*puVar15) {
LAB_00457ad2:
            bVar24 = 1 - bVar24 == (uint)(bVar24 != 0);
            goto LAB_00457b22;
          }
          if (bVar2 == 0) break;
          bVar2 = *(byte *)((int)puVar9 + 1);
          bVar24 = bVar2 < *(byte *)((int)puVar15 + 1);
          if (bVar2 != *(byte *)((int)puVar15 + 1)) goto LAB_00457ad2;
          puVar9 = (uint *)((int)puVar9 + 2);
          puVar15 = (uint *)((int)puVar15 + 2);
        } while (bVar2 != 0);
        bVar24 = true;
LAB_00457b22:
        if (bVar24) goto LAB_00457b46;
      }
      FUN_005c2100();
    }
    else {
      pbVar23 = (byte *)(uVar20 + 1);
      param_10 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
      if ((byte *)0x1fffffff < pbVar23) goto LAB_0045779c;
      if (pbVar23 == param_10) {
        pbVar14 = *(byte **)(iVar6 + 0x48);
      }
      else {
        if ((*(uint *)(iVar6 + 0x4c) & 1) == 0) {
          if ((uint)((int)pbVar23 * 4) < 0x100000) {
            pbVar13 = (byte *)0x1;
            if (pbVar23 != (byte *)0x0) {
              do {
                pbVar13 = (byte *)((int)pbVar13 * 2);
              } while (pbVar13 <= pbVar23);
            }
          }
          else {
            pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
          }
          if ((uint)((int)param_10 * 4) < 0x100000) {
            pbVar23 = param_10;
            if ((byte *)0x1 < param_10) {
              in_stack_00000100 = (float)(int)param_10;
              pbVar23 = (byte *)(1 << ((char)((uint)in_stack_00000100 >> 0x17) + 0x81U & 0x1f));
              param_6 = param_10;
              if (pbVar23 < param_10) {
                pbVar23 = (byte *)((int)pbVar23 * 2);
              }
            }
          }
          else {
            pbVar23 = (byte *)(((uint)param_10 & 0x7ffffc00) + 0x400);
          }
          pbVar14 = *(byte **)(iVar6 + 0x48);
          if (pbVar23 != pbVar13) {
            param_8 = (byte *)0x0;
            if (pbVar13 != (byte *)0x0) {
              puVar12 = (undefined4 *)func_0x0097c5d0();
              if (puVar12 == (undefined4 *)0x0) goto LAB_0045779c;
              pbVar23 = (byte *)(puVar12 + 1);
              *puVar12 = pbVar13;
              func_0x004010e0();
              param_8 = pbVar23;
              if (pbVar23 == (byte *)0x0) goto LAB_0045779c;
              pbVar23 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
              param_6 = pbVar13;
              if (pbVar23 <= pbVar13) {
                param_6 = pbVar23;
              }
              pbVar23 = (byte *)0x0;
              if (param_6 != (byte *)0x0) {
                do {
                  FUN_005c2100();
                  pbVar23 = pbVar23 + 1;
                } while (pbVar23 < param_6);
              }
            }
            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
              func_0x004010c0();
            }
            *(byte **)(iVar6 + 0x48) = param_8;
            pbVar14 = param_8;
            if (param_8 == (byte *)0x0) goto LAB_0045779c;
          }
          uVar20 = (*(int *)(unaff_EBP + 0xc) + 1) * 2 | *(uint *)(iVar6 + 0x4c) & 1;
        }
        else {
          param_7 = (byte *)0x0;
          if (pbVar23 != (byte *)0x0) {
            puVar12 = (undefined4 *)func_0x0097c5d0();
            if (puVar12 == (undefined4 *)0x0) goto LAB_0045779c;
            pbVar13 = (byte *)(puVar12 + 1);
            *puVar12 = pbVar23;
            func_0x004010e0();
            param_7 = pbVar13;
            if (pbVar13 == (byte *)0x0) goto LAB_0045779c;
            pbVar13 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
            param_6 = pbVar23;
            if (pbVar13 <= pbVar23) {
              param_6 = pbVar13;
            }
            pbVar23 = (byte *)0x0;
            if (param_6 != (byte *)0x0) {
              do {
                FUN_005c2100();
                pbVar23 = pbVar23 + 1;
              } while (pbVar23 < param_6);
            }
          }
          if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
            func_0x004010c0();
          }
          *(byte **)(iVar6 + 0x48) = param_7;
          if (param_7 == (byte *)0x0) {
LAB_0045779c:
            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
              func_0x004010c0();
            }
            *(undefined4 *)(iVar6 + 0x48) = 0;
            *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1;
            func_0x0041edb0();
            param_18._1_1_ = '\x01';
            goto LAB_00458824;
          }
          uVar20 = (*(int *)(unaff_EBP + 0xc) + 1) * 2 | *(uint *)(iVar6 + 0x4c) & 1;
          pbVar14 = param_7;
        }
        *(uint *)(iVar6 + 0x4c) = uVar20;
      }
      if (pbVar14 == (byte *)0x0) goto LAB_00457b46;
      pbVar23 = param_10;
      if (param_10 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1)) {
        do {
          FUN_005c2100();
          pbVar23 = pbVar23 + 1;
        } while (pbVar23 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1));
      }
      FUN_005c2100();
    }
    func_0x006a2a60();
LAB_00457b46:
    func_0x0041edb0();
    param_18._1_1_ = '\x01';
    goto LAB_00458824;
  }
  if (puVar9 != (uint *)0x0) {
    if (*puVar9 >> 8 != 0) {
      if (puVar9 == (uint *)0x0) {
        puVar15 = (uint *)0x0;
      }
      else {
        puVar15 = puVar9 + 1;
      }
      if ((char)*puVar15 != '\0') {
        if (puVar9 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar9 + 1;
        }
        bVar24 = puVar15 == (uint *)&UNK_00c80ad4;
        goto LAB_00457135;
      }
    }
    goto LAB_0045768e;
  }
LAB_004576b8:
  if (*(int *)param_11 == 0) {
LAB_00457b5c:
    if ((puVar9 == (uint *)0x0) || (puVar9 == &uRamfffffffc)) goto LAB_00457b86;
    if (puVar9 == (uint *)0x0) {
      puVar15 = (uint *)0x0;
    }
    else {
      puVar15 = puVar9 + 1;
    }
    bVar24 = true;
    iVar6 = 5;
    pcVar5 = "text";
    do {
      if (iVar6 == 0) break;
      iVar6 = iVar6 + -1;
      bVar24 = *pcVar5 == (char)*puVar15;
      pcVar5 = pcVar5 + 1;
      puVar15 = (uint *)((int)puVar15 + 1);
    } while (bVar24);
LAB_00457bc7:
    if (!bVar24) goto LAB_0045802f;
    iVar6 = *(int *)(unaff_EBP + 8);
    pbVar23 = (byte *)(iVar6 + 0x1718);
    in_stack_0000014c = iVar6 + 0x1740;
    param_15 = pbVar23;
    in_stack_00000150 = pbVar23;
    iVar7 = GetCurrentThreadId();
    if ((*(int *)(iVar6 + 0x1738) == 0) || (*(int *)(iVar6 + 0x1738) != iVar7)) {
      if (*(char *)(iVar6 + 0x1724) == '\0') {
        (**(code **)(*(int *)pbVar23 + 0x18))();
      }
      else {
        EnterCriticalSection();
      }
      *(undefined4 *)(iVar6 + 0x173c) = 0;
      *(int *)(iVar6 + 0x1738) = iVar7;
    }
    else {
      *(int *)(iVar6 + 0x173c) = *(int *)(iVar6 + 0x173c) + 1;
    }
    if ((*(int *)(iVar6 + 6000) == 0) || (*(int *)(unaff_EBP + 0xc) == -1)) goto LAB_00458019;
    iVar6 = *(int *)(iVar6 + 6000);
    uVar20 = *(uint *)(unaff_EBP + 0xc);
    if (uVar20 < *(uint *)(iVar6 + 0x4c) >> 1) {
      if (*(int *)param_12 == 0) {
        puVar9 = (uint *)0x0;
      }
      else {
        puVar9 = (uint *)(*(int *)param_12 + 4);
      }
      puVar15 = *(uint **)(*(int *)(iVar6 + 0x48) + uVar20 * 4);
      if (puVar15 == (uint *)0x0) {
LAB_00457fc9:
        if (puVar9 == (uint *)0x0) goto LAB_00458019;
        if ((char)*puVar9 == '\0') {
          func_0x0041edb0();
          param_18._2_1_ = '\x01';
          goto LAB_00458824;
        }
      }
      else {
        if ((puVar15 == &uRamfffffffc) || (puVar9 == (uint *)0x0)) {
          if ((puVar15 != (uint *)0x0) && (*puVar15 >> 8 != 0)) {
            if (puVar15 == (uint *)0x0) {
              puVar21 = (uint *)0x0;
            }
            else {
              puVar21 = puVar15 + 1;
            }
            if ((char)*puVar21 != '\0') {
              if (puVar15 == (uint *)0x0) {
                puVar15 = (uint *)0x0;
              }
              else {
                puVar15 = puVar15 + 1;
              }
              bVar24 = puVar15 == puVar9;
              goto LAB_00457ff5;
            }
          }
          goto LAB_00457fc9;
        }
        if (puVar15 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar15 + 1;
        }
        do {
          bVar2 = (byte)*puVar9;
          bVar24 = bVar2 < (byte)*puVar15;
          if (bVar2 != (byte)*puVar15) {
LAB_00457fa5:
            bVar24 = 1 - bVar24 == (uint)(bVar24 != 0);
            goto LAB_00457ff5;
          }
          if (bVar2 == 0) break;
          bVar2 = *(byte *)((int)puVar9 + 1);
          bVar24 = bVar2 < *(byte *)((int)puVar15 + 1);
          if (bVar2 != *(byte *)((int)puVar15 + 1)) goto LAB_00457fa5;
          puVar9 = (uint *)((int)puVar9 + 2);
          puVar15 = (uint *)((int)puVar15 + 2);
        } while (bVar2 != 0);
        bVar24 = true;
LAB_00457ff5:
        if (bVar24) goto LAB_00458019;
      }
      FUN_005c2100();
    }
    else {
      pbVar23 = (byte *)(uVar20 + 1);
      param_10 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
      if ((byte *)0x1fffffff < pbVar23) goto LAB_00457c6a;
      if (pbVar23 == param_10) {
        pbVar14 = *(byte **)(iVar6 + 0x48);
      }
      else {
        if ((*(uint *)(iVar6 + 0x4c) & 1) == 0) {
          if ((uint)((int)pbVar23 * 4) < 0x100000) {
            pbVar13 = (byte *)0x1;
            if (pbVar23 != (byte *)0x0) {
              do {
                pbVar13 = (byte *)((int)pbVar13 * 2);
              } while (pbVar13 <= pbVar23);
            }
          }
          else {
            pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
          }
          if ((uint)((int)param_10 * 4) < 0x100000) {
            pbVar23 = param_10;
            if ((byte *)0x1 < param_10) {
              in_stack_000000ec = (float)(int)param_10;
              pbVar23 = (byte *)(1 << ((char)((uint)in_stack_000000ec >> 0x17) + 0x81U & 0x1f));
              param_6 = param_10;
              if (pbVar23 < param_10) {
                pbVar23 = (byte *)((int)pbVar23 * 2);
              }
            }
          }
          else {
            pbVar23 = (byte *)(((uint)param_10 & 0x7ffffc00) + 0x400);
          }
          pbVar14 = *(byte **)(iVar6 + 0x48);
          if (pbVar23 != pbVar13) {
            param_8 = (byte *)0x0;
            if (pbVar13 != (byte *)0x0) {
              puVar12 = (undefined4 *)func_0x0097c5d0();
              if (puVar12 == (undefined4 *)0x0) goto LAB_00457c6a;
              pbVar23 = (byte *)(puVar12 + 1);
              *puVar12 = pbVar13;
              func_0x004010e0();
              param_8 = pbVar23;
              if (pbVar23 == (byte *)0x0) goto LAB_00457c6a;
              pbVar23 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
              param_6 = pbVar13;
              if (pbVar23 <= pbVar13) {
                param_6 = pbVar23;
              }
              pbVar23 = (byte *)0x0;
              if (param_6 != (byte *)0x0) {
                do {
                  FUN_005c2100();
                  pbVar23 = pbVar23 + 1;
                } while (pbVar23 < param_6);
              }
            }
            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
              func_0x004010c0();
            }
            *(byte **)(iVar6 + 0x48) = param_8;
            pbVar14 = param_8;
            if (param_8 == (byte *)0x0) goto LAB_00457c6a;
          }
          uVar20 = (*(int *)(unaff_EBP + 0xc) + 1) * 2 | *(uint *)(iVar6 + 0x4c) & 1;
        }
        else {
          param_7 = (byte *)0x0;
          if (pbVar23 != (byte *)0x0) {
            puVar12 = (undefined4 *)func_0x0097c5d0();
            if (puVar12 == (undefined4 *)0x0) goto LAB_00457c6a;
            pbVar13 = (byte *)(puVar12 + 1);
            *puVar12 = pbVar23;
            func_0x004010e0();
            param_7 = pbVar13;
            if (pbVar13 == (byte *)0x0) goto LAB_00457c6a;
            pbVar13 = (byte *)(*(uint *)(iVar6 + 0x4c) >> 1);
            param_6 = pbVar23;
            if (pbVar13 <= pbVar23) {
              param_6 = pbVar13;
            }
            pbVar23 = (byte *)0x0;
            if (param_6 != (byte *)0x0) {
              do {
                FUN_005c2100();
                pbVar23 = pbVar23 + 1;
              } while (pbVar23 < param_6);
            }
          }
          if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
            func_0x004010c0();
          }
          *(byte **)(iVar6 + 0x48) = param_7;
          if (param_7 == (byte *)0x0) {
LAB_00457c6a:
            if ((*(int *)(iVar6 + 0x48) != 0) && (*(int *)(iVar6 + 0x48) != 0)) {
              func_0x004010c0();
            }
            *(undefined4 *)(iVar6 + 0x48) = 0;
            *(uint *)(iVar6 + 0x4c) = *(uint *)(iVar6 + 0x4c) & 1;
            func_0x0041edb0();
            param_18._2_1_ = '\x01';
            goto LAB_00458824;
          }
          uVar20 = (*(int *)(unaff_EBP + 0xc) + 1) * 2 | *(uint *)(iVar6 + 0x4c) & 1;
          pbVar14 = param_7;
        }
        *(uint *)(iVar6 + 0x4c) = uVar20;
      }
      if (pbVar14 == (byte *)0x0) goto LAB_00458019;
      pbVar23 = param_10;
      if (param_10 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1)) {
        do {
          FUN_005c2100();
          pbVar23 = pbVar23 + 1;
        } while (pbVar23 < (byte *)(*(int *)(unaff_EBP + 0xc) + 1));
      }
      FUN_005c2100();
    }
    func_0x006a2a60();
LAB_00458019:
    func_0x0041edb0();
    param_18._2_1_ = '\x01';
    goto LAB_00458824;
  }
  if (puVar9 != (uint *)0x0) {
    if (*puVar9 >> 8 != 0) {
      if (puVar9 == (uint *)0x0) {
        puVar15 = (uint *)0x0;
      }
      else {
        puVar15 = puVar9 + 1;
      }
      if ((char)*puVar15 != '\0') {
        if (puVar9 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar9 + 1;
        }
        bVar24 = puVar15 == (uint *)&UNK_00c80b04;
        goto LAB_004576f9;
      }
    }
    goto LAB_00457b5c;
  }
LAB_00457b86:
  if (*(int *)param_11 == 0) {
LAB_0045802f:
    if ((puVar9 == (uint *)0x0) || (puVar9 == &uRamfffffffc)) goto LAB_00458059;
    if (puVar9 == (uint *)0x0) {
      puVar15 = (uint *)0x0;
    }
    else {
      puVar15 = puVar9 + 1;
    }
    bVar24 = true;
    iVar6 = 0xb;
    pcVar5 = "textactive";
    do {
      if (iVar6 == 0) break;
      iVar6 = iVar6 + -1;
      bVar24 = *pcVar5 == (char)*puVar15;
      pcVar5 = pcVar5 + 1;
      puVar15 = (uint *)((int)puVar15 + 1);
    } while (bVar24);
LAB_0045809a:
    if (!bVar24) goto LAB_0045834a;
    iVar6 = *(int *)pbVar23;
    if (iVar6 == 0) {
LAB_004580f6:
      param_13._3_1_ = false;
    }
    else if (iVar6 == -4) {
      if ((uRamfffffffc >> 8 == 0) || (DAT_00000000 == '\0')) goto LAB_004580f6;
      param_13._3_1_ = false;
    }
    else if (iVar6 == 0) {
      iVar6 = 2;
      param_13._3_1_ = true;
      pcVar5 = "1";
      pcVar19 = (char *)0x0;
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        param_13._3_1_ = *pcVar5 == *pcVar19;
        pcVar5 = pcVar5 + 1;
        pcVar19 = pcVar19 + 1;
      } while ((bool)param_13._3_1_);
    }
    else {
      iVar7 = 2;
      param_13._3_1_ = true;
      pcVar5 = "1";
      pcVar19 = (char *)(iVar6 + 4);
      do {
        if (iVar7 == 0) break;
        iVar7 = iVar7 + -1;
        param_13._3_1_ = *pcVar5 == *pcVar19;
        pcVar5 = pcVar5 + 1;
        pcVar19 = pcVar19 + 1;
      } while ((bool)param_13._3_1_);
    }
    iVar6 = *(int *)(unaff_EBP + 8);
    in_stack_00000130 = iVar6 + 0x17a0;
    in_stack_00000134 = (int *)(iVar6 + 0x1778);
    iVar7 = GetCurrentThreadId();
    if ((*(int *)(iVar6 + 0x1798) == 0) || (*(int *)(iVar6 + 0x1798) != iVar7)) {
      if (*(char *)(iVar6 + 0x1784) == '\0') {
        (**(code **)(*(int *)(iVar6 + 0x1778) + 0x18))();
      }
      else {
        EnterCriticalSection();
      }
      *(undefined4 *)(iVar6 + 0x179c) = 0;
      *(int *)(iVar6 + 0x1798) = iVar7;
    }
    else {
      *(int *)(iVar6 + 0x179c) = *(int *)(iVar6 + 0x179c) + 1;
    }
    if ((*(int *)(iVar6 + 0x17d0) == 0) ||
       (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 == 0xffffffff)) goto LAB_00458339;
    iVar7 = *(int *)(iVar6 + 0x17d0);
    if (uVar20 < *(uint *)(iVar7 + 0x4c) >> 1) {
      pcVar5 = (char *)(uVar20 + *(int *)(iVar7 + 0x48));
      if (*pcVar5 == param_13._3_1_) goto LAB_00458339;
      *pcVar5 = param_13._3_1_;
    }
    else {
      pbVar23 = (byte *)(uVar20 + 1);
      param_10 = (byte *)(*(uint *)(iVar7 + 0x4c) >> 1);
      if ((byte *)0x7fffffff < pbVar23) {
        if (*(int *)(iVar7 + 0x48) != 0) {
          func_0x0097caf0();
        }
        *(undefined4 *)(iVar7 + 0x48) = 0;
        *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
        func_0x0041edb0();
        goto LAB_00458824;
      }
      if (pbVar23 == param_10) {
        iVar18 = *(int *)(iVar7 + 0x48);
      }
      else {
        if ((*(uint *)(iVar7 + 0x4c) & 1) == 0) {
          if (pbVar23 < (byte *)0x100000) {
            pbVar13 = (byte *)0x1;
            if (pbVar23 != (byte *)0x0) {
              do {
                pbVar13 = (byte *)((int)pbVar13 * 2);
              } while (pbVar13 <= pbVar23);
            }
          }
          else {
            pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
          }
          if (param_10 < (byte *)0x100000) {
            pbVar14 = param_10;
            if ((byte *)0x1 < param_10) {
              in_stack_000000f8 = (float)(int)param_10;
              pbVar14 = (byte *)(1 << ((char)((uint)in_stack_000000f8 >> 0x17) + 0x81U & 0x1f));
              param_15 = param_10;
              if (pbVar14 < param_10) {
                pbVar14 = (byte *)((int)pbVar14 * 2);
              }
            }
          }
          else {
            pbVar14 = (byte *)(((uint)param_10 & 0x7ffffc00) + 0x400);
          }
          iVar18 = *(int *)(iVar7 + 0x48);
          if (pbVar14 != pbVar13) {
            if (pbVar13 == (byte *)0x0) goto joined_r0x004582ab;
            uVar10 = func_0x0097c810();
            *(undefined4 *)(iVar7 + 0x48) = uVar10;
            goto LAB_004582bd;
          }
        }
        else {
          if (pbVar23 == (byte *)0x0) {
            iVar18 = *(int *)(iVar7 + 0x48);
joined_r0x004582ab:
            if (iVar18 != 0) {
              func_0x0097caf0();
              *(undefined4 *)(iVar7 + 0x48) = 0;
            }
          }
          else {
            uVar10 = func_0x0097c810();
            *(undefined4 *)(iVar7 + 0x48) = uVar10;
          }
LAB_004582bd:
          iVar18 = *(int *)(iVar7 + 0x48);
          if (iVar18 == 0) {
            *(undefined4 *)(iVar7 + 0x48) = 0;
            *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
            func_0x0041edb0();
            goto LAB_00458824;
          }
        }
        *(uint *)(iVar7 + 0x4c) = (int)pbVar23 * 2 | *(uint *)(iVar7 + 0x4c) & 1;
      }
      pbVar13 = param_10;
      if (iVar18 == 0) goto LAB_00458339;
      for (; pbVar13 < pbVar23; pbVar13 = pbVar13 + 1) {
        pbVar13[*(int *)(iVar7 + 0x48)] = *(byte *)(iVar6 + 0x17d4);
      }
      *(char *)(*(int *)(unaff_EBP + 0xc) + *(int *)(*(int *)(iVar6 + 0x17d0) + 0x48)) =
           param_13._3_1_;
    }
    func_0x006a2a60();
LAB_00458339:
    func_0x0041edb0();
    goto LAB_00458824;
  }
  if (puVar9 != (uint *)0x0) {
    if (*puVar9 >> 8 != 0) {
      if (puVar9 == (uint *)0x0) {
        puVar15 = (uint *)0x0;
      }
      else {
        puVar15 = puVar9 + 1;
      }
      if ((char)*puVar15 != '\0') {
        if (puVar9 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar9 + 1;
        }
        bVar24 = puVar15 == (uint *)&UNK_00c80b0c;
        goto LAB_00457bc7;
      }
    }
    goto LAB_0045802f;
  }
LAB_00458059:
  if (*(int *)param_11 == 0) {
LAB_0045834a:
    if ((puVar9 == (uint *)0x0) || (puVar9 == &uRamfffffffc)) goto LAB_0045837e;
    if (puVar9 == (uint *)0x0) {
      iVar6 = 4;
      bVar24 = true;
      pcVar5 = "fix";
      pcVar19 = (char *)0x0;
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar24 = *pcVar5 == *pcVar19;
        pcVar5 = pcVar5 + 1;
        pcVar19 = pcVar19 + 1;
      } while (bVar24);
    }
    else {
      iVar6 = 4;
      bVar24 = true;
      pcVar5 = "fix";
      puVar15 = puVar9 + 1;
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar24 = *pcVar5 == (char)*puVar15;
        pcVar5 = pcVar5 + 1;
        puVar15 = (uint *)((int)puVar15 + 1);
      } while (bVar24);
    }
LAB_004583bf:
    if ((bVar24) && (iVar6 = *(int *)pbVar23, iVar6 != 0)) {
      if (iVar6 == -4) {
        if ((uRamfffffffc >> 8 == 0) || (DAT_00000000 == '\0')) goto LAB_00458438;
        bVar24 = false;
      }
      else {
        if (iVar6 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar6 + 4);
        }
        iVar6 = 2;
        bVar24 = true;
        pcVar19 = "1";
        do {
          if (iVar6 == 0) break;
          iVar6 = iVar6 + -1;
          bVar24 = *pcVar19 == *pcVar5;
          pcVar19 = pcVar19 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar24);
      }
      if (bVar24) {
        in_stack_000000bc = CONCAT31(in_stack_000000bc._1_3_,1);
        goto LAB_00458824;
      }
    }
LAB_00458438:
    if ((puVar9 == (uint *)0x0) || (puVar9 == &uRamfffffffc)) goto LAB_0045846c;
    if (puVar9 == (uint *)0x0) {
      iVar6 = 3;
      bVar24 = true;
      pcVar5 = "bw";
      pcVar19 = (char *)0x0;
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar24 = *pcVar5 == *pcVar19;
        pcVar5 = pcVar5 + 1;
        pcVar19 = pcVar19 + 1;
      } while (bVar24);
    }
    else {
      iVar6 = 3;
      bVar24 = true;
      pcVar5 = "bw";
      puVar15 = puVar9 + 1;
      do {
        if (iVar6 == 0) break;
        iVar6 = iVar6 + -1;
        bVar24 = *pcVar5 == (char)*puVar15;
        pcVar5 = pcVar5 + 1;
        puVar15 = (uint *)((int)puVar15 + 1);
      } while (bVar24);
    }
LAB_004584b1:
    if ((bVar24) && (iVar6 = *(int *)pbVar23, iVar6 != 0)) {
      if (iVar6 == -4) {
        if ((uRamfffffffc >> 8 == 0) || (DAT_00000000 == '\0')) goto LAB_0045852a;
        bVar24 = false;
      }
      else {
        if (iVar6 == 0) {
          pcVar5 = (char *)0x0;
        }
        else {
          pcVar5 = (char *)(iVar6 + 4);
        }
        iVar6 = 2;
        bVar24 = true;
        pcVar19 = "1";
        do {
          if (iVar6 == 0) break;
          iVar6 = iVar6 + -1;
          bVar24 = *pcVar19 == *pcVar5;
          pcVar19 = pcVar19 + 1;
          pcVar5 = pcVar5 + 1;
        } while (bVar24);
      }
      if (bVar24) {
        in_stack_000000b8 = CONCAT31(in_stack_000000b8._1_3_,1);
        goto LAB_00458824;
      }
    }
LAB_0045852a:
    if ((puVar9 == (uint *)0x0) || (puVar9 == &uRamfffffffc)) goto LAB_00458552;
    if (puVar9 == (uint *)0x0) {
      puVar9 = (uint *)0x0;
    }
    else {
      puVar9 = puVar9 + 1;
    }
    iVar6 = 0xb;
    bVar24 = true;
    pcVar5 = "backuphash";
    do {
      if (iVar6 == 0) break;
      iVar6 = iVar6 + -1;
      bVar24 = *pcVar5 == (char)*puVar9;
      pcVar5 = pcVar5 + 1;
      puVar9 = (uint *)((int)puVar9 + 1);
    } while (bVar24);
  }
  else {
    if (puVar9 != (uint *)0x0) {
      if (*puVar9 >> 8 != 0) {
        if (puVar9 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar9 + 1;
        }
        if ((char)*puVar15 != '\0') {
          if (puVar9 == (uint *)0x0) {
            puVar15 = (uint *)0x0;
          }
          else {
            puVar15 = puVar9 + 1;
          }
          bVar24 = puVar15 == (uint *)&UNK_00c80b14;
          goto LAB_0045809a;
        }
      }
      goto LAB_0045834a;
    }
LAB_0045837e:
    if (*(int *)param_11 == 0) goto LAB_00458438;
    if (puVar9 != (uint *)0x0) {
      if (*puVar9 >> 8 != 0) {
        if (puVar9 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar9 + 1;
        }
        if ((char)*puVar15 != '\0') {
          if (puVar9 == (uint *)0x0) {
            puVar15 = (uint *)0x0;
          }
          else {
            puVar15 = puVar9 + 1;
          }
          bVar24 = puVar15 == (uint *)&UNK_00c81444;
          goto LAB_004583bf;
        }
      }
      goto LAB_00458438;
    }
LAB_0045846c:
    if (*(int *)param_11 == 0) goto LAB_0045852a;
    if (puVar9 != (uint *)0x0) {
      if (*puVar9 >> 8 != 0) {
        if (puVar9 == (uint *)0x0) {
          puVar15 = (uint *)0x0;
        }
        else {
          puVar15 = puVar9 + 1;
        }
        if ((char)*puVar15 != '\0') {
          if (puVar9 == (uint *)0x0) {
            puVar15 = (uint *)0x0;
          }
          else {
            puVar15 = puVar9 + 1;
          }
          bVar24 = puVar15 == (uint *)&UNK_00c8145c;
          goto LAB_004584b1;
        }
      }
      goto LAB_0045852a;
    }
LAB_00458552:
    if (((*(int *)param_11 == 0) || (puVar9 == (uint *)0x0)) || (*puVar9 >> 8 == 0))
    goto LAB_00458824;
    if (puVar9 == (uint *)0x0) {
      puVar15 = (uint *)0x0;
    }
    else {
      puVar15 = puVar9 + 1;
    }
    if ((char)*puVar15 == '\0') goto LAB_00458824;
    if (puVar9 == (uint *)0x0) {
      puVar9 = (uint *)0x0;
    }
    else {
      puVar9 = puVar9 + 1;
    }
    bVar24 = puVar9 == (uint *)&UNK_00c80c6c;
  }
  if (!bVar24) goto LAB_00458824;
  uVar20 = func_0x0049ff60();
  iVar6 = *(int *)(unaff_EBP + 8);
  param_6 = (byte *)(uVar20 & 0xffff);
  in_stack_00000138 = iVar6 + 0x2138;
  in_stack_0000013c = (int *)(iVar6 + 0x2110);
  iVar7 = GetCurrentThreadId();
  if ((*(int *)(iVar6 + 0x2130) == 0) || (*(int *)(iVar6 + 0x2130) != iVar7)) {
    if (*(char *)(iVar6 + 0x211c) == '\0') {
      (**(code **)(*(int *)(iVar6 + 0x2110) + 0x18))();
    }
    else {
      EnterCriticalSection();
    }
    *(undefined4 *)(iVar6 + 0x2134) = 0;
    *(int *)(iVar6 + 0x2130) = iVar7;
  }
  else {
    *(int *)(iVar6 + 0x2134) = *(int *)(iVar6 + 0x2134) + 1;
  }
  if ((*(int *)(iVar6 + 0x2168) == 0) || (uVar20 = *(uint *)(unaff_EBP + 0xc), uVar20 == 0xffffffff)
     ) goto LAB_00458813;
  iVar7 = *(int *)(iVar6 + 0x2168);
  if (uVar20 < *(uint *)(iVar7 + 0x4c) >> 1) {
    if (*(short *)(*(int *)(iVar7 + 0x48) + uVar20 * 2) == (short)param_6) goto LAB_00458813;
    *(short *)(*(int *)(iVar7 + 0x48) + uVar20 * 2) = (short)param_6;
  }
  else {
    pbVar23 = (byte *)(uVar20 + 1);
    param_7 = (byte *)(*(uint *)(iVar7 + 0x4c) >> 1);
    if ((byte *)0x3fffffff < pbVar23) {
      if (*(int *)(iVar7 + 0x48) != 0) {
        func_0x0097caf0();
      }
      *(undefined4 *)(iVar7 + 0x48) = 0;
      *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
      goto LAB_00458813;
    }
    if (pbVar23 == param_7) {
      pbVar8 = *(byte **)(iVar7 + 0x48);
    }
    else if ((*(uint *)(iVar7 + 0x4c) & 1) == 0) {
      if ((uint)((int)pbVar23 * 2) < 0x100000) {
        pbVar13 = (byte *)0x1;
        if (pbVar23 != (byte *)0x0) {
          do {
            pbVar13 = (byte *)((int)pbVar13 * 2);
          } while (pbVar13 <= pbVar23);
        }
      }
      else {
        pbVar13 = (byte *)(((uint)pbVar23 & 0xfffffc00) + 0x400);
      }
      if ((uint)((int)param_7 * 2) < 0x100000) {
        pbVar14 = param_7;
        if ((byte *)0x1 < param_7) {
          in_stack_00000108 = (float)(int)param_7;
          pbVar14 = (byte *)(1 << ((char)((uint)in_stack_00000108 >> 0x17) + 0x81U & 0x1f));
          param_10 = param_7;
          if (pbVar14 < param_7) {
            pbVar14 = (byte *)((int)pbVar14 * 2);
          }
        }
      }
      else {
        pbVar14 = (byte *)(((uint)param_7 & 0x7ffffc00) + 0x400);
      }
      pbVar8 = *(byte **)(iVar7 + 0x48);
      if (pbVar14 != pbVar13) {
        if (pbVar13 == (byte *)0x0) {
          if (pbVar8 != (byte *)0x0) {
            func_0x0097caf0();
            *(undefined4 *)(iVar7 + 0x48) = 0;
          }
        }
        else {
          uVar10 = func_0x0097c810();
          *(undefined4 *)(iVar7 + 0x48) = uVar10;
        }
        pbVar8 = *(byte **)(iVar7 + 0x48);
        if (pbVar8 == (byte *)0x0) {
          *(undefined4 *)(iVar7 + 0x48) = 0;
          *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
          goto LAB_00458813;
        }
      }
      *(uint *)(iVar7 + 0x4c) = (int)pbVar23 * 2 | *(uint *)(iVar7 + 0x4c) & 1;
    }
    else {
      if (pbVar23 == (byte *)0x0) {
        if (*(int *)(iVar7 + 0x48) != 0) {
          func_0x0097caf0();
          *(undefined4 *)(iVar7 + 0x48) = 0;
        }
      }
      else {
        uVar10 = func_0x0097c810();
        *(undefined4 *)(iVar7 + 0x48) = uVar10;
      }
      pbVar8 = *(byte **)(iVar7 + 0x48);
      param_10 = pbVar8;
      if (pbVar8 == (byte *)0x0) {
        *(undefined4 *)(iVar7 + 0x48) = 0;
        *(uint *)(iVar7 + 0x4c) = *(uint *)(iVar7 + 0x4c) & 1;
        goto LAB_00458813;
      }
      *(uint *)(iVar7 + 0x4c) = (int)pbVar23 * 2 | *(uint *)(iVar7 + 0x4c) & 1;
    }
    pbVar13 = param_7;
    if (pbVar8 == (byte *)0x0) goto LAB_00458813;
    for (; pbVar13 < pbVar23; pbVar13 = pbVar13 + 1) {
      *(undefined2 *)(*(int *)(iVar7 + 0x48) + (int)pbVar13 * 2) = *(undefined2 *)(iVar6 + 0x216c);
    }
    *(short *)(*(int *)(*(int *)(iVar6 + 0x2168) + 0x48) + *(int *)(unaff_EBP + 0xc) * 2) =
         (short)param_6;
  }
  func_0x006a2a60();
LAB_00458813:
  func_0x0041edb0();
  param_18._0_1_ = '\x01';
  goto LAB_00458824;
}



