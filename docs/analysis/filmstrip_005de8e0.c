// Address: 005de8e0
// Function: FUN_005de8e0
// Target requested: 0x005de8e0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int __thiscall FUN_005de8e0(uint *******param_1,uint *******param_2)

{
  char cVar1;
  int iVar2;
  int *extraout_ECX;
  int *extraout_ECX_00;
  uint *******unaff_ESI;
  char *pcVar3;
  byte *pbVar4;
  uint *******pppppppuVar5;
  uint *******unaff_EDI;
  uint ******ppppppuVar6;
  char *pcVar7;
  uint ******ppppppuVar8;
  bool bVar9;
  undefined4 uVar10;
  uint ******ppppppuStack_7c;
  undefined1 *puStack_78;
  uint ******ppppppuStack_74;
  uint ******ppppppuStack_70;
  uint ******ppppppuStack_6c;
  uint ******ppppppuStack_68;
  uint ******ppppppuStack_64;
  uint ******ppppppuStack_54;
  uint *****pppppuStack_4c;
  uint ****ppppuStack_48;
  undefined4 uStack_44;
  uint *****apppppuStack_40 [2];
  int iStack_38;
  
  if (param_2[8] == (uint ******)0x8000002) {
    ppppppuVar6 = param_2[5];
    pppppppuVar5 = param_2 + 5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005dea07;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xd;
        bVar9 = true;
        pcVar3 = "buttontoggle";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xd;
        bVar9 = true;
        pcVar3 = "buttontoggle";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        if (_DAT_00d67914 == 0) {
          pppppuStack_4c = (uint *****)0x0;
          ppppppuStack_64 = (uint ******)0x5de9ba;
          func_0x00401000();
          return 0xf4241;
        }
        ppppppuStack_64 = &pppppuStack_4c;
        ppppppuStack_68 = (uint ******)0x5de98a;
        func_0x009c2f50();
        if (param_1 != (uint *******)0x0) {
          if (param_1 + 1 == (uint *******)0x0) {
            if ((((uint)*param_1 & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005de9f0;
            bVar9 = false;
          }
          else {
            iVar2 = 0x1d;
            bVar9 = true;
            pcVar3 = "searchcontainer/searchbutton";
            pppppppuVar5 = param_1 + 1;
            do {
              if (iVar2 == 0) break;
              iVar2 = iVar2 + -1;
              bVar9 = *pcVar3 == *(char *)pppppppuVar5;
              pcVar3 = pcVar3 + 1;
              pppppppuVar5 = (uint *******)((int)pppppppuVar5 + 1);
            } while (bVar9);
          }
          if (bVar9) {
            ppppppuStack_68 = param_2[9];
            ppppppuStack_6c = (uint ******)0x5de9f0;
            func_0x005d4a20();
          }
        }
        goto LAB_005de9f0;
      }
    }
LAB_005dea07:
    if ((param_1[0x333] != (uint ******)0x0) &&
       (ppppppuVar6 = *pppppppuVar5, ppppppuVar6 != (uint ******)0x0)) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005dea79;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 7;
        bVar9 = true;
        pcVar3 = "resync";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 7;
        bVar9 = true;
        pcVar3 = "resync";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_64 = (uint ******)0x0;
        ppppppuStack_6c = (uint ******)0x5dea75;
        ppppppuStack_68 = (uint ******)param_1;
        func_0x0059cc20();
      }
    }
LAB_005dea79:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005debbd;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xe;
        bVar9 = true;
        pcVar3 = "filmstripmove";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xe;
        bVar9 = true;
        pcVar3 = "filmstripmove";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuVar6 = param_1[0xc35];
        if ((((ppppppuVar6 == (uint ******)0x4) || (ppppppuVar6 == (uint ******)0x5)) ||
            (ppppppuVar6 == (uint ******)0x2)) || (ppppppuVar6 == (uint ******)0x6)) {
          ppppppuStack_64 = (uint ******)0x0;
          ppppppuStack_68 = (uint ******)0x0;
          ppppppuStack_6c = (uint ******)0x1;
          ppppppuStack_74 = (uint ******)0x5deb0e;
          ppppppuStack_70 = (uint ******)param_1;
          iVar2 = func_0x005f8d80();
          if (iVar2 != 0) {
            return iVar2;
          }
        }
        ppppppuStack_64 = (uint ******)0x5deb24;
        cVar1 = func_0x00569620();
        if (cVar1 != '\0') {
          ppppppuStack_68 = (uint ******)0x5deb2e;
          ppppppuStack_64 = (uint ******)param_1;
          iVar2 = func_0x0056aad0();
          if (iVar2 != 0) {
            return iVar2;
          }
        }
        if (_DAT_00d67914 == 0) {
          ppppppuStack_74 = (uint ******)0x0;
        }
        else {
          ppppppuStack_64 = (uint ******)0x5deb49;
          ppppppuStack_74 = (uint ******)func_0x009c2fc0();
        }
        ppppppuStack_64 = (uint ******)0x0;
        ppppppuStack_68 = (uint ******)0xd3e688;
        ppppppuStack_6c = (uint ******)0xd3b8a0;
        ppppppuStack_70 = (uint ******)0x0;
        puStack_78 = (undefined1 *)0x5deb61;
        iVar2 = func_0x00c07db2();
        if (iVar2 != 0) {
          ppppppuStack_64 = (uint ******)0x5deb6d;
          ppppppuStack_64 = (uint ******)func_0x005a65b0();
          if ((ppppppuStack_64 != param_1[0x399]) && (param_1[0x3aa] != (uint ******)0x0)) {
            ppppppuStack_68 = (uint ******)0x5deb87;
            func_0x00717c50();
          }
        }
        if (*(char *)((int)param_1 + 0x332f) == '\0') {
          ppppppuStack_64 = (uint ******)0x5deb97;
          func_0x005f8160();
          if (*(char *)((int)param_1 + 0x332f) == '\0') {
            return 0xf4241;
          }
        }
        if (*(char *)(param_1 + 0xccc) != '\0') {
          ppppppuStack_68 = (uint ******)0x5debaf;
          ppppppuStack_64 = (uint ******)param_1;
          func_0x0075eac0();
        }
        return 0xf4241;
      }
    }
