// Address: 0068acbb
// Function: FUN_0068acbb

/* WARNING: Restarted to delay deadcode elimination for space: stack */

void __fastcall FUN_0068acbb(byte param_1,undefined2 param_2)

{
  byte *pbVar1;
  undefined1 uVar2;
  int iVar3;
  byte *pbVar4;
  char cVar5;
  uint *in_EAX;
  char *pcVar6;
  int *piVar7;
  byte **ppbVar8;
  uint uVar9;
  undefined *puVar10;
  undefined *puVar11;
  int unaff_EBX;
  int iVar12;
  code *pcVar13;
  undefined4 *unaff_EBP;
  undefined1 *unaff_EDI;
  byte *pbStack00000014;
  undefined4 in_stack_00000020;
  undefined4 in_stack_00000024;
  undefined4 in_stack_00000028;
  byte *in_stack_00000034;
  int in_stack_00000040;
  byte *in_stack_000001f0;
  byte *in_stack_000003f8;
  byte *in_stack_00000600;
  byte *in_stack_00000808;
  undefined4 in_stack_00000a3c;
  int *in_stack_00000a48;
  byte *in_stack_00000a80;
  undefined1 *puVar14;
  byte *pbStack_2c;
  undefined4 uStack_28;
  byte **ppbStack_24;
  byte **ppbStack_20;
  uint *puStack_1c;
  byte *pbStack_18;
  undefined4 *puStack_14;
  byte *pbStack_10;
  undefined *puStack_c;
  byte *pbStack_8;
  byte *pbStack_4;
  
  uVar2 = in(param_2);
  *unaff_EDI = uVar2;
  *(char *)(unaff_EBX + -0x75151709) = *(char *)(unaff_EBX + -0x75151709) + (param_1 | (byte)in_EAX)
  ;
  *in_EAX = *in_EAX ^ (uint)in_EAX;
  if (in_stack_00000040 == 0) {
    pbStack_4 = (byte *)0x0;
  }
  else {
    pbStack_4 = (byte *)(in_stack_00000040 + 4);
  }
  pbStack00000014 = (byte *)0x0;
  pcVar6 = (char *)pbStack_4;
  if (pbStack_4 != (byte *)0x0) {
    do {
      cVar5 = *pcVar6;
      pcVar6 = pcVar6 + 1;
    } while (cVar5 != '\0');
    pbStack_8 = &UNK_0068acfc;
    func_0x00985ff0();
  }
  pbVar1 = pbStack00000014;
  if ((byte *)unaff_EBP[1] != pbStack00000014) {
    pbStack_4 = &UNK_0068ad0b;
    func_0x00401000();
    unaff_EBP[1] = pbVar1;
    if (pbVar1 != (byte *)0x0) {
      if (*pbVar1 < 0x80) {
        pbStack_8 = &UNK_0068ad23;
        pbStack_4 = pbVar1;
        cVar5 = InterlockedIncrement();
        if (cVar5 != -1) goto code_r0x0068ad36;
      }
      pbStack_4 = &UNK_0068ad36;
      func_0x00985a60();
    }
  }
code_r0x0068ad36:
  pbStack_4 = &UNK_0068ad3f;
  func_0x00401000();
  pbVar4 = in_stack_00000034;
  in_stack_00000024 = 0;
  in_stack_00000020 = 0;
  pbStack00000014 = (byte *)0x0;
  in_stack_00000028 = 0;
  pbVar1 = in_stack_00000034 + 0x48;
  pbStack_4 = (byte *)&stack0x00000024;
  puStack_c = &UNK_0068ad6f;
  pbStack_8 = in_stack_00000a80;
  (**(code **)(*(int *)(in_stack_00000034 + 0x48) + 0x18))();
  puStack_c = &stack0x00000018;
  puStack_14 = (undefined4 *)&UNK_0068ad7e;
  pbStack_10 = in_stack_00000a80;
  (**(code **)(*(int *)pbVar1 + 0x1c))();
  puStack_14 = unaff_EBP + 2;
  puStack_1c = (uint *)&UNK_0068ad8c;
  pbStack_18 = in_stack_00000a80;
  (**(code **)(*(int *)pbVar1 + 0x14))();
  puStack_1c = (uint *)&stack0x00000010;
  ppbStack_24 = (byte **)&UNK_0068ad9b;
  (**(code **)(*(int *)pbVar1 + 0x24))();
  ppbStack_24 = &pbStack_8;
  pbStack_2c = pbVar4;
  func_0x0044ddd0();
  piVar7 = (int *)func_0x00453c00();
  if (*piVar7 != 0) {
    func_0x00401000();
    ppbStack_24 = (byte **)*piVar7;
    if ((ppbStack_24 != (byte **)0x0) &&
       ((0x7f < *(byte *)ppbStack_24 || (cVar5 = InterlockedIncrement(ppbStack_24), cVar5 == -1))))
    {
      func_0x00985a60();
    }
  }
  func_0x00401000();
  if (ppbStack_24 == (byte **)0x0) {
    ppbStack_20 = (byte **)0x0;
  }
  else {
    ppbStack_20 = ppbStack_24 + 1;
  }
  puVar14 = (undefined1 *)register0x00000010;
  (**(code **)(*(int *)pbVar1 + 0x20))();
  puStack_14 = (undefined4 *)0x0;
  func_0x00985ff0();
  if ((byte *)*unaff_EBP != pbStack_18) {
    func_0x00401000();
    *unaff_EBP = pbStack_18;
    if ((pbStack_18 != (byte *)0x0) &&
       ((0x7f < *pbStack_18 || (cVar5 = InterlockedIncrement(), cVar5 == -1)))) {
      func_0x00985a60();
    }
  }
  func_0x00401000();
  if (ppbStack_20 == (byte **)0x0) {
    ppbVar8 = (byte **)0x0;
  }
  else {
    ppbVar8 = ppbStack_20 + 1;
  }
  func_0x0040ea90(&UNK_00ca7810,ppbVar8);
  if (((ppbStack_24 != (byte **)0x0) && (((uint)*ppbStack_24 & 0xffffff00) != 0)) &&
     (*(byte *)(ppbStack_24 + 1) != 0)) {
    func_0x0040ea90(&UNK_00ca781c,ppbStack_24 + 1);
  }
  if (((puStack_1c != (uint *)0x0) && ((*puStack_1c & 0xffffff00) != 0)) &&
     ((char)puStack_1c[1] != '\0')) {
    func_0x0040ea90(&UNK_00ca7830,puStack_1c + 1);
  }
  func_0x0040ea90(&UNK_00ca7840,pbStack_2c);
  func_0x0040ea90(&UNK_00ca7850,CONCAT44(pbStack_8,puStack_c));
  pbStack_2c = (byte *)0x0;
  uStack_28 = 0;
  pbStack_18 = (byte *)0x0;
  puStack_14 = (undefined4 *)0x0;
  func_0x006a3b80(pbStack_10 + 0x988,&UNK_00ca785c,in_stack_00000a3c,&pbStack_2c,&pbStack_18);
  uVar9 = (uint)puVar14 >> 1;
  if (uVar9 != 0) {
    iVar12 = (int)pbStack_2c - (int)in_stack_00000a48;
    piVar7 = in_stack_00000a48;
    do {
      iVar3 = *(int *)(iVar12 + (int)piVar7);
      puVar11 = (undefined *)(iVar3 + 4);
      if (iVar3 == 0) {
        puVar11 = &UNK_00c7f979;
      }
      if (*piVar7 == 0) {
        puVar10 = &UNK_00c7f979;
      }
      else {
        puVar10 = (undefined *)(*piVar7 + 4);
      }
      func_0x0040ea90(&UNK_00ca77e8,puVar10,puVar11);
      piVar7 = piVar7 + 1;
      uVar9 = uVar9 - 1;
    } while (uVar9 != 0);
  }
  if (pbStack_2c != (byte *)0x0) {
    pbVar1 = pbStack_2c + -4;
    func_0x00401110(4,&UNK_005bd380);
    func_0x0097caf0(pbVar1);
  }
  if (in_stack_00000a48 != (int *)0x0) {
    func_0x00401110(4,&UNK_005bd380);
    func_0x0097caf0(in_stack_00000a48 + -1);
  }
  pcVar13 = InterlockedIncrement_exref;
  if (bRam00000001 < 0x80) {
    cVar5 = InterlockedDecrement(1);
    pcVar13 = InterlockedIncrement_exref;
    if (cVar5 == '\x7f') {
      if (bRam00000001 < 0x80) {
        cVar5 = InterlockedIncrement(1);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(1);
    }
  }
  if (UNK_00ca77f0 < 0x80) {
    cVar5 = InterlockedDecrement(&UNK_00ca77f0);
    if (cVar5 == '\x7f') {
      if (UNK_00ca77f0 < 0x80) {
        cVar5 = (*pcVar13)(&UNK_00ca77f0);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(&UNK_00ca77f0);
    }
  }
  if ((pbVar4 != (byte *)0x0) && (*pbVar4 < 0x80)) {
    cVar5 = InterlockedDecrement(pbVar4);
    if (cVar5 == '\x7f') {
      if (*pbVar4 < 0x80) {
        cVar5 = (*pcVar13)(pbVar4);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(pbVar4);
    }
  }
  if ((&puStack_14 != (undefined4 **)0x0) && ((byte)puStack_14 < 0x80)) {
    cVar5 = InterlockedDecrement(&puStack_14);
    if (cVar5 == '\x7f') {
      if ((byte)puStack_14 < 0x80) {
        cVar5 = (*pcVar13)(&puStack_14);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(&puStack_14);
    }
  }
  if ((in_stack_00000808 != (byte *)0x0) && (*in_stack_00000808 < 0x80)) {
    cVar5 = InterlockedDecrement(in_stack_00000808);
    if (cVar5 == '\x7f') {
      if (*in_stack_00000808 < 0x80) {
        cVar5 = (*pcVar13)(in_stack_00000808);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(in_stack_00000808);
    }
  }
  if ((in_stack_00000600 != (byte *)0x0) && (*in_stack_00000600 < 0x80)) {
    cVar5 = InterlockedDecrement(in_stack_00000600);
    if (cVar5 == '\x7f') {
      if (*in_stack_00000600 < 0x80) {
        cVar5 = (*pcVar13)(in_stack_00000600);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(in_stack_00000600);
    }
  }
  if ((in_stack_000003f8 != (byte *)0x0) && (*in_stack_000003f8 < 0x80)) {
    cVar5 = InterlockedDecrement(in_stack_000003f8);
    if (cVar5 == '\x7f') {
      if (*in_stack_000003f8 < 0x80) {
        cVar5 = (*pcVar13)(in_stack_000003f8);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(in_stack_000003f8);
    }
  }
  pbVar1 = in_stack_000001f0;
  if ((in_stack_000001f0 != (byte *)0x0) && (*in_stack_000001f0 < 0x80)) {
    cVar5 = InterlockedDecrement(in_stack_000001f0);
    if (cVar5 == '\x7f') {
      if (*pbVar1 < 0x80) {
        cVar5 = (*pcVar13)(pbVar1);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(in_stack_000001f0);
    }
  }
  pbVar1 = pbStack_18;
  in_stack_000001f0 = (byte *)0x0;
  if ((pbStack_18 != (byte *)0x0) && (*pbStack_18 < 0x80)) {
    cVar5 = InterlockedDecrement(pbStack_18);
    if (cVar5 == '\x7f') {
      if (*pbVar1 < 0x80) {
        cVar5 = (*pcVar13)(pbVar1);
      }
      else {
        cVar5 = -1;
      }
    }
    if (cVar5 == '\0') {
      func_0x0097caf0(pbStack_18);
    }
  }
  func_0x00bef10a();
  return;
}


