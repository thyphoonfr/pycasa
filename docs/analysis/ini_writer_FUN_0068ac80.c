// Address: 0068ac80
// Function: FUN_0068ac80
// Target requested: 0x0068AC80

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */
/* WARNING: Restarted to delay deadcode elimination for space: stack */

void FUN_0068ac80(undefined4 *param_1,byte *param_2,byte *param_3)

{
  byte *pbVar1;
  int iVar2;
  byte *pbVar3;
  char cVar4;
  char *pcVar5;
  int *piVar6;
  byte **ppbVar7;
  uint uVar8;
  undefined *puVar9;
  undefined *puVar10;
  int iVar11;
  code *pcVar12;
  undefined1 *puVar13;
  byte *pbStack_aa0;
  byte *pbStack_a9c;
  byte **ppbStack_a98;
  byte **ppbStack_a94;
  uint *puStack_a90;
  byte *pbStack_a8c;
  undefined4 *puStack_a88;
  byte *pbStack_a84;
  undefined1 *puStack_a80;
  byte *pbStack_a7c;
  byte *pbStack_a78;
  uint uStack_a64;
  byte *pbStack_a60;
  undefined1 auStack_a5c [8];
  undefined4 uStack_a54;
  undefined4 uStack_a50;
  undefined4 uStack_a4c;
  byte *pbStack_a40;
  int iStack_a34;
  byte *pbStack_884;
  byte *pbStack_67c;
  byte *pbStack_474;
  byte *pbStack_26c;
  undefined4 uStack_38;
  int *piStack_2c;
  uint uStack_8;
  
  uStack_8 = _DAT_00d24004 ^ (uint)&uStack_a64;
  pbStack_a40 = param_2;
  pbStack_a78 = (byte *)0x68acba;
  func_0x00408b50();
  pbStack_a78 = (byte *)0x68acc6;
  func_0x009a37b0();
  if (iStack_a34 == 0) {
    pbStack_a78 = (byte *)0x0;
  }
  else {
    pbStack_a78 = (byte *)(iStack_a34 + 4);
  }
  pbStack_a60 = (byte *)0x0;
  pcVar5 = (char *)pbStack_a78;
  if (pbStack_a78 != (byte *)0x0) {
    do {
      cVar4 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar4 != '\0');
    pbStack_a7c = (byte *)0x68acfc;
    func_0x00985ff0();
  }
  pbVar1 = pbStack_a60;
  if ((byte *)param_1[1] != pbStack_a60) {
    pbStack_a78 = (byte *)0x68ad0b;
    func_0x00401000();
    param_1[1] = pbVar1;
    if (pbVar1 != (byte *)0x0) {
      if (*pbVar1 < 0x80) {
        pbStack_a7c = (byte *)0x68ad23;
        pbStack_a78 = pbVar1;
        cVar4 = InterlockedIncrement();
        if (cVar4 != -1) goto LAB_0068ad36;
      }
      pbStack_a78 = (byte *)0x68ad36;
      func_0x00985a60();
    }
  }
LAB_0068ad36:
  pbStack_a78 = (byte *)0x68ad3f;
  func_0x00401000();
  pbVar3 = pbStack_a40;
  uStack_a50 = 0;
  uStack_a54 = 0;
  pbStack_a60 = (byte *)0x0;
  uStack_a4c = 0;
  pbVar1 = pbStack_a40 + 0x48;
  pbStack_a78 = (byte *)&uStack_a50;
  pbStack_a7c = param_3;
  puStack_a80 = (undefined1 *)0x68ad6f;
  (**(code **)(*(int *)(pbStack_a40 + 0x48) + 0x18))();
  puStack_a80 = auStack_a5c;
  pbStack_a84 = param_3;
  puStack_a88 = (undefined4 *)0x68ad7e;
  (**(code **)(*(int *)pbVar1 + 0x1c))();
  puStack_a88 = param_1 + 2;
  pbStack_a8c = param_3;
  puStack_a90 = (uint *)0x68ad8c;
  (**(code **)(*(int *)pbVar1 + 0x14))();
  puStack_a90 = &uStack_a64;
  ppbStack_a94 = (byte **)param_3;
  ppbStack_a98 = (byte **)0x68ad9b;
  (**(code **)(*(int *)pbVar1 + 0x24))();
  ppbStack_a98 = &pbStack_a7c;
  pbStack_a9c = param_3;
  pbStack_aa0 = pbVar3;
  func_0x0044ddd0();
  piVar6 = (int *)func_0x00453c00();
  if (*piVar6 != 0) {
    func_0x00401000();
    ppbStack_a98 = (byte **)*piVar6;
    if ((ppbStack_a98 != (byte **)0x0) &&
       ((0x7f < *(byte *)ppbStack_a98 || (cVar4 = InterlockedIncrement(ppbStack_a98), cVar4 == -1)))
       ) {
      func_0x00985a60();
    }
  }
  func_0x00401000();
  if (ppbStack_a98 == (byte **)0x0) {
    ppbStack_a94 = (byte **)0x0;
  }
  else {
    ppbStack_a94 = ppbStack_a98 + 1;
  }
  puVar13 = &stack0xfffff58c;
  (**(code **)(*(int *)pbVar1 + 0x20))();
  puStack_a88 = (undefined4 *)0x0;
  func_0x00985ff0();
  pbVar1 = pbStack_a8c;
  if ((byte *)*param_1 != pbStack_a8c) {
    func_0x00401000();
    *param_1 = pbVar1;
    if ((pbVar1 != (byte *)0x0) &&
       ((0x7f < *pbVar1 || (cVar4 = InterlockedIncrement(), cVar4 == -1)))) {
      func_0x00985a60();
    }
  }
  func_0x00401000();
  if (ppbStack_a94 == (byte **)0x0) {
    ppbVar7 = (byte **)0x0;
  }
  else {
    ppbVar7 = ppbStack_a94 + 1;
  }
  func_0x0040ea90(&UNK_00ca7810,ppbVar7);
  if (((ppbStack_a98 != (byte **)0x0) && (((uint)*ppbStack_a98 & 0xffffff00) != 0)) &&
     (*(byte *)(ppbStack_a98 + 1) != 0)) {
    func_0x0040ea90(&UNK_00ca781c,ppbStack_a98 + 1);
  }
  if (((puStack_a90 != (uint *)0x0) && ((*puStack_a90 & 0xffffff00) != 0)) &&
     ((char)puStack_a90[1] != '\0')) {
    func_0x0040ea90(&UNK_00ca7830,puStack_a90 + 1);
  }
  func_0x0040ea90(&UNK_00ca7840,pbStack_aa0);
  func_0x0040ea90(&UNK_00ca7850,CONCAT44(pbStack_a7c,puStack_a80));
  pbStack_aa0 = (byte *)0x0;
  pbStack_a9c = (byte *)0x0;
  pbStack_a8c = (byte *)0x0;
  puStack_a88 = (undefined4 *)0x0;
  func_0x006a3b80(pbStack_a84 + 0x988,&UNK_00ca785c,uStack_38,&pbStack_aa0,&pbStack_a8c);
  uVar8 = (uint)puVar13 >> 1;
  if (uVar8 != 0) {
    iVar11 = (int)pbStack_aa0 - (int)piStack_2c;
    piVar6 = piStack_2c;
    do {
      iVar2 = *(int *)(iVar11 + (int)piVar6);
      puVar10 = (undefined *)(iVar2 + 4);
      if (iVar2 == 0) {
        puVar10 = &UNK_00c7f979;
      }
      if (*piVar6 == 0) {
        puVar9 = &UNK_00c7f979;
      }
      else {
        puVar9 = (undefined *)(*piVar6 + 4);
      }
      func_0x0040ea90(&UNK_00ca77e8,puVar9,puVar10);
      piVar6 = piVar6 + 1;
      uVar8 = uVar8 - 1;
    } while (uVar8 != 0);
  }
  if (pbStack_aa0 != (byte *)0x0) {
    pbVar1 = pbStack_aa0 + -4;
    func_0x00401110(4,&UNK_005bd380);
    func_0x0097caf0(pbVar1);
  }
  if (piStack_2c != (int *)0x0) {
    func_0x00401110(4,&UNK_005bd380);
    func_0x0097caf0(piStack_2c + -1);
  }
  pcVar12 = InterlockedIncrement_exref;
  if (bRam00000001 < 0x80) {
    cVar4 = InterlockedDecrement(1);
    pcVar12 = InterlockedIncrement_exref;
    if (cVar4 == '\x7f') {
      if (bRam00000001 < 0x80) {
        cVar4 = InterlockedIncrement(1);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(1);
    }
  }
  if (UNK_00ca77f0 < 0x80) {
    cVar4 = InterlockedDecrement(&UNK_00ca77f0);
    if (cVar4 == '\x7f') {
      if (UNK_00ca77f0 < 0x80) {
        cVar4 = (*pcVar12)(&UNK_00ca77f0);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(&UNK_00ca77f0);
    }
  }
  if ((pbVar3 != (byte *)0x0) && (*pbVar3 < 0x80)) {
    cVar4 = InterlockedDecrement(pbVar3);
    if (cVar4 == '\x7f') {
      if (*pbVar3 < 0x80) {
        cVar4 = (*pcVar12)(pbVar3);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(pbVar3);
    }
  }
  if ((&puStack_a88 != (undefined4 **)0x0) && ((byte)puStack_a88 < 0x80)) {
    cVar4 = InterlockedDecrement(&puStack_a88);
    if (cVar4 == '\x7f') {
      if ((byte)puStack_a88 < 0x80) {
        cVar4 = (*pcVar12)(&puStack_a88);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(&puStack_a88);
    }
  }
  pbVar1 = pbStack_26c;
  if ((pbStack_26c != (byte *)0x0) && (*pbStack_26c < 0x80)) {
    cVar4 = InterlockedDecrement(pbStack_26c);
    if (cVar4 == '\x7f') {
      if (*pbVar1 < 0x80) {
        cVar4 = (*pcVar12)(pbVar1);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(pbStack_26c);
    }
  }
  pbVar1 = pbStack_474;
  pbStack_26c = (byte *)0x0;
  if ((pbStack_474 != (byte *)0x0) && (*pbStack_474 < 0x80)) {
    cVar4 = InterlockedDecrement(pbStack_474);
    if (cVar4 == '\x7f') {
      if (*pbVar1 < 0x80) {
        cVar4 = (*pcVar12)(pbVar1);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(pbStack_474);
    }
  }
  pbVar1 = pbStack_67c;
  pbStack_474 = (byte *)0x0;
  if ((pbStack_67c != (byte *)0x0) && (*pbStack_67c < 0x80)) {
    cVar4 = InterlockedDecrement(pbStack_67c);
    if (cVar4 == '\x7f') {
      if (*pbVar1 < 0x80) {
        cVar4 = (*pcVar12)(pbVar1);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(pbStack_67c);
    }
  }
  pbVar1 = pbStack_884;
  pbStack_67c = (byte *)0x0;
  if ((pbStack_884 != (byte *)0x0) && (*pbStack_884 < 0x80)) {
    cVar4 = InterlockedDecrement(pbStack_884);
    if (cVar4 == '\x7f') {
      if (*pbVar1 < 0x80) {
        cVar4 = (*pcVar12)(pbVar1);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(pbStack_884);
    }
  }
  pbVar1 = pbStack_a8c;
  pbStack_884 = (byte *)0x0;
  if ((pbStack_a8c != (byte *)0x0) && (*pbStack_a8c < 0x80)) {
    cVar4 = InterlockedDecrement(pbStack_a8c);
    if (cVar4 == '\x7f') {
      if (*pbVar1 < 0x80) {
        cVar4 = (*pcVar12)(pbVar1);
      }
      else {
        cVar4 = -1;
      }
    }
    if (cVar4 == '\0') {
      func_0x0097caf0(pbStack_a8c);
    }
  }
  func_0x00bef10a();
  return;
}


