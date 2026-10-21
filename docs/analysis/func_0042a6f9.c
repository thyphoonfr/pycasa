// Address: 0042a6f9
// Function: FUN_0042a6f9
// Target requested: 0x0042a6f9

undefined4 FUN_0042a6f9(void)

{
  uint *puVar1;
  int iVar2;
  int unaff_EBX;
  char *pcVar3;
  bool bVar4;
  int *in_stack_0000001c;
  int *in_stack_0000002c;
  
  FUN_009b9190();
  func_0x009b93f0();
  func_0x00401000();
  *in_stack_0000002c = 0;
  FUN_0099ac80();
  puVar1 = *(uint **)(unaff_EBX + 0x10);
  if (((puVar1 == (uint *)0x0) || ((*puVar1 & 0xffffff00) == 0)) || ((char)puVar1[1] == '\0'))
  goto LAB_0042a7cb;
  if (puVar1 != (uint *)0x0) {
    if (puVar1 == (uint *)0xfffffffc) {
      if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_0042a7ae;
      bVar4 = false;
    }
    else {
      if (puVar1 == (uint *)0x0) {
        puVar1 = (uint *)0x0;
      }
      else {
        puVar1 = puVar1 + 1;
      }
      iVar2 = 0xb;
      bVar4 = true;
      pcVar3 = "rotate(-1)";
      do {
        if (iVar2 == 0) break;
        iVar2 = iVar2 + -1;
        bVar4 = *pcVar3 == (char)*puVar1;
        pcVar3 = pcVar3 + 1;
        puVar1 = (uint *)((int)puVar1 + 1);
      } while (bVar4);
    }
    if (bVar4) goto LAB_0042a7cb;
  }
LAB_0042a7ae:
  if (*(int *)(unaff_EBX + 0x10) == 0) {
    iVar2 = 0;
  }
  else {
    iVar2 = *(int *)(unaff_EBX + 0x10) + 4;
  }
  func_0x00c07eef(iVar2,&UNK_00c81474,in_stack_0000002c);
LAB_0042a7cb:
  if (((in_stack_0000001c[2] <= *in_stack_0000001c) ||
      (in_stack_0000001c[3] <= in_stack_0000001c[1])) && (*in_stack_0000002c == 0)) {
    return 0;
  }
  return 1;
}


