// Address: 005e2e83
// Function: FUN_005e2e83
// Target requested: 0x005e2e83

/* WARNING (jumptable): Unable to track spacebase fully for stack */

undefined4 FUN_005e2e83(void)

{
  char cVar1;
  undefined4 uVar2;
  uint uVar3;
  int iVar4;
  char *pcVar5;
  int *unaff_EBX;
  byte *pbVar6;
  uint *puVar7;
  bool bVar8;
  undefined4 in_stack_00000020;
  int in_stack_00000030;
  uint *in_stack_00000034;
  byte *in_stack_00000050;
  int in_stack_00000054;
  char in_stack_00000058;
  
  uVar2 = TrackPopupMenu();
  func_0x00a6b060();
  unaff_EBX[0xd29] = unaff_EBX[0xd29] + -1;
  switch(uVar2) {
  case 0x9dfc:
    func_0x005e0750();
    func_0x0097a090();
    if (in_stack_00000020._1_1_ == '\0') {
      bVar8 = 0xfffffffe < uRam00d35a18;
      uRam00d35a18 = uRam00d35a18 + 1;
      iRam00d35a1c = iRam00d35a1c + (uint)bVar8;
    }
    else {
      bVar8 = 0xfffffffe < uRam00d35a38;
      uRam00d35a38 = uRam00d35a38 + 1;
      iRam00d35a3c = iRam00d35a3c + (uint)bVar8;
    }
    break;
  case 0x9dfd:
    func_0x004aa300();
    func_0x00444ee0();
    func_0x00401000();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35a98;
    uRam00d35a98 = uRam00d35a98 + 1;
    iRam00d35a9c = iRam00d35a9c + (uint)bVar8;
    break;
  case 0x9dfe:
    func_0x004aa300();
    func_0x00444ee0();
    func_0x00401000();
    in_stack_00000058 = '\0';
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35a58;
    uRam00d35a58 = uRam00d35a58 + 1;
    iRam00d35a5c = iRam00d35a5c + (uint)bVar8;
    break;
  default:
    goto LAB_005e3451;
  case 0x9e01:
    func_0x005a0e90();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35b38;
    uRam00d35b38 = uRam00d35b38 + 1;
    iRam00d35b3c = iRam00d35b3c + (uint)bVar8;
    break;
  case 0x9e02:
    func_0x005a0e90();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35b58;
    uRam00d35b58 = uRam00d35b58 + 1;
    iRam00d35b5c = iRam00d35b5c + (uint)bVar8;
    break;
  case 0x9e03:
    func_0x005e0ef0();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35bb8;
    uRam00d35bb8 = uRam00d35bb8 + 1;
    iRam00d35bbc = iRam00d35bbc + (uint)bVar8;
    break;
  case 0x9e04:
    func_0x005a0100();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35bd8;
    uRam00d35bd8 = uRam00d35bd8 + 1;
    iRam00d35bdc = iRam00d35bdc + (uint)bVar8;
    break;
  case 0x9e06:
    func_0x009ae560();
    (**(code **)(*unaff_EBX + 0x24))();
    func_0x009ae560();
    func_0x009ae560();
    cVar1 = func_0x009bac20();
    if ((cVar1 != '\0') &&
       (iVar4 = (**(code **)(*(int *)(unaff_EBX[0xaf] + 0x48) + 0x8c))(), iVar4 == 0)) {
      func_0x004a0410();
      func_0x005a0790();
      func_0x004a0520();
    }
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35c38;
    uRam00d35c38 = uRam00d35c38 + 1;
    iRam00d35c3c = iRam00d35c3c + (uint)bVar8;
    break;
  case 0x9e08:
    if ((DAT_00d67849 == '\0') || (uVar3 = GetAsyncKeyState(), (uVar3 >> 0xf & 1) == 0)) {
      func_0x005a0f60();
      func_0x0097a090();
      bVar8 = 0xfffffffe < uRam00d35bf8;
      uRam00d35bf8 = uRam00d35bf8 + 1;
      iRam00d35bfc = iRam00d35bfc + (uint)bVar8;
    }
    else {
      func_0x005a10c0();
      func_0x0097a090();
      bVar8 = 0xfffffffe < uRam00d35c18;
      uRam00d35c18 = uRam00d35c18 + 1;
      iRam00d35c1c = iRam00d35c1c + (uint)bVar8;
    }
    break;
  case 0x9e0a:
    func_0x004aa300();
    func_0x00444ee0();
    func_0x00401000();
    in_stack_00000054 = 0;
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35ab8;
    uRam00d35ab8 = uRam00d35ab8 + 1;
    iRam00d35abc = iRam00d35abc + (uint)bVar8;
    break;
  case 0x9e0d:
    if (in_stack_00000034 == (uint *)0x0) {
code_r0x005e3120:
      pcVar5 = "]star";
    }
    else {
      if (in_stack_00000034 + 1 == (uint *)0x0) {
        if (((*in_stack_00000034 & 0xffffff00) == 0) || (DAT_00000000 == '\0'))
        goto code_r0x005e3120;
        bVar8 = false;
      }
      else {
        iVar4 = 6;
        bVar8 = true;
        pbVar6 = &UNK_00c811d4;
        puVar7 = in_stack_00000034 + 1;
        do {
          if (iVar4 == 0) break;
          iVar4 = iVar4 + -1;
          bVar8 = *pbVar6 == (byte)*puVar7;
          pbVar6 = pbVar6 + 1;
          puVar7 = (uint *)((int)puVar7 + 1);
        } while (bVar8);
      }
      pcVar5 = "";
      if (!bVar8) goto code_r0x005e3120;
    }
    if (pcVar5 != (char *)0x0) {
      do {
        cVar1 = *pcVar5;
        pcVar5 = pcVar5 + 1;
      } while (cVar1 != '\0');
      func_0x00985ff0();
    }
    func_0x004aa300();
    func_0x00444ee0();
    func_0x00401000();
    in_stack_00000050 = (byte *)0x0;
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35af8;
    uRam00d35af8 = uRam00d35af8 + 1;
    iRam00d35afc = iRam00d35afc + (uint)bVar8;
    func_0x0097a100();
    func_0x00401000();
    goto LAB_005e3451;
  case 0x9e0f:
    func_0x004aa300();
    func_0x00444ee0();
    func_0x00401000();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35b18;
    uRam00d35b18 = uRam00d35b18 + 1;
    iRam00d35b1c = iRam00d35b1c + (uint)bVar8;
    break;
  case 0x9e13:
    func_0x004aa300();
    func_0x00444ee0();
    func_0x00401000();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35ad8;
    uRam00d35ad8 = uRam00d35ad8 + 1;
    iRam00d35adc = iRam00d35adc + (uint)bVar8;
    break;
  case 0x9e14:
    func_0x004aa300();
    func_0x00444ee0();
    func_0x00401000();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35a78;
    uRam00d35a78 = uRam00d35a78 + 1;
    iRam00d35a7c = iRam00d35a7c + (uint)bVar8;
    break;
  case 0x9e1a:
    func_0x005a0e90();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35b78;
    uRam00d35b78 = uRam00d35b78 + 1;
    iRam00d35b7c = iRam00d35b7c + (uint)bVar8;
    break;
  case 0x9e1b:
    func_0x005a0e90();
    func_0x0097a090();
    bVar8 = 0xfffffffe < uRam00d35b98;
    uRam00d35b98 = uRam00d35b98 + 1;
    iRam00d35b9c = iRam00d35b9c + (uint)bVar8;
  }
  func_0x0097a100();
LAB_005e3451:
  if ((in_stack_00000034 != (uint *)0x0) && ((byte)*in_stack_00000034 < 0x80)) {
    cVar1 = InterlockedDecrement();
    if (cVar1 == '\x7f') {
      if ((byte)*in_stack_00000034 < 0x80) {
        cVar1 = InterlockedIncrement();
      }
      else {
        cVar1 = -1;
      }
    }
    if (cVar1 == '\0') {
      func_0x0097caf0();
    }
  }
  if ((in_stack_00000050 != (byte *)0x0) && (*in_stack_00000050 < 0x80)) {
    cVar1 = InterlockedDecrement();
    if (cVar1 == '\x7f') {
      if (*in_stack_00000050 < 0x80) {
        cVar1 = InterlockedIncrement();
      }
      else {
        cVar1 = -1;
      }
    }
    if (cVar1 == '\0') {
      func_0x0097caf0();
    }
  }
  func_0x004a0520();
  func_0x00413490();
  if (in_stack_00000030 != 0) {
    (**(code **)(*(int *)(in_stack_00000030 + 4) + 8))();
  }
  if ((in_stack_00000058 != '\0') && (in_stack_00000054 != 0)) {
    DestroyMenu();
  }
  func_0x00401000();
  return 0;
}


