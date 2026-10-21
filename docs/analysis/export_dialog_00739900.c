// Address: 00739900
// Function: FUN_00739900
// Target requested: 0x00739900

void FUN_00739900(void)

{
  int iVar1;
  int unaff_EBX;
  
  func_0x0073b500();
  if (**(int **)(unaff_EBX + 200) == 0) {
    iVar1 = 0;
  }
  else {
    iVar1 = **(int **)(unaff_EBX + 200) + 4;
  }
  func_0x00985af0(&stack0x00000008,iVar1);
  func_0x00985af0(&stack0x00000000,&UNK_00c80910);
  func_0x0073a140();
  func_0x00401000();
  return;
}


