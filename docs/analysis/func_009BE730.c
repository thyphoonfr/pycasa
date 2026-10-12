// Address: 009be730
// Function: FUN_009be730
// Target requested: 0x009BE730

byte * FUN_009be730(int *param_1,byte *param_2,undefined4 param_3)

{
  char *pcVar1;
  byte *pbVar2;
  int *piVar3;
  char cVar4;
  int iVar5;
  char *pcVar6;
  byte *pbVar7;
  byte bVar8;
  int iVar9;
  char *unaff_EBX;
  byte *unaff_EBP;
  char *pcVar10;
  char *pcVar11;
  byte *unaff_ESI;
  char *pcVar12;
  byte *pbVar13;
  undefined *puVar14;
  
  piVar3 = param_1;
  if (param_1[2] == 0) {
    param_2[0] = 0;
    param_2[1] = 0;
    param_2[2] = 0;
    param_2[3] = 0;
    return param_2;
  }
  func_0x009bd5b0(param_3);
  puVar14 = &UNK_00c80c78;
  param_1 = (int *)0x0;
  func_0x00985ff0();
  func_0x00985af0(&param_1,param_3);
  func_0x00985af0(&param_1,&UNK_00c8193c);
  func_0x00985a60();
  if ((*piVar3 != 0) && (pcVar11 = (char *)(*piVar3 + 4), pcVar11 != (char *)0x0)) {
    if (puVar14 == (undefined *)0x0) {
      pcVar10 = (char *)0x0;
    }
    else {
      pcVar10 = puVar14 + 4;
    }
    if ((pcVar10 != (char *)0x0) && (*pcVar11 != '\0')) {
LAB_009be7e0:
      pcVar6 = pcVar10;
      pcVar12 = pcVar11;
      cVar4 = *pcVar10;
      if (*pcVar10 != '\0') {
        while( true ) {
          if ((cVar4 < 'A') || ('Z' < cVar4)) {
            iVar9 = (int)cVar4;
          }
          else {
            iVar9 = cVar4 + 0x20;
          }
          cVar4 = *pcVar12;
          if ((cVar4 < 'A') || ('Z' < cVar4)) {
            iVar5 = (int)cVar4;
          }
          else {
            iVar5 = cVar4 + 0x20;
          }
          if (iVar9 != iVar5) break;
          pcVar1 = pcVar6 + 1;
          pcVar6 = pcVar6 + 1;
          pcVar12 = pcVar12 + 1;
          cVar4 = *pcVar1;
          if (*pcVar1 == '\0') goto LAB_009be829;
        }
      }
      if (*pcVar6 != '\0') goto code_r0x009be863;
LAB_009be829:
      if (pcVar11 != (char *)0x0) {
        pcVar6 = (char *)func_0x00bf7fa0(pcVar11 + 1,0x5b);
        pcVar10 = unaff_EBX + 1;
        do {
          cVar4 = *unaff_EBX;
          unaff_EBX = unaff_EBX + 1;
        } while (cVar4 != '\0');
        if (unaff_ESI == (byte *)0x0) {
          pbVar7 = (byte *)0x0;
        }
        else {
          pbVar7 = unaff_ESI + 4;
        }
        pcVar11 = pcVar11 + ((int)unaff_EBX - (int)pcVar10);
        if (((pbVar7 != (byte *)0x0) && (pcVar11 != (char *)0x0)) && (*pcVar11 != '\0')) {
          while( true ) {
            pbVar13 = pbVar7;
            pcVar10 = pcVar11;
            bVar8 = *pbVar7;
            if (*pbVar7 != 0) {
              while( true ) {
                if (((char)bVar8 < 'A') || ('Z' < (char)bVar8)) {
                  iVar9 = (int)(char)bVar8;
                }
                else {
                  iVar9 = (char)bVar8 + 0x20;
                }
                cVar4 = *pcVar10;
                if ((cVar4 < 'A') || ('Z' < cVar4)) {
                  iVar5 = (int)cVar4;
                }
                else {
                  iVar5 = cVar4 + 0x20;
                }
                if (iVar9 != iVar5) break;
                pbVar2 = pbVar13 + 1;
                pbVar13 = pbVar13 + 1;
                pcVar10 = pcVar10 + 1;
                bVar8 = *pbVar2;
                if (*pbVar2 == 0) goto LAB_009be901;
              }
            }
            if (*pbVar13 == 0) break;
            pcVar11 = pcVar11 + 1;
            if (*pcVar11 == '\0') goto LAB_009be86f;
          }
LAB_009be901:
          if ((pcVar11 != (char *)0x0) && ((pcVar6 == (char *)0x0 || (pcVar11 < pcVar6)))) {
            iVar9 = func_0x00bf7fa0(pcVar11,0x3d);
            iVar5 = func_0x00bf7fa0(pcVar11,0xd);
            if (iVar5 == 0) {
              iVar5 = func_0x00bf7fa0(pcVar11 + 1,10);
              if (iVar5 == 0) {
                func_0x00bf7fa0(pcVar11 + 1,0);
              }
            }
            func_0x00985ff0(iVar9 + 1);
            *(byte **)unaff_ESI = unaff_EBP;
            if ((unaff_EBP != (byte *)0x0) && (*unaff_EBP < 0x80)) {
              InterlockedIncrement(unaff_EBP);
            }
            func_0x00401000();
            unaff_EBP = unaff_ESI;
            goto LAB_009be879;
          }
        }
      }
    }
  }
LAB_009be86f:
  unaff_EBP[0] = 0;
  unaff_EBP[1] = 0;
  unaff_EBP[2] = 0;
  unaff_EBP[3] = 0;
LAB_009be879:
  func_0x00401000();
  func_0x00401000();
  return unaff_EBP;
code_r0x009be863:
  pcVar11 = pcVar11 + 1;
  if (*pcVar11 == '\0') goto LAB_009be86f;
  goto LAB_009be7e0;
}


