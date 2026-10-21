// Address: 00738d00
// Function: FUN_00738d00
// Target requested: 0x00738D00

/* WARNING: Removing unreachable block (ram,0x00739368) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __fastcall FUN_00738d00(undefined4 param_1,undefined4 param_2)

{
  byte *pbVar1;
  bool bVar2;
  uint uVar3;
  char cVar4;
  char cVar5;
  int in_EAX;
  uint uVar6;
  int iVar7;
  uint *puVar8;
  undefined4 *puVar9;
  uint *puVar10;
  undefined4 uVar11;
  byte bVar12;
  uint *unaff_EBX;
  int *unaff_EBP;
  byte bStack_59;
  
  pbVar1 = (byte *)(CONCAT31((int3)((uint)(in_EAX + 0x468d00c4) >> 8),
                             (char)(in_EAX + 0x468d00c4) + -0x15) + -0x73);
  bVar12 = *pbVar1;
  *pbVar1 = bVar12 << 2 |
            (byte)(CONCAT11(CARRY1((byte)((uint)param_2 >> 8),(byte)*unaff_EBX),bVar12) >> 7);
  func_0x00985af0();
  func_0x00407630();
  uVar6 = func_0x004078e0();
  func_0x004089e0();
  cVar4 = func_0x00994290();
  func_0x00408c00();
  bVar12 = (byte)unaff_EBX;
  if ((cVar4 == '\0') != (bool)bVar12) {
    func_0x00407760();
  }
  func_0x004078e0();
  func_0x004082f0();
  func_0x0073b500();
  func_0x00407a20();
  func_0x00985ff0();
  func_0x00407630();
  func_0x00401000();
  func_0x00407a20();
  func_0x004019b0();
  func_0x00401000();
  func_0x00401000();
  bVar2 = false;
  func_0x00407a20();
  func_0x004019b0();
  func_0x00401000();
  func_0x00401000();
  func_0x00407a20();
  func_0x004019b0();
  func_0x00401000();
  func_0x00401000();
  puVar10 = *(uint **)(unaff_EBP[0x32] + 4);
  if ((puVar10 != unaff_EBX) && ((byte)*puVar10 < 0x80)) {
    InterlockedIncrement();
  }
  func_0x009958c0();
  if ((_DAT_00d6fc64 & 1) == 0) {
    _DAT_00d6fc64 = _DAT_00d6fc64 | 1;
    GetModuleHandleA();
    iVar7 = GetProcAddress();
    DAT_00d6fc60 = iVar7 != 0;
  }
  if (DAT_00d6fc60 != bVar12) {
    bVar2 = true;
    func_0x00407a20();
    iVar7 = func_0x004019b0();
    bStack_59 = 1;
    if (iVar7 != 0) goto LAB_00738f71;
  }
  bStack_59 = bVar12;
LAB_00738f71:
  if (bVar2) {
    func_0x00401000();
    func_0x00401000();
  }
  if (bStack_59 != bVar12) {
    if (*(uint **)(unaff_EBP[0x32] + 8) == unaff_EBX) {
      puVar8 = (uint *)0x0;
    }
    else {
      puVar8 = *(uint **)(unaff_EBP[0x32] + 8) + 1;
    }
    if (puVar8 != unaff_EBX) {
      do {
        uVar3 = *puVar8;
        puVar8 = (uint *)((int)puVar8 + 1);
      } while ((byte)uVar3 != bVar12);
      func_0x00985ff0();
    }
    if (((puVar10 != (uint *)0x0) && (func_0x00401000(), unaff_EBX != (uint *)0x0)) &&
       ((0x7f < DAT_00000000 || (cVar5 = InterlockedIncrement(), cVar5 == -1)))) {
      func_0x00985a60();
    }
    func_0x00401000();
    func_0x006e0410();
    func_0x00985af0();
  }
  func_0x00985ff0();
  puVar9 = (undefined4 *)func_0x0052e590();
  if ((uint *)*puVar9 != unaff_EBX) {
    (*(code *)**(undefined4 **)*puVar9)();
  }
  puVar10 = (uint *)func_0x00c0769f();
  if (puVar10 == unaff_EBX) {
    puVar10 = (uint *)0x0;
  }
  else {
    *puVar10 = (uint)&UNK_00c7f790;
    puVar10[1] = ~(uVar6 >> 0x1f) & 1;
  }
  *puVar9 = puVar10;
  func_0x00401000();
  func_0x00985ff0();
  puVar9 = (undefined4 *)func_0x0052e590();
  if ((uint *)*puVar9 != unaff_EBX) {
    (*(code *)**(undefined4 **)*puVar9)();
  }
  puVar10 = (uint *)func_0x00c0769f();
  if (puVar10 == unaff_EBX) {
    puVar10 = (uint *)0x0;
  }
  else {
    *puVar10 = (uint)&UNK_00c7f790;
    puVar10[1] = (uint)((uint *)CONCAT13(cVar4 == '\0',(int3)unaff_EBP) != unaff_EBX);
  }
  *puVar9 = puVar10;
  func_0x00401000();
  func_0x00985ff0();
  func_0x0052e590();
  func_0x00668920();
  func_0x00401000();
  func_0x00985ff0();
  func_0x0052e590();
  func_0x00668920();
  func_0x00401000();
  func_0x00985ff0();
  puVar9 = (undefined4 *)func_0x0052e590();
  if ((uint *)*puVar9 != unaff_EBX) {
    (*(code *)**(undefined4 **)*puVar9)();
  }
  puVar10 = (uint *)func_0x00c0769f();
  if (puVar10 == unaff_EBX) {
    puVar10 = (uint *)0x0;
  }
  else {
    *puVar10 = (uint)&UNK_00c7f790;
    puVar10[1] = (uint)unaff_EBX;
  }
  *puVar9 = puVar10;
  func_0x00401000();
  func_0x00985ff0();
  puVar9 = (undefined4 *)func_0x0052e590();
  if ((uint *)*puVar9 != unaff_EBX) {
    (*(code *)**(undefined4 **)*puVar9)();
  }
  puVar10 = (uint *)func_0x00c0769f();
  if (puVar10 == unaff_EBX) {
    puVar10 = (uint *)0x0;
  }
  else {
    *puVar10 = (uint)&UNK_00caa2e8;
    *(byte *)(puVar10 + 1) = (byte)((uint)unaff_EBX >> 0x18);
  }
  *puVar9 = puVar10;
  func_0x00401000();
  puVar9 = (undefined4 *)func_0x004078e0();
  puVar10 = (uint *)*puVar9;
  if (((puVar10 != unaff_EBX) && ((*puVar10 & 0xffffff00) != 0)) && ((byte)puVar10[1] != bVar12)) {
    func_0x00985ff0();
    puVar9 = (undefined4 *)func_0x004078e0();
    if (((uint *)*puVar9 != unaff_EBX) && ((byte)*(uint *)*puVar9 < 0x80)) {
      InterlockedIncrement();
    }
    func_0x0052e590();
    func_0x00668920();
    func_0x00401000();
    func_0x00401000();
  }
  iVar7 = func_0x004019b0();
  func_0x00985ff0();
  puVar9 = (undefined4 *)func_0x0052e590();
  if ((uint *)*puVar9 != unaff_EBX) {
    (*(code *)**(undefined4 **)*puVar9)();
  }
  puVar10 = (uint *)func_0x00c0769f();
  if (puVar10 == unaff_EBX) {
    puVar10 = (uint *)0x0;
  }
  else {
    *puVar10 = (uint)&UNK_00c7f790;
    puVar10[1] = (uint)(iVar7 != 0);
  }
  *puVar9 = puVar10;
  func_0x00401000();
  (**(code **)(*unaff_EBP + 0xe0))();
  if (unaff_EBX == (uint *)&UNK_00c7eafc) {
    puVar9 = (undefined4 *)func_0x00c0769f();
    if (puVar9 != (undefined4 *)&UNK_00c7eafc) {
      *puVar9 = &UNK_00c8b714;
      puVar9[1] = &UNK_00c7eafc;
    }
    func_0x00985ff0();
    (**(code **)(*unaff_EBP + 0xe8))();
    func_0x00401000();
    (*(code *)*_UNK_00c80a9c)();
  }
  else {
    uVar6 = func_0x00739f10();
    puVar10 = (uint *)func_0x00c0769f();
    if (puVar10 != unaff_EBX) {
      *puVar10 = (uint)&UNK_00c8b714;
      puVar10[1] = uVar6;
    }
    func_0x00985ff0();
    (**(code **)(*unaff_EBP + 0xe8))();
    func_0x00401000();
    if (unaff_EBX != (uint *)&UNK_00cafa50) {
      (*(code *)*_UNK_00cafa50)();
    }
    puVar10 = (uint *)func_0x00c0769f();
    if (puVar10 != unaff_EBX) {
      *puVar10 = (uint)&UNK_00c8b714;
      puVar10[1] = (uint)&UNK_00c7eafc;
    }
    func_0x00985ff0();
    (**(code **)(*unaff_EBP + 0xe8))();
    func_0x00401000();
    if (unaff_EBX != (uint *)&UNK_00c80a9c) {
      (*(code *)*_UNK_00c80a9c)();
    }
  }
  if (*(byte *)((int)unaff_EBP + 0xcd) == bVar12) {
    func_0x00985ff0();
    (**(code **)(*unaff_EBP + 0x114))();
    func_0x00401000();
  }
  func_0x00985ff0();
  (**(code **)(*unaff_EBP + 0xa0))();
  puVar10 = (uint *)func_0x00c07db2();
  func_0x00401000();
  if (puVar10 != unaff_EBX) {
    puVar10[0x13] = (uint)&UNK_00738b70;
  }
  func_0x00985ff0();
  (**(code **)(*unaff_EBP + 0xa0))();
  iVar7 = func_0x00c07db2();
  unaff_EBP[0x37] = iVar7;
  func_0x00401000();
  func_0x00985ff0();
  iVar7 = (**(code **)(*unaff_EBP + 0xa0))();
  unaff_EBP[0x38] = iVar7;
  func_0x00401000();
  func_0x00985ff0();
  func_0x008d59a0();
  func_0x00401000();
  func_0x00985ff0();
  func_0x008d59a0();
  func_0x00401000();
  func_0x00985ff0();
  func_0x008d59a0();
  func_0x00401000();
  puVar10 = (uint *)&stack0xffffff1c;
  func_0x00407a20(puVar10,&UNK_00c7eafc);
  uVar11 = func_0x004019b0();
  *(undefined4 *)(unaff_EBP[0x32] + 0xa3c) = uVar11;
  func_0x00401000();
  func_0x00401000();
  func_0x0073a0c0();
  uVar6 = *(uint *)(unaff_EBP[0x32] + 0xa3c);
  puVar8 = (uint *)func_0x00c0769f(8);
  if (puVar8 != unaff_EBX) {
    *puVar8 = (uint)&UNK_00c8b714;
    puVar8[1] = uVar6 / 5;
  }
  func_0x00985ff0(&UNK_00cafa6c);
  (**(code **)(*unaff_EBP + 0xe8))(&stack0xfffffef0,&stack0xfffffef0);
  func_0x00401000();
  if (puVar10 != unaff_EBX) {
    (**(code **)*puVar10)(1);
  }
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00543d30(&stack0xffffff20);
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  func_0x00401000();
  return;
}