LAB_005debbd:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005decb9;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xb;
        bVar9 = true;
        pcVar3 = "editcancel";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xb;
        bVar9 = true;
        pcVar3 = "editcancel";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        *(undefined1 *)(param_1 + 0x91) = 1;
        if ((uint *******)param_2[9] == param_1 + 0x42d) {
          ppppppuStack_64 = (uint ******)&UNK_00c949ac;
          pppppuStack_4c = (uint *****)0x0;
          ppppppuStack_68 = (uint ******)0x5dec5a;
          func_0x00985ff0();
          ppppppuStack_6c = ppppppuStack_54;
          ppppppuStack_70 = (uint ******)0x5dec67;
          ppppppuStack_68 = &pppppuStack_4c;
          iVar2 = func_0x00a53c20();
          goto LAB_005e04c5;
        }
        if ((uint *******)param_2[9] == param_1 + 0x3b7) {
          if (_DAT_00d67914 == 0) {
            ppppppuStack_64 = (uint ******)0x0;
          }
          else {
            ppppppuStack_64 = (uint ******)0x5dec8d;
            ppppppuStack_64 = (uint ******)func_0x009c2fc0();
          }
          ppppppuStack_68 = (uint ******)0x5dec9f;
          (*(code *)(*param_1)[0x1f])();
          *(undefined1 *)(param_1 + 0x5d) = 1;
          ppppppuStack_68 = (uint ******)0x5decb0;
          iVar2 = func_0x009cd8a0();
          return iVar2;
        }
        goto LAB_005dfa52;
      }
    }
LAB_005decb9:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005ded35;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xd;
        bVar9 = true;
        pcVar3 = "editselected";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xd;
        bVar9 = true;
        pcVar3 = "editselected";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        if ((uint *******)param_2[9] == param_1 + 0x42d) {
          ppppppuStack_64 = (uint ******)0x5ded2c;
          iVar2 = func_0x009cd8a0();
          return iVar2;
        }
        goto LAB_005dfa52;
      }
    }
LAB_005ded35:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005deda1;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 10;
        bVar9 = true;
        pcVar3 = "scrolling";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 10;
        bVar9 = true;
        pcVar3 = "scrolling";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_64 = (uint ******)0x1;
        ppppppuStack_6c = (uint ******)0x5ded98;
        ppppppuStack_68 = (uint ******)param_1;
        iVar2 = FUN_005ce090();
        return iVar2;
      }
    }
LAB_005deda1:
    ppppppuStack_64 = (uint ******)0x0;
    ppppppuStack_68 = (uint ******)0x5dedaf;
    cVar1 = func_0x00987030();
    if (cVar1 != '\0') {
      ppppppuStack_64 = (uint ******)param_2;
      ppppppuStack_6c = (uint ******)0x5dedc1;
      ppppppuStack_68 = (uint ******)param_1;
      iVar2 = func_0x005d3290();
      return iVar2;
    }
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005dee37;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xe;
        bVar9 = true;
        pcVar3 = "selectiondone";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xe;
        bVar9 = true;
        pcVar3 = "selectiondone";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_64 = (uint ******)param_2;
        ppppppuStack_68 = (uint ******)0x5dee2e;
        iVar2 = func_0x005d4e80();
        return iVar2;
      }
    }
LAB_005dee37:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005deeab;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xf;
        bVar9 = true;
        pcVar3 = "selectionvalid";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xf;
        bVar9 = true;
        pcVar3 = "selectionvalid";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_64 = (uint ******)0x5dee93;
        cVar1 = func_0x005f9550();
        if (cVar1 != '\0') {
          ppppppuStack_64 = (uint ******)0x1;
          ppppppuStack_68 = (uint ******)0x5deea2;
          iVar2 = func_0x005f4130();
          return iVar2;
        }
      }
    }
LAB_005deeab:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005def1f;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0x11;
        bVar9 = true;
        pcVar3 = "selectioninvalid";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0x11;
        bVar9 = true;
        pcVar3 = "selectioninvalid";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_64 = (uint ******)0x5def07;
        cVar1 = func_0x005f9550();
        if (cVar1 != '\0') {
          ppppppuStack_64 = (uint ******)0x0;
          ppppppuStack_68 = (uint ******)0x5def16;
          iVar2 = func_0x005f4130();
          return iVar2;
        }
      }
    }
LAB_005def1f:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005def92;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xe;
        bVar9 = true;
        pcVar3 = "selectiondrag";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xe;
        bVar9 = true;
        pcVar3 = "selectiondrag";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_64 = (uint ******)0x5def7b;
        cVar1 = func_0x005f9550();
        if (cVar1 != '\0') {
          ppppppuStack_68 = (uint ******)0x5def89;
          ppppppuStack_64 = (uint ******)param_1;
          iVar2 = func_0x005f4400();
          return iVar2;
        }
      }
    }
LAB_005def92:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005deff8;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xc;
        bVar9 = true;
        pcVar3 = "scrollstart";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xc;
        bVar9 = true;
        pcVar3 = "scrollstart";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_68 = (uint ******)0x5deff3;
        ppppppuStack_64 = (uint ******)param_1;
        func_0x00562ae0();
        goto LAB_005dfa52;
      }
    }
LAB_005deff8:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df05e;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 0xb;
        bVar9 = true;
        pcVar3 = "scrollstop";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 0xb;
        bVar9 = true;
        pcVar3 = "scrollstop";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        ppppppuStack_68 = (uint ******)0x5df059;
        ppppppuStack_64 = (uint ******)param_1;
        func_0x0052e1f0();
        goto LAB_005dfa52;
      }
    }
LAB_005df05e:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 != (uint ******)0x0) {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df0c5;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 10;
        bVar9 = true;
        pcVar3 = "dragstart";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 10;
        bVar9 = true;
        pcVar3 = "dragstart";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (bVar9) {
        *(undefined1 *)(param_1 + 0x370) = 1;
        goto LAB_005dfa52;
      }
    }
LAB_005df0c5:
    ppppppuVar6 = *pppppppuVar5;
    if (ppppppuVar6 == (uint ******)0x0) {
LAB_005df120:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df17b;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0xb;
          bVar9 = true;
          pcVar3 = "dragcancel";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0xb;
          bVar9 = true;
          pcVar3 = "dragcancel";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) goto LAB_005dfa47;
      }
LAB_005df17b:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df1ea;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 9;
          bVar9 = true;
          pcVar3 = "selected";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 9;
          bVar9 = true;
          pcVar3 = "selected";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          ppppppuStack_64 = (uint ******)0x5df1e1;
          iVar2 = func_0x0056bc10();
          return iVar2;
        }
      }
LAB_005df1ea:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df276;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0x11;
          bVar9 = true;
          pcVar3 = "selectedbyheader";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0x11;
          bVar9 = true;
          pcVar3 = "selectedbyheader";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          ppppppuStack_70 = (uint ******)param_2[9][0xa8];
          ppppppuStack_64 = (uint ******)0x0;
          ppppppuStack_68 = (uint ******)0x1;
          ppppppuStack_6c = (uint ******)0x0;
          ppppppuStack_74 = (uint ******)0x5df26d;
          iVar2 = (*(code *)param_1[0xa9][0x11])();
          return iVar2;
        }
      }
