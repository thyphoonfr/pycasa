// Address: 006b5e00
// Function: FUN_006b5e00
// Target requested: 0x006B5E00

void __fastcall FUN_006b5e00(undefined4 *param_1)

{
  byte *pbVar1;
  int iVar2;
  int unaff_ESI;
  uint uVar3;
  int unaff_EDI;
  undefined1 auStack_1c [28];
  
  *param_1 = &UNK_00ca84bc;
  param_1[0x12] = &UNK_00ca84e8;
  func_0x00407a20(auStack_1c,&UNK_00c7eafc,&UNK_00ca8400);
  iVar2 = func_0x004019b0();
  func_0x00401000();
  func_0x00401000();
  if (iVar2 == 0) goto LAB_006b5f3d;
  pbVar1 = (byte *)param_1[0x21];
  if ((pbVar1 != (byte *)0x0) && (*pbVar1 < 0x80)) {
    InterlockedIncrement(pbVar1);
  }
  func_0x00985af0(&stack0xffffffd4,&UNK_00ca8414);
  if (unaff_EDI == 0) {
    iVar2 = 0;
  }
  else {
    iVar2 = unaff_EDI + 4;
  }
  func_0x009917f0(iVar2);
  if (pbVar1 != (byte *)0x0) {
    func_0x00c07782(pbVar1,&UNK_00ca841c);
    uVar3 = 0;
    if ((param_1[0x1a] & 0xfffffffe) != 0) {
      do {
        func_0x00c07782(pbVar1,&UNK_00ca8434,*(uint *)(param_1[0x19] + uVar3 * 4) & 0xffffff,
                        *(undefined4 *)(param_1[0x17] + uVar3 * 4),
                        *(undefined4 *)(param_1[0x15] + uVar3 * 4));
        uVar3 = uVar3 + 1;
      } while (uVar3 < (uint)param_1[0x1a] >> 1);
    }
  }
  if (unaff_ESI == 0) {
LAB_006b5f2b:
    func_0x0099d890();
  }
  else {
    iVar2 = InterlockedDecrement(unaff_ESI);
    if (iVar2 == 0) {
      func_0x0097caf0(unaff_ESI);
      goto LAB_006b5f2b;
    }
  }
  func_0x00401000();
LAB_006b5f3d:
  if (param_1[0x28] != 0) {
    func_0x0097caf0(param_1[0x28]);
  }
  param_1[0x29] = param_1[0x29] & 1;
  param_1[0x28] = 0;
  if ((param_1[0x24] != 0) && (param_1[0x25] != 0)) {
    func_0x0097caf0(param_1[0x25]);
  }
  param_1[0x25] = 0;
  param_1[0x24] = 0;
  func_0x00401000();
  param_1[0x22] = 0;
  func_0x00401000();
  param_1[0x21] = 0;
  iVar2 = param_1[0x1f];
  if (iVar2 != 0) {
    func_0x00401110(0x14,&UNK_0099db30);
    func_0x0097caf0(iVar2 + -4);
  }
  param_1[0x20] = param_1[0x20] & 1;
  param_1[0x1f] = 0;
  func_0x00401000();
  param_1[0x1b] = 0;
  if (param_1[0x19] != 0) {
    func_0x0097caf0(param_1[0x19]);
  }
  param_1[0x1a] = param_1[0x1a] & 1;
  param_1[0x19] = 0;
  if (param_1[0x17] != 0) {
    func_0x0097caf0(param_1[0x17]);
  }
  param_1[0x18] = param_1[0x18] & 1;
  param_1[0x17] = 0;
  if (param_1[0x15] != 0) {
    func_0x0097caf0(param_1[0x15]);
  }
  param_1[0x16] = param_1[0x16] & 1;
  param_1[0x15] = 0;
  param_1[0x12] = &UNK_00c81f48;
  *param_1 = &UNK_00cd850c;
  if (*(char *)((int)param_1 + 5) != '\0') {
    func_0x0097b210(param_1);
  }
  if (param_1[7] != 0) {
    func_0x0097b420(0);
  }
  DeleteCriticalSection(param_1 + 10);
  CloseHandle(param_1[0x10]);
  *param_1 = &UNK_00c9416c;
  return;
}


