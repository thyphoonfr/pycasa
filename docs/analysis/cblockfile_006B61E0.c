// Address: 006b61e0
// Function: FUN_006b61e0
// Target requested: 0x006B61E0

/* WARNING: Removing unreachable block (ram,0x006b6429) */
/* WARNING: Removing unreachable block (ram,0x006b65d6) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int FUN_006b61e0(uint param_1)

{
  int in_EAX;
  uint *puVar1;
  undefined4 *puVar2;
  int iVar3;
  undefined *puVar4;
  uint uVar5;
  uint *puVar6;
  uint *puVar7;
  uint *puVar8;
  bool bVar9;
  undefined4 uStack_20;
  uint *puStack_1c;
  int iStack_18;
  undefined4 uStack_14;
  undefined4 uStack_10;
  undefined4 uStack_c;
  undefined4 uStack_8;
  
  uStack_20 = 0;
  func_0x0040ea90(&UNK_00ca8448,param_1);
  func_0x006b5bc0(in_EAX + 0x88,&uStack_20);
  uStack_14 = _DAT_00d678e0;
  uStack_10 = 0;
  puVar7 = (uint *)0x1;
  uStack_c = 2;
  uStack_8 = 1;
  if (param_1 < *(uint *)(in_EAX + 0x80) >> 1) goto LAB_006b6576;
  puVar6 = (uint *)(param_1 + 1);
  if (0x6666666 < puVar6) {
    iVar3 = *(int *)(in_EAX + 0x7c);
    if (iVar3 != 0) {
      func_0x00401110(0x14,&SUB_0099db30);
      func_0x0097caf0(iVar3 + -4);
    }
    *(uint *)(in_EAX + 0x80) = *(uint *)(in_EAX + 0x80) & 1;
    *(undefined4 *)(in_EAX + 0x7c) = 0;
    goto LAB_006b6555;
  }
  puVar1 = (uint *)(*(uint *)(in_EAX + 0x80) >> 1);
  if (puVar6 == puVar1) {
    puVar8 = *(uint **)(in_EAX + 0x7c);
LAB_006b6551:
    if (puVar8 != (uint *)0x0) {
LAB_006b6576:
      if (iStack_18 == 0) {
        iVar3 = 0;
      }
      else {
        iVar3 = iStack_18 + 4;
      }
      iVar3 = func_0x00991d90(*(int *)(in_EAX + 0x7c) + param_1 * 0x14,&uStack_14,iVar3);
      if (iVar3 != 0) {
        puVar4 = (undefined *)(iStack_18 + 4);
        if (iStack_18 == 0) {
          puVar4 = &UNK_00c7f979;
        }
        func_0x0040eab0(&UNK_00ca844c,iVar3,puVar4);
        func_0x00980700(0,0);
        func_0x00401000();
      }
      func_0x00401000();
      func_0x00401000();
      return iVar3;
    }
  }
  else {
    if ((*(uint *)(in_EAX + 0x80) & 1) == 0) {
      if ((uint)((int)puVar6 * 0x14) < 0x100000) {
        if (puVar6 != (uint *)0x0) {
          do {
            puVar7 = (uint *)((int)puVar7 * 2);
          } while (puVar7 <= puVar6);
        }
      }
      else {
        puVar7 = (uint *)(((uint)puVar6 & 0xfffffc00) + 0x400);
      }
      if ((uint)((int)puVar1 * 0x14) < 0x100000) {
        if ((uint *)0x1 < puVar1) {
          puStack_1c = (uint *)(float)(int)puVar1;
          puVar6 = (uint *)(1 << ((char)((uint)puStack_1c >> 0x17) + 0x81U & 0x1f));
          bVar9 = puVar6 < puVar1;
          puVar1 = puVar6;
          if (bVar9) {
            puVar1 = (uint *)((int)puVar6 * 2);
          }
        }
      }
      else {
        puVar1 = (uint *)(((uint)puVar1 & 0x7ffffc00) + 0x400);
      }
      puVar8 = *(uint **)(in_EAX + 0x7c);
      if (puVar1 == puVar7) {
LAB_006b6538:
        *(uint *)(in_EAX + 0x80) = *(uint *)(in_EAX + 0x80) & 1 | (param_1 + 1) * 2;
        goto LAB_006b6551;
      }
      puVar8 = (uint *)0x0;
      puVar6 = puStack_1c;
      if (puVar7 != (uint *)0x0) {
        uVar5 = -(uint)((int)(ZEXT48(puVar7) * 0x14 >> 0x20) != 0) | (uint)(ZEXT48(puVar7) * 0x14);
        uVar5 = -(uint)(0xfffffffb < uVar5) | uVar5 + 4;
        puVar2 = (undefined4 *)func_0x0097c5d0(uVar5);
        if (puVar2 != (undefined4 *)0x0) {
          func_0x00bf37c0(puVar2,0,uVar5);
          *puVar2 = puVar7;
          puVar8 = puVar2 + 1;
          func_0x004010e0(0x14,&UNK_0099dae0);
          if (puVar8 != (uint *)0x0) {
            puVar1 = (uint *)(*(uint *)(in_EAX + 0x80) >> 1);
            puVar6 = puStack_1c;
            if (puVar7 < puVar1) {
              puVar1 = puVar7;
            }
            while (puStack_1c = puVar1, puStack_1c != (uint *)0x0) {
              func_0x0099dc10();
              puVar6 = (uint *)((int)puStack_1c + -1);
              puVar1 = (uint *)((int)puStack_1c + -1);
            }
            goto LAB_006b650b;
          }
        }
        goto LAB_006b63a7;
      }
LAB_006b650b:
      puStack_1c = puVar6;
      iVar3 = *(int *)(in_EAX + 0x7c);
      if (iVar3 != 0) {
        func_0x00401110(0x14,&SUB_0099db30);
        func_0x0097caf0(iVar3 + -4);
      }
      *(uint **)(in_EAX + 0x7c) = puVar8;
      if (puVar8 != (uint *)0x0) goto LAB_006b6538;
    }
    else {
      puVar8 = (uint *)0x0;
      if (puVar6 == (uint *)0x0) {
LAB_006b6360:
        iVar3 = *(int *)(in_EAX + 0x7c);
        if (iVar3 != 0) {
          func_0x00401110(0x14,&SUB_0099db30);
          func_0x0097caf0(iVar3 + -4);
        }
        *(uint **)(in_EAX + 0x7c) = puVar8;
        if (puVar8 != (uint *)0x0) {
          *(uint *)(in_EAX + 0x80) = *(uint *)(in_EAX + 0x80) & 1 | (param_1 + 1) * 2;
          goto LAB_006b6551;
        }
      }
      else {
        uVar5 = -(uint)((int)(ZEXT48(puVar6) * 0x14 >> 0x20) != 0) | (uint)(ZEXT48(puVar6) * 0x14);
        uVar5 = -(uint)(0xfffffffb < uVar5) | uVar5 + 4;
        puVar8 = (uint *)func_0x0097c5d0(uVar5);
        if (puVar8 != (uint *)0x0) {
          func_0x00bf37c0(puVar8,0,uVar5);
          *puVar8 = (uint)puVar6;
          puVar8 = puVar8 + 1;
          func_0x004010e0(0x14,&UNK_0099dae0);
          puStack_1c = puVar8;
          if (puVar8 != (uint *)0x0) {
            puVar7 = (uint *)(*(uint *)(in_EAX + 0x80) >> 1);
            if (puVar7 <= puVar6) {
              puVar6 = puVar7;
            }
            for (; puStack_1c = puVar8, puVar6 != (uint *)0x0; puVar6 = (uint *)((int)puVar6 + -1))
            {
              func_0x0099dc10();
              puVar8 = puStack_1c;
            }
            goto LAB_006b6360;
          }
        }
LAB_006b63a7:
        iVar3 = *(int *)(in_EAX + 0x7c);
        if (iVar3 != 0) {
          func_0x00401110(0x14,&SUB_0099db30);
          func_0x0097caf0(iVar3 + -4);
        }
      }
    }
    *(uint *)(in_EAX + 0x80) = *(uint *)(in_EAX + 0x80) & 1;
    *(undefined4 *)(in_EAX + 0x7c) = 0;
  }
LAB_006b6555:
  func_0x00401000();
  func_0x00401000();
  return 4;
}