LAB_005df276:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df2d1;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 9;
          bVar9 = true;
          pcVar3 = "combotab";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 9;
          bVar9 = true;
          pcVar3 = "combotab";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          return 1000000;
        }
      }
LAB_005df2d1:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df34b;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0xc;
          bVar9 = true;
          pcVar3 = "albumdouble";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0xc;
          bVar9 = true;
          pcVar3 = "albumdouble";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          ppppppuStack_64 = (uint ******)0x4;
          ppppppuStack_68 = (uint ******)0x5df333;
          cVar1 = func_0x0057c430();
          if (cVar1 != '\0') {
            return 1000000;
          }
          ppppppuStack_68 = (uint ******)0x5df342;
          iVar2 = func_0x006db580();
          return iVar2;
        }
      }
LAB_005df34b:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df3a6;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0xf;
          bVar9 = true;
          pcVar3 = "selnode_double";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0xf;
          bVar9 = true;
          pcVar3 = "selnode_double";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          return 1000000;
        }
      }
LAB_005df3a6:
      ppppppuStack_64 = (uint ******)0x0;
      ppppppuStack_68 = (uint ******)0x5df3b4;
      cVar1 = func_0x00987030();
      if (cVar1 != '\0') {
        ppppppuStack_6c = (uint ******)0x5df3c3;
        ppppppuStack_68 = (uint ******)param_1;
        ppppppuStack_64 = (uint ******)pppppppuVar5;
        iVar2 = func_0x00679ca0();
        return iVar2;
      }
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df436;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0x11;
          bVar9 = true;
          pcVar3 = "BicubicEndThread";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0x11;
          bVar9 = true;
          pcVar3 = "BicubicEndThread";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          ppppppuStack_64 = (uint ******)0x0;
          ppppppuStack_68 = (uint ******)0x0;
          ppppppuStack_70 = (uint ******)0x5df431;
          ppppppuStack_6c = (uint ******)param_1;
          func_0x006040a0();
          goto LAB_005dfa52;
        }
      }
LAB_005df436:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df4c7;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0x13;
          bVar9 = true;
          pcVar3 = "BicubicBeginThread";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0x13;
          bVar9 = true;
          pcVar3 = "BicubicBeginThread";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          if (*(char *)(param_1 + 0xd28) == '\0') {
            ppppppuStack_64 = (uint ******)&ppppuStack_48;
            ppppppuStack_68 = (uint ******)0x5df4ad;
            QueryPerformanceCounter();
            *(undefined1 *)(param_1 + 0xd28) = 1;
            *(double *)(param_1 + 0xd26) = (double)CONCAT44(uStack_44,ppppuStack_48);
          }
          goto LAB_005dfa52;
        }
      }
LAB_005df4c7:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df52c;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0xc;
          bVar9 = true;
          pcVar3 = "captiondone";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0xc;
          bVar9 = true;
          pcVar3 = "captiondone";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          ppppppuStack_64 = (uint ******)0x5df527;
          func_0x005f89a0();
          goto LAB_005dfa52;
        }
      }
LAB_005df52c:
      ppppppuVar6 = *pppppppuVar5;
      if (ppppppuVar6 != (uint ******)0x0) {
        if (ppppppuVar6 == (uint ******)0xfffffffc) {
          if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df59f;
          bVar9 = false;
        }
        else if (ppppppuVar6 == (uint ******)0x0) {
          iVar2 = 0xe;
          bVar9 = true;
          pcVar3 = "captioncancel";
          pcVar7 = (char *)0x0;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *pcVar7;
            pcVar3 = pcVar3 + 1;
            pcVar7 = pcVar7 + 1;
          } while (bVar9);
        }
        else {
          iVar2 = 0xe;
          bVar9 = true;
          pcVar3 = "captioncancel";
          ppppppuVar6 = ppppppuVar6 + 1;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pcVar3 == *(char *)ppppppuVar6;
            pcVar3 = pcVar3 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          ppppppuStack_64 = (uint ******)0x1;
          ppppppuStack_68 = (uint ******)0x5df58a;
          ppppppuStack_68 = (uint ******)FUN_00579330();
          ppppppuStack_6c = (uint ******)0x5df594;
          func_0x00568010();
          return 0;
        }
      }
