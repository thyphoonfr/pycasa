// Address: 0099ac80
// Function: FUN_0099ac80
// Target requested: 0x0099AC80

undefined4 FUN_0099ac80(char *param_1)

{
  int *piVar1;
  char cVar2;
  uint *puVar3;
  undefined1 *puVar4;
  char *pcVar5;
  int iVar6;
  int iVar7;
  undefined4 unaff_EBP;
  int iVar8;
  int unaff_EDI;
  
  puVar3 = *(uint **)(param_1 + 0x10);
  piVar1 = (int *)(param_1 + 0x10);
  if (((puVar3 != (uint *)0x0) && ((*puVar3 & 0xffffff00) != 0)) && ((char)puVar3[1] != '\0')) {
    func_0x00985a60();
    if (*piVar1 == 0) {
      puVar4 = (undefined1 *)0x0;
    }
    else {
      puVar4 = (undefined1 *)(*piVar1 + 4);
    }
    *puVar4 = 0;
  }
  (*(code *)**(undefined4 **)param_1)(1);
  if (param_1[0xc] != '\0') {
    if (((uint *)*piVar1 == (uint *)0x0) || (*(uint *)*piVar1 >> 8 < 0x1000)) {
      func_0x00985990(&stack0x00000000,0x1001,0);
      func_0x005c2100();
      func_0x00401000();
    }
    pcVar5 = param_1;
    if (param_1 != (char *)0x0) {
      do {
        cVar2 = *pcVar5;
        pcVar5 = pcVar5 + 1;
      } while (cVar2 != '\0');
      func_0x00985ff0(param_1);
    }
    func_0x0049f820(0x5b,0x28);
    func_0x0049f820(0x5d,0x29);
    if (*(int *)(param_1 + 4) == 0) {
      iVar8 = 0;
    }
    else {
      iVar8 = *(int *)(param_1 + 4) + 4;
    }
    func_0x00985a60();
    if (*piVar1 == 0) {
      iVar7 = 0;
    }
    else {
      iVar7 = *piVar1 + 4;
    }
    if (unaff_EDI == 0) {
      iVar6 = 0;
    }
    else {
      iVar6 = unaff_EDI + 4;
    }
    func_0x009bf1a0(iVar6,unaff_EBP,iVar7,0x1000,iVar8);
    func_0x0099abc0(piVar1);
    func_0x00401000();
  }
  return 0;
}


