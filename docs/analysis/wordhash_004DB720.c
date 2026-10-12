// Address: 004db720
// Function: FUN_004db720
// Target requested: 0x004DB720

undefined4 __thiscall FUN_004db720(int param_1,undefined4 param_2)

{
  int iVar1;
  uint uVar2;
  uint uVar3;
  undefined *puVar4;
  undefined4 uVar5;
  uint uStack_38;
  undefined4 uStack_34;
  uint uStack_30;
  int iStack_2c;
  undefined4 uStack_28;
  int iStack_24;
  undefined1 uStack_20;
  int iStack_1c;
  int iStack_18;
  
  func_0x00991870(&iStack_1c,param_2);
  if (iStack_18 != 0) {
    uStack_38 = 0;
    iVar1 = func_0x007046e0(&iStack_1c,param_1 + 0xc,&uStack_38);
    func_0x0099cde0(iVar1,&UNK_00c85efc,&UNK_00c85f0c,0x205);
    if (iVar1 == 0) {
      if (*(int *)(param_1 + 0x20) == 0x10000) {
        uVar2 = func_0x00c08928(iStack_18);
        uStack_34 = func_0x00c08928(iStack_18);
        func_0x00c08a1d(iStack_18,0,2);
        uStack_30 = func_0x00c08928(iStack_18);
        func_0x00c08a1d(iStack_18,uStack_34,0);
        if (uStack_30 <= uVar2) {
          iStack_2c = param_1 + 0xc;
          *(undefined4 *)(param_1 + 0x30) = 0;
          uStack_28 = 0xffffffff;
          iStack_24 = 0;
          uStack_20 = 0;
          func_0x004ddea0();
          while (iStack_24 != 0) {
            uVar2 = 0;
            if ((*(uint *)(iStack_24 + 0xc) & 0xfffffffe) != 0) {
              do {
                uVar3 = *(int *)(*(int *)(iStack_24 + 8) + uVar2 * 4) + 1;
                if (uVar3 <= *(uint *)(param_1 + 0x30)) {
                  uVar3 = *(uint *)(param_1 + 0x30);
                }
                *(uint *)(param_1 + 0x30) = uVar3;
                uVar2 = uVar2 + 1;
              } while (uVar2 < *(uint *)(iStack_24 + 0xc) >> 1);
            }
            func_0x004ddea0();
          }
          if (uStack_38 < *(uint *)(param_1 + 0x30)) {
            func_0x0099cde0(3,&UNK_00c85f68,&UNK_00c85f0c,0x230);
          }
          *(undefined1 *)(param_1 + 8) = 0;
          goto LAB_004db8b7;
        }
        uVar5 = 0x216;
        puVar4 = &UNK_00c85f48;
      }
      else {
        uVar5 = 0x20e;
        puVar4 = &UNK_00c85f24;
      }
      func_0x0099cde0(3,puVar4,&UNK_00c85f0c,uVar5);
    }
    func_0x004d84a0();
    *(undefined4 *)(param_1 + 0x30) = 0;
    *(undefined1 *)(param_1 + 8) = 0;
  }
LAB_004db8b7:
  if (iStack_1c != 0) {
    iVar1 = InterlockedDecrement(iStack_1c);
    if (iVar1 != 0) {
      return 0;
    }
    func_0x0097caf0(iStack_1c);
    iStack_1c = 0;
  }
  func_0x0099d890();
  return 0;
}