LAB_005df59f:
      ppppppuStack_64 = (uint ******)0x0;
      ppppppuStack_68 = (uint ******)0x5df5ad;
      cVar1 = func_0x00987030();
      ppppppuStack_68 = (uint ******)0x0;
      if (cVar1 != '\0') {
        ppppppuStack_6c = (uint ******)&UNK_00c81288;
        ppppppuStack_70 = (uint ******)0x5df5bf;
        cVar1 = func_0x00987150();
        if (cVar1 == '\0') {
          ppppppuStack_70 = (uint ******)0x0;
          ppppppuStack_74 = (uint ******)0x1;
          puStack_78 = (undefined1 *)0x5df5e7;
          func_0x005ff7a0();
          return 1000000;
        }
        ppppppuStack_70 = (uint ******)0x1;
        ppppppuStack_74 = (uint ******)0x0;
        puStack_78 = (undefined1 *)0x5df5d0;
        func_0x005ff7a0();
        return 1000000;
      }
      ppppppuStack_6c = (uint ******)0x5df5ff;
      cVar1 = func_0x00987030();
      if (cVar1 != '\0') {
        ppppppuStack_70 = (uint ******)0x5df60f;
        iVar2 = func_0x007b3920();
        return iVar2;
      }
      ppppppuStack_6c = (uint ******)0x0;
      ppppppuStack_70 = (uint ******)0x5df627;
      cVar1 = func_0x00987030();
      if (cVar1 != '\0') {
        ppppppuStack_74 = (uint ******)0x5df635;
        func_0x0053c020();
        return 1000000;
      }
      ppppppuStack_70 = (uint ******)0x0;
      ppppppuStack_74 = (uint ******)0x5df651;
      cVar1 = func_0x00987030();
      if (cVar1 != '\0') {
        ppppppuStack_74 = *pppppppuVar5;
        if ((ppppppuStack_74 != (uint ******)0x0) && (*(byte *)ppppppuStack_74 < 0x80)) {
          puStack_78 = (undefined1 *)0x5df671;
          InterlockedIncrement();
        }
        ppppppuStack_74 = (uint ******)0x5df67e;
        func_0x005e0f70();
        ppppppuStack_74 = (uint ******)0x5df687;
        func_0x00401000();
        return 0xf4242;
      }
      ppppppuStack_74 = (uint ******)0x0;
      puStack_78 = (undefined1 *)0x5df6a3;
      cVar1 = func_0x00987030();
      if (cVar1 == '\0') {
        ppppppuVar6 = *pppppppuVar5;
        if (ppppppuVar6 != (uint ******)0x0) {
          if (ppppppuVar6 == (uint ******)0xfffffffc) {
            if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df738;
            bVar9 = false;
          }
          else if (ppppppuVar6 == (uint ******)0x0) {
            iVar2 = 0x12;
            bVar9 = true;
            pcVar3 = "retouchcheckpoint";
            pcVar7 = (char *)0x0;
            do {
              if (iVar2 == 0) break;
              iVar2 = iVar2 + -1;
              bVar9 = *pcVar3 == *pcVar7;
              pcVar3 = pcVar3 + 1;
              pcVar7 = pcVar7 + 1;
            } while (bVar9);
          }
          else {
            iVar2 = 0x12;
            bVar9 = true;
            pcVar3 = "retouchcheckpoint";
            ppppppuVar6 = ppppppuVar6 + 1;
            do {
              if (iVar2 == 0) break;
              iVar2 = iVar2 + -1;
              bVar9 = *pcVar3 == *(char *)ppppppuVar6;
              pcVar3 = pcVar3 + 1;
              ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
            } while (bVar9);
          }
          if (bVar9) {
            ppppppuStack_68 = (uint ******)0x5df733;
            ppppppuStack_64 = (uint ******)param_1;
            func_0x005f7b30();
            goto LAB_005dfa52;
          }
        }
LAB_005df738:
        ppppppuVar6 = *pppppppuVar5;
        if (ppppppuVar6 == (uint ******)0x0) {
LAB_005df793:
          ppppppuVar6 = *pppppppuVar5;
          if (ppppppuVar6 != (uint ******)0x0) {
            if (ppppppuVar6 == (uint ******)0xfffffffc) {
              if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df7ee;
              bVar9 = false;
            }
            else if (ppppppuVar6 == (uint ******)0x0) {
              iVar2 = 0x1b;
              bVar9 = true;
              pcVar3 = "CAutoCompleteListBox::hide";
              pcVar7 = (char *)0x0;
              do {
                if (iVar2 == 0) break;
                iVar2 = iVar2 + -1;
                bVar9 = *pcVar3 == *pcVar7;
                pcVar3 = pcVar3 + 1;
                pcVar7 = pcVar7 + 1;
              } while (bVar9);
            }
            else {
              iVar2 = 0x1b;
              bVar9 = true;
              pcVar3 = "CAutoCompleteListBox::hide";
              ppppppuVar6 = ppppppuVar6 + 1;
              do {
                if (iVar2 == 0) break;
                iVar2 = iVar2 + -1;
                bVar9 = *pcVar3 == *(char *)ppppppuVar6;
                pcVar3 = pcVar3 + 1;
                ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
              } while (bVar9);
            }
            if (bVar9) goto LAB_005df9ce;
          }
LAB_005df7ee:
          ppppppuVar6 = *pppppppuVar5;
          if (ppppppuVar6 != (uint ******)0x0) {
            if (ppppppuVar6 == (uint ******)0xfffffffc) {
              if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df8a3;
              bVar9 = false;
            }
            else if (ppppppuVar6 == (uint ******)0x0) {
              iVar2 = 0x10;
              bVar9 = true;
              pcVar3 = "goingfullscreen";
              pcVar7 = (char *)0x0;
              do {
                if (iVar2 == 0) break;
                iVar2 = iVar2 + -1;
                bVar9 = *pcVar3 == *pcVar7;
                pcVar3 = pcVar3 + 1;
                pcVar7 = pcVar7 + 1;
              } while (bVar9);
            }
            else {
              iVar2 = 0x10;
              bVar9 = true;
              pcVar3 = "goingfullscreen";
              ppppppuVar6 = ppppppuVar6 + 1;
              do {
                if (iVar2 == 0) break;
                iVar2 = iVar2 + -1;
                bVar9 = *pcVar3 == *(char *)ppppppuVar6;
                pcVar3 = pcVar3 + 1;
                ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
              } while (bVar9);
            }
            if (bVar9) goto LAB_005df849;
          }
LAB_005df8a3:
          ppppppuStack_64 = (uint ******)0x0;
          ppppppuStack_68 = (uint ******)0x5df8b1;
          cVar1 = func_0x00987030();
          if (cVar1 == '\0') {
            ppppppuVar6 = *pppppppuVar5;
            if (ppppppuVar6 != (uint ******)0x0) {
              if (ppppppuVar6 == (uint ******)0xfffffffc) {
                if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005dfa52;
                bVar9 = false;
              }
              else if (ppppppuVar6 == (uint ******)0x0) {
                iVar2 = 0xf;
                bVar9 = true;
                pcVar3 = "WebUserChanged";
                pcVar7 = (char *)0x0;
                do {
                  if (iVar2 == 0) break;
                  iVar2 = iVar2 + -1;
                  bVar9 = *pcVar3 == *pcVar7;
                  pcVar3 = pcVar3 + 1;
                  pcVar7 = pcVar7 + 1;
                } while (bVar9);
              }
              else {
                iVar2 = 0xf;
                bVar9 = true;
                pcVar3 = "WebUserChanged";
                ppppppuVar6 = ppppppuVar6 + 1;
                do {
                  if (iVar2 == 0) break;
                  iVar2 = iVar2 + -1;
                  bVar9 = *pcVar3 == *(char *)ppppppuVar6;
                  pcVar3 = pcVar3 + 1;
                  ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
                } while (bVar9);
              }
              if (bVar9) {
                ppppppuStack_64 = (uint ******)0x5df977;
                func_0x00573e20();
                if (param_1[0x3a8] != (uint ******)0x0) {
                  ppppppuStack_64 = (uint ******)&UNK_00c814f0;
                  ppppppuStack_68 = (uint ******)&UNK_00c7eafc;
                  ppppppuStack_6c = apppppuStack_40;
                  ppppuStack_48 = (uint ****)0x0;
                  ppppppuStack_70 = (uint ******)0x5df9aa;
                  func_0x00407a20();
                  ppppppuStack_70 = (uint ******)0x5df9b3;
                  ppppppuStack_70 = (uint ******)func_0x004019b0();
                  ppppppuStack_74 = param_1[0x3a8];
                  puStack_78 = (undefined1 *)0x5df9c0;
                  func_0x00768000();
                  puStack_78 = (undefined1 *)0x5df9c9;
                  func_0x009c84a0();
                }
              }
            }
            goto LAB_005dfa52;
          }
          if (_DAT_00d67914 == 0) goto LAB_005df8ca;
          ppppppuStack_64 = (uint ******)0x5df8c8;
          ppppppuStack_74 = (uint ******)func_0x009c2fc0();
        }
        else {
          if (ppppppuVar6 == (uint ******)0xfffffffc) {
            if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df793;
            bVar9 = false;
          }
          else if (ppppppuVar6 == (uint ******)0x0) {
            iVar2 = 0x1b;
            bVar9 = true;
            pcVar3 = "CAutoCompleteListBox::show";
            pcVar7 = (char *)0x0;
            do {
              if (iVar2 == 0) break;
              iVar2 = iVar2 + -1;
              bVar9 = *pcVar3 == *pcVar7;
              pcVar3 = pcVar3 + 1;
              pcVar7 = pcVar7 + 1;
            } while (bVar9);
          }
          else {
            iVar2 = 0x1b;
            bVar9 = true;
            pcVar3 = "CAutoCompleteListBox::show";
            ppppppuVar6 = ppppppuVar6 + 1;
            do {
              if (iVar2 == 0) break;
              iVar2 = iVar2 + -1;
              bVar9 = *pcVar3 == *(char *)ppppppuVar6;
              pcVar3 = pcVar3 + 1;
              ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
            } while (bVar9);
          }
          if (!bVar9) goto LAB_005df793;
LAB_005df9ce:
          ppppppuVar6 = *pppppppuVar5;
          if (ppppppuVar6 == (uint ******)0x0) {
LAB_005dfa16:
            bVar9 = false;
          }
          else if (ppppppuVar6 == (uint ******)0xfffffffc) {
            if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005dfa16;
            bVar9 = false;
          }
          else if (ppppppuVar6 == (uint ******)0x0) {
            iVar2 = 0x1b;
            bVar9 = true;
            pcVar3 = "CAutoCompleteListBox::show";
            pcVar7 = (char *)0x0;
            do {
              if (iVar2 == 0) break;
              iVar2 = iVar2 + -1;
              bVar9 = *pcVar3 == *pcVar7;
              pcVar3 = pcVar3 + 1;
              pcVar7 = pcVar7 + 1;
            } while (bVar9);
          }
          else {
            iVar2 = 0x1b;
            bVar9 = true;
            pcVar3 = "CAutoCompleteListBox::show";
            ppppppuVar6 = ppppppuVar6 + 1;
            do {
              if (iVar2 == 0) break;
              iVar2 = iVar2 + -1;
              bVar9 = *pcVar3 == *(char *)ppppppuVar6;
              pcVar3 = pcVar3 + 1;
              ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
            } while (bVar9);
          }
          if (param_1[0x3a8] != (uint ******)0x0) {
            *(bool *)(param_1[0x3a8] + 0x99) = !bVar9;
          }
LAB_005df849:
          if (_DAT_00d67914 == 0) {
            ppppppuStack_74 = (uint ******)0x0;
          }
          else {
            ppppppuStack_64 = (uint ******)0x5df85c;
            ppppppuStack_74 = (uint ******)func_0x009c2fc0();
          }
          ppppppuStack_64 = (uint ******)0x0;
          ppppppuStack_68 = (uint ******)0xd3b914;
          ppppppuStack_6c = (uint ******)0xd3b8a0;
          ppppppuStack_70 = (uint ******)0x0;
          puStack_78 = (undefined1 *)0x5df874;
          iVar2 = func_0x00c07db2();
          if (iVar2 != 0) {
            ppppppuStack_64 = (uint ******)0x5df882;
            cVar1 = func_0x009e39b0();
            if (cVar1 != '\0') {
              ppppppuStack_68 = (uint ******)0x5df88e;
              ppppppuStack_64 = (uint ******)pppppppuVar5;
              (**(code **)(*extraout_ECX + 0x7c))();
            }
          }
          if (_DAT_00d67914 == 0) {
LAB_005df8ca:
            ppppppuStack_74 = (uint ******)0x0;
          }
          else {
            ppppppuStack_64 = (uint ******)0x5df8a1;
            ppppppuStack_74 = (uint ******)func_0x009c2fc0();
          }
        }
        ppppppuStack_64 = (uint ******)0x0;
        ppppppuStack_68 = (uint ******)0xd3b914;
        ppppppuStack_6c = (uint ******)0xd3b8a0;
        ppppppuStack_70 = (uint ******)0x0;
        puStack_78 = (undefined1 *)0x5df8e0;
        iVar2 = func_0x00c07db2();
        if (iVar2 != 0) {
          ppppppuStack_64 = (uint ******)0x5df8f2;
          cVar1 = func_0x009e39b0();
          if (cVar1 != '\0') {
            ppppppuStack_68 = (uint ******)0x5df902;
            ppppppuStack_64 = (uint ******)pppppppuVar5;
            (**(code **)(*extraout_ECX_00 + 0x7c))();
          }
        }
      }
      else if (param_1[0xd13] != (uint ******)0x0) {
        *(undefined1 *)(param_1 + 0x91) = 1;
        ppppppuStack_6c = (uint ******)0x5df6c9;
        ppppppuStack_68 = param_1[0xd13];
        ppppppuStack_64 = (uint ******)pppppppuVar5;
        iVar2 = func_0x0051f070();
        return iVar2;
      }
    }
    else {
      if (ppppppuVar6 == (uint ******)0xfffffffc) {
        if (((uRamfffffffc & 0xffffff00) == 0) || (DAT_00000000 == '\0')) goto LAB_005df120;
        bVar9 = false;
      }
      else if (ppppppuVar6 == (uint ******)0x0) {
        iVar2 = 9;
        bVar9 = true;
        pcVar3 = "dragstop";
        pcVar7 = (char *)0x0;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *pcVar7;
          pcVar3 = pcVar3 + 1;
          pcVar7 = pcVar7 + 1;
        } while (bVar9);
      }
      else {
        iVar2 = 9;
        bVar9 = true;
        pcVar3 = "dragstop";
        ppppppuVar6 = ppppppuVar6 + 1;
        do {
          if (iVar2 == 0) break;
          iVar2 = iVar2 + -1;
          bVar9 = *pcVar3 == *(char *)ppppppuVar6;
          pcVar3 = pcVar3 + 1;
          ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
        } while (bVar9);
      }
      if (!bVar9) goto LAB_005df120;
