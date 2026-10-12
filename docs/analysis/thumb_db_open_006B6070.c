// Address: 006b6070
// Function: FUN_006b6070
// Target requested: 0x006B6070

undefined4 FUN_006b6070(byte *param_1,char *param_2)

{
  uint *puVar1;
  byte *pbVar2;
  char *pcVar3;
  char cVar4;
  char *pcVar5;
  int unaff_retaddr;
  undefined1 auStack_c [4];
  undefined4 uStack_8;
  
  pcVar3 = param_2;
  puVar1 = *(uint **)((int)param_1 + 0x84);
  if (((puVar1 != (uint *)0x0) && ((*puVar1 & 0xffffff00) != 0)) && ((char)puVar1[1] != '\0')) {
    return 3;
  }
  uStack_8 = 0;
  func_0x00985ff0(&UNK_00ca8440);
  param_1 = (byte *)0x0;
  pcVar5 = pcVar3;
  if (pcVar3 != (char *)0x0) {
    do {
      cVar4 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar4 != '\0');
    func_0x00985ff0(pcVar3);
  }
  func_0x006b5bc0(&param_1,auStack_c);
  func_0x005c2100();
  func_0x00401000();
  uStack_8 = 0;
  func_0x00401000();
  func_0x00401000();
  param_1 = (byte *)0x0;
  pcVar5 = pcVar3;
  if (pcVar3 != (char *)0x0) {
    do {
      cVar4 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar4 != '\0');
    func_0x00985ff0(pcVar3);
  }
  pbVar2 = param_1;
  if (*(byte **)(unaff_retaddr + 0x88) != param_1) {
    func_0x00401000();
    *(byte **)(unaff_retaddr + 0x88) = pbVar2;
    if ((pbVar2 != (byte *)0x0) &&
       ((0x7f < *pbVar2 || (cVar4 = InterlockedIncrement(pbVar2), cVar4 == -1)))) {
      func_0x00985a60();
    }
  }
  func_0x00401000();
  return 0;
}