LAB_005dfa47:
      *(undefined1 *)(param_1 + 0x370) = 0;
    }
  }
LAB_005dfa52:
  if ((param_2[8] == (uint ******)0x8000000) || (param_2[8] == (uint ******)0x8000001)) {
    if (_DAT_00d67914 == 0) {
      pppppuStack_4c = (uint *****)0x0;
    }
    else {
      ppppppuStack_64 = &pppppuStack_4c;
      ppppppuStack_68 = (uint ******)0x5dfa7c;
      func_0x009c2f50();
      if ((uint ******)pppppuStack_4c != (uint ******)0x0) {
        ppppppuVar6 = (uint ******)(pppppuStack_4c + 1);
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfb10;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x17;
          pbVar4 = &UNK_00c8fa50;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfb10:
          if (bVar9) {
            ppppppuStack_64 = (uint ******)0x5dfb22;
            iVar2 = func_0x005d20b0();
            goto LAB_005e04c5;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfb55;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x18;
          pbVar4 = &UNK_00c95acc;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfb55:
          if (bVar9) {
            ppppppuStack_68 = (uint ******)0x5dfb68;
            ppppppuStack_64 = (uint ******)param_1;
            iVar2 = func_0x005d1e20();
            goto LAB_005e04c5;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfb9b;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x17;
          pbVar4 = &UNK_00c8e914;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfb9b:
          if (bVar9) {
            ppppppuStack_64 = (uint ******)param_2;
            ppppppuStack_6c = (uint ******)0x5dfbad;
            ppppppuStack_68 = (uint ******)param_1;
            iVar2 = func_0x005d2020();
            goto LAB_005e04c5;
          }
        }
        if (ppppppuVar6 != (uint ******)0x0) {
          bVar9 = true;
          iVar2 = 0x17;
          pbVar4 = &UNK_00c870f8;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfbe0:
          if (!bVar9) goto LAB_005dfbeb;
LAB_005e04b5:
          ppppppuStack_64 = (uint ******)0x0;
LAB_005e04bc:
          ppppppuStack_6c = (uint ******)0x5e04c3;
          ppppppuStack_68 = (uint ******)param_1;
          iVar2 = func_0x005d21a0();
          goto LAB_005e04c5;
        }
        if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
          bVar9 = false;
          goto LAB_005dfbe0;
        }
LAB_005dfbeb:
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfc19;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x16;
          pbVar4 = &UNK_00c87110;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfc19:
          if (bVar9) goto LAB_005e04b5;
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfc52;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x1a;
          pbVar4 = &UNK_00c87130;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfc52:
          if (bVar9) goto LAB_005e04b5;
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfc8b;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x17;
          pbVar4 = &UNK_00c96b08;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfc8b:
          if (bVar9) {
            ppppppuStack_64 = (uint ******)0x1;
            goto LAB_005e04bc;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfccc;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x17;
          pbVar4 = &UNK_00c96b20;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfccc:
          if (bVar9) {
            ppppppuStack_64 = (uint ******)0x2;
            goto LAB_005e04bc;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfd0d;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x17;
          pbVar4 = &UNK_00c96b38;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfd0d:
          if (bVar9) {
            ppppppuStack_64 = (uint ******)0x3;
            goto LAB_005e04bc;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfd4e;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x17;
          pbVar4 = &UNK_00c95f58;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfd4e:
          if (bVar9) {
            if (param_2[8] != (uint ******)0x8000001) {
              ppppppuStack_64 = (uint ******)0x1;
              ppppppuStack_68 = (uint ******)0x0;
              ppppppuStack_6c = (uint ******)0x0;
              ppppppuStack_74 = (uint ******)0x5dfd6e;
              ppppppuStack_70 = (uint ******)param_1;
              func_0x0065b840();
            }
            goto LAB_005dfd6e;
          }
        }
        if (ppppppuVar6 != (uint ******)0x0) {
          bVar9 = true;
          iVar2 = 0x1e;
          pbVar4 = &UNK_00c8e530;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfdb3:
          if (!bVar9) goto LAB_005dfdbe;
LAB_005e04a8:
          ppppppuStack_64 = (uint ******)param_2;
          ppppppuStack_6c = (uint ******)0x5e04b3;
          ppppppuStack_68 = (uint ******)param_1;
          iVar2 = func_0x00595960();
          goto LAB_005e04c5;
        }
        if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
          bVar9 = false;
          goto LAB_005dfdb3;
        }
LAB_005dfdbe:
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfdec;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x1d;
          pbVar4 = &UNK_00c8e4f4;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfdec:
          if (bVar9) goto LAB_005e04a8;
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfe25;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x1b;
          pbVar4 = &UNK_00c8e514;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfe25:
          if (bVar9) goto LAB_005e04a8;
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005dfe5e;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x1f;
          pbVar4 = &UNK_00c918cc;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005dfe5e:
          if (bVar9) {
            ppppppuStack_64 = (uint ******)param_2;
            ppppppuStack_6c = (uint ******)0x5dfe70;
            ppppppuStack_68 = (uint ******)param_1;
            iVar2 = func_0x00595fa0();
            goto LAB_005e04c5;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) == 0) || (DAT_00000000 == '\0'))
          goto LAB_005dfaa8;
          bVar9 = false;
        }
        else {
          iVar2 = 0x18;
          bVar9 = true;
          pbVar4 = &UNK_00c96b50;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar6;
            pbVar4 = pbVar4 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
        }
        if (bVar9) {
          ppppppuStack_64 = (uint ******)param_2;
          ppppppuStack_68 = (uint ******)0x5dfeb9;
          iVar2 = func_0x005f80d0();
          goto LAB_005e04c5;
        }
      }
    }
LAB_005dfaa8:
    ppppppuStack_64 = (uint ******)0x5dfab1;
    func_0x00401000();
  }
  if (param_2[8] == (uint ******)0x204) {
    ppppppuStack_64 = (uint ******)0x5dfaca;
    func_0x009cd040();
    if ((((uint ******)pppppuStack_4c == (uint ******)0x0) ||
        (((uint)*pppppuStack_4c & 0xffffff00) == 0)) || (*(byte *)(pppppuStack_4c + 1) == 0))
    goto LAB_005dfae4;
    ppppppuStack_64 = (uint ******)0x5dfec7;
    func_0x00401000();
  }
  if (param_2[8] == (uint ******)0x8000003) {
    ppppppuStack_64 = (uint ******)0x5dfee1;
    func_0x009cd040();
    if ((((uint ******)pppppuStack_4c == (uint ******)0x0) ||
        (((uint)*pppppuStack_4c & 0xffffff00) == 0)) || (*(byte *)(pppppuStack_4c + 1) == 0)) {
LAB_005dfae4:
      ppppppuStack_64 = (uint ******)0x5dfaed;
      func_0x00401000();
      return 3;
    }
    if ((uint ******)(pppppuStack_4c + 1) == (uint ******)0x0) {
      bVar9 = false;
    }
    else {
      iVar2 = 0x12;
      bVar9 = true;
      pbVar4 = &UNK_00c88a40;
      ppppppuVar6 = (uint ******)(pppppuStack_4c + 1);
      do {
        if (iVar2 == 0) break;
        iVar2 = iVar2 + -1;
        bVar9 = *pbVar4 == *(byte *)ppppppuVar6;
        pbVar4 = pbVar4 + 1;
        ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
      } while (bVar9);
    }
    if (!bVar9) {
      ppppppuStack_64 = (uint ******)0x0;
      ppppppuStack_68 = (uint ******)0x5dff65;
      cVar1 = func_0x00987030();
      if (cVar1 != '\0') {
        ppppppuStack_68 = (uint ******)0x5dff72;
        cVar1 = func_0x00569620();
        if (cVar1 != '\0') {
          ppppppuStack_68 = (uint ******)0x1;
          ppppppuStack_6c = (uint ******)0x0;
          ppppppuStack_70 = (uint ******)0x1;
          ppppppuStack_74 = ppppppuStack_54;
          puStack_78 = (undefined1 *)0x5dff8a;
          iVar2 = func_0x005f8d80();
          goto LAB_005e04c5;
        }
      }
LAB_005de9f0:
      ppppppuStack_68 = (uint ******)0x5de9f9;
      func_0x00401000();
      return 0xf4241;
    }
    ppppppuStack_64 = (uint ******)0x5dff2d;
    cVar1 = func_0x00569620();
    if (cVar1 == '\0') {
      ppppppuStack_64 = (uint ******)0x0;
      ppppppuStack_68 = (uint ******)0x0;
      ppppppuStack_6c = (uint ******)0x1;
      ppppppuStack_74 = (uint ******)0x5dff50;
      ppppppuStack_70 = (uint ******)param_1;
      iVar2 = func_0x005f8d80();
    }
    else {
      ppppppuStack_64 = (uint ******)0x5dff3b;
      iVar2 = func_0x009cd8a0();
    }
    goto LAB_005e04c5;
  }
  if (param_2[8] != (uint ******)0x8000004) goto LAB_005e0451;
  ppppppuStack_64 = (uint ******)0x5dffa6;
  func_0x009cd040();
  if ((((uint ******)pppppuStack_4c == (uint ******)0x0) ||
      (((uint)*pppppuStack_4c & 0xffffff00) == 0)) ||
     (ppppppuVar6 = (uint ******)(pppppuStack_4c + 1), *(byte *)ppppppuVar6 == 0))
  goto LAB_005dfae4;
  ppppppuStack_64 = (uint ******)0x0;
  ppppppuStack_68 = (uint ******)0x5dffda;
  cVar1 = func_0x00987030();
  if (cVar1 != '\0') {
    ppppppuStack_6c = ppppppuStack_54;
    ppppppuStack_70 = (uint ******)0x5dffeb;
    ppppppuStack_68 = &pppppuStack_4c;
    iVar2 = func_0x005d4ef0();
    goto LAB_005e04c5;
  }
  ppppppuStack_68 = (uint ******)0x0;
  ppppppuStack_6c = (uint ******)0x5dfffc;
  cVar1 = func_0x00987030();
  if (cVar1 != '\0') {
    ppppppuStack_70 = (uint ******)param_2;
    ppppppuStack_74 = (uint ******)&stack0xffffffa8;
    ppppppuStack_7c = (uint ******)0x5e0013;
    func_0x00743980();
    ppppppuStack_7c = (uint ******)0x5e001c;
    func_0x00401000();
    return 1000000;
  }
  ppppppuVar8 = unaff_ESI[0xc35];
  if ((((ppppppuVar8 == (uint ******)0x4) || (ppppppuVar8 == (uint ******)0x5)) ||
      (ppppppuVar8 == (uint ******)0x2)) || (ppppppuVar8 == (uint ******)0x6)) {
    ppppppuStack_70 = (uint ******)0x5e0051;
    cVar1 = func_0x005e0610();
    if (cVar1 != '\0') {
      ppppppuStack_70 = (uint ******)0x5e005a;
      ppppppuStack_70 = (uint ******)func_0x00569620();
      ppppppuStack_74 = (uint ******)0x0;
      puStack_78 = (undefined1 *)0x1;
      ppppppuStack_7c = (uint ******)unaff_ESI;
      iVar2 = func_0x005f8d80();
      if (iVar2 != 0) goto LAB_005e04c5;
    }
  }
  ppppppuStack_70 = (uint ******)0x0;
  ppppppuStack_74 = (uint ******)0x5e0083;
  cVar1 = func_0x00987030();
  if (cVar1 != '\0') {
    puStack_78 = (undefined1 *)0x5e0095;
    ppppppuStack_74 = (uint ******)unaff_EDI;
    iVar2 = func_0x00760240();
    goto LAB_005e04c5;
  }
  ppppppuStack_74 = (uint ******)0x0;
  puStack_78 = (undefined1 *)0x5e00a6;
  cVar1 = func_0x00987030();
  if (cVar1 != '\0') {
    puStack_78 = &stack0xffffffa0;
    ppppppuStack_7c = ppppppuStack_64;
    iVar2 = func_0x005d59f0();
    goto LAB_005e04c5;
  }
  puStack_78 = (undefined1 *)0x0;
  ppppppuStack_7c = (uint ******)0x5e00ce;
  cVar1 = func_0x00987030();
  if (cVar1 == '\0') {
    ppppppuStack_7c = (uint ******)0x0;
    cVar1 = func_0x00987030();
    if (cVar1 == '\0') {
      ppppppuStack_7c = (uint ******)0x0;
      cVar1 = func_0x00987030();
      if (cVar1 == '\0') {
        ppppppuStack_7c = (uint ******)0x0;
        cVar1 = func_0x00987030();
        if (((cVar1 != '\0') || (cVar1 = func_0x00987030(0), cVar1 != '\0')) ||
           (cVar1 = func_0x00987030(0), cVar1 != '\0')) {
          iVar2 = func_0x005d9cc0(ppppppuStack_6c,&ppppppuStack_68,param_2);
          goto LAB_005e04c5;
        }
        uVar10 = 0;
        cVar1 = func_0x00987030(0);
        if ((cVar1 != '\0') || (cVar1 = func_0x00987030(0), cVar1 != '\0')) {
          iVar2 = func_0x005d8810(ppppppuStack_70);
          goto LAB_005e04c5;
        }
        cVar1 = func_0x00987030(0);
        if (cVar1 != '\0') {
          iVar2 = func_0x005de120();
          goto LAB_005e04c5;
        }
        cVar1 = func_0x00987030(0);
        if (cVar1 != '\0') {
          iVar2 = func_0x005e0f70();
          goto LAB_005e04c5;
        }
        cVar1 = func_0x00987030(0);
        if (cVar1 != '\0') {
          iVar2 = func_0x0069af80(ppppppuStack_7c);
          goto LAB_005e04c5;
        }
        cVar1 = func_0x00987030(0);
        if (cVar1 != '\0') {
          iVar2 = func_0x00679ca0(uVar10,&ppppppuStack_7c);
          goto LAB_005e04c5;
        }
        cVar1 = func_0x00987030(0);
        if (cVar1 != '\0') {
          ppppppuStack_64 = &pppppuStack_4c;
          ppppppuStack_6c = (uint ******)0x5e0234;
          ppppppuStack_68 = (uint ******)param_1;
          iVar2 = func_0x005d56e0();
          goto LAB_005e04c5;
        }
        if ((uint *******)param_1[0xd13] != (uint *******)0x0) {
          ppppppuStack_64 = &pppppuStack_4c;
          ppppppuStack_6c = (uint ******)0x5e0252;
          ppppppuStack_68 = param_1[0xd13];
          iVar2 = func_0x0051f070();
          if (iVar2 == 1000000) {
LAB_005dfd6e:
            ppppppuStack_64 = (uint ******)0x5dfd77;
            func_0x00401000();
            return 1000000;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005e028c;
          }
        }
        else {
          iVar2 = 10;
          bVar9 = true;
          pbVar4 = &UNK_00c96c34;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005e028c:
          if (bVar9) {
            if (*(char *)((int)param_1 + 0x332f) != '\0') {
              ppppppuStack_64 = (uint ******)&UNK_00c95a94;
              ppppuStack_48 = (uint ****)0x0;
              ppppppuStack_68 = (uint ******)0x5e02bb;
              func_0x00985ff0();
              ppppppuStack_70 = (uint ******)0x5e02c8;
              ppppppuStack_68 = (uint ******)&ppppuStack_48;
              iVar2 = func_0x005d59f0();
              ppppppuStack_70 = (uint ******)0x5e02cf;
              func_0x00401000();
              ppppppuStack_70 = (uint ******)0x5e02d8;
              func_0x00401000();
              return iVar2;
            }
            ppppppuStack_64 = (uint ******)0x5e02ed;
            iVar2 = func_0x009cd8a0();
            goto LAB_005e04c5;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005e0324;
          }
        }
        else {
          bVar9 = true;
          iVar2 = 0x18;
          pbVar4 = &UNK_00c8f7a8;
          ppppppuVar8 = ppppppuVar6;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar8;
            pbVar4 = pbVar4 + 1;
            ppppppuVar8 = (uint ******)((int)ppppppuVar8 + 1);
          } while (bVar9);
LAB_005e0324:
          if (bVar9) {
            ppppppuStack_64 = (uint ******)0x0;
            ppppppuStack_68 = (uint ******)0x1;
            ppppppuStack_6c = (uint ******)0x5e0338;
            iVar2 = func_0x005ff7a0();
            goto LAB_005e04c5;
          }
        }
        if (ppppppuVar6 == (uint ******)0x0) {
          if ((((uint)*pppppuStack_4c & 0xffffff00) != 0) && (DAT_00000000 != '\0')) {
            bVar9 = false;
            goto LAB_005e0370;
          }
        }
        else {
          iVar2 = 0x18;
          bVar9 = true;
          pbVar4 = &UNK_00c96c40;
          do {
            if (iVar2 == 0) break;
            iVar2 = iVar2 + -1;
            bVar9 = *pbVar4 == *(byte *)ppppppuVar6;
            pbVar4 = pbVar4 + 1;
            ppppppuVar6 = (uint ******)((int)ppppppuVar6 + 1);
          } while (bVar9);
LAB_005e0370:
          if (bVar9) {
            pppppppuVar5 = (uint *******)((int)param_1[0x3ac][200] + (int)param_1[0x3ac][0xbe]);
            if (pppppppuVar5 != (uint *******)0xffffffff) {
              ppppppuStack_64 = (uint ******)0x5e039f;
              func_0x004a06e0();
              ppppppuStack_64 = apppppuStack_40;
              ppppppuStack_6c = (uint ******)0x5e03b4;
              ppppppuStack_68 = (uint ******)pppppppuVar5;
              func_0x004ae4e0();
              ppppppuStack_6c = (uint ******)0x5e03bd;
              cVar1 = func_0x004a07e0();
              if (cVar1 != '\0') {
                ppppppuStack_6c = (uint ******)0x1;
                ppppppuStack_70 = (uint ******)0x5e03d0;
                func_0x004ab9a0();
              }
              ppppppuStack_6c = (uint ******)0x5e03d9;
              cVar1 = func_0x004a0800();
              if (cVar1 != '\0') {
                if (iStack_38 == 0) {
                  ppppppuStack_70 = (uint ******)0x0;
                }
                else {
                  ppppppuStack_70 = (uint ******)(iStack_38 + 4);
                }
                ppppppuStack_6c = (uint ******)0x0;
                ppppppuStack_74 = (uint ******)0x5e03f6;
                func_0x00575130();
              }
              ppppppuStack_6c = (uint ******)0x5e03ff;
              func_0x004abb70();
            }
            ppppppuStack_64 = (uint ******)0x5e0408;
            func_0x00401000();
            return 1000000;
          }
        }
        ppppppuStack_64 = (uint ******)pppppuStack_4c;
        if (*(byte *)pppppuStack_4c < 0x80) {
          ppppppuStack_68 = (uint ******)pppppuStack_4c;
          ppppppuStack_6c = (uint ******)0x5e0431;
          InterlockedIncrement();
        }
        ppppppuStack_6c = (uint ******)0x5e043b;
        ppppppuStack_68 = (uint ******)param_1;
        iVar2 = func_0x005e04e0();
        ppppppuStack_6c = (uint ******)0x5e0446;
        func_0x00401000();
        if (iVar2 != 0) {
          return iVar2;
        }
LAB_005e0451:
        if (param_2[8] != (uint ******)0x72677264) {
          return 0xf4241;
        }
        ppppppuStack_64 = (uint ******)param_2;
        ppppppuStack_6c = (uint ******)0x5e0469;
        ppppppuStack_68 = (uint ******)param_1;
        iVar2 = func_0x00602c40();
        return iVar2;
      }
    }
  }
  ppppppuStack_7c = (uint ******)&ppppppuStack_64;
  iVar2 = func_0x005952d0(ppppppuStack_68);
LAB_005e04c5:
  ppppppuStack_70 = (uint ******)0x5e04ce;
  func_0x00401000();
  return iVar2;
}


